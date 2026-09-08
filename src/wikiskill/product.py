"""Host-agent-driven skill improvement, independent of model and runtime.

This controller emits work requests; the caller's agent executes them in its
normal environment. Immutable event records own scores and retained versions.
No model is invoked and no sandbox or account configuration is changed here.
"""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from uuid import uuid4

SCHEMA = 'wikiskill.workspace.v1'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value, *, immutable=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if immutable and path.exists():
        if path.read_text(encoding='utf-8') != data: raise ValueError('Existing record differs: '+str(path))
        return
    tmp = path.with_name('.'+path.name+'.'+uuid4().hex+'.tmp')
    tmp.write_text(data, encoding='utf-8'); os.replace(tmp, path)


@contextmanager
def locked(root):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    with (root/'.writer.lock').open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if handle.tell() == 0: handle.write(b'0'); handle.flush()
            handle.seek(0)
            try: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc: raise RuntimeError('Another writer owns this workspace') from exc
        else:
            import fcntl
            try: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc: raise RuntimeError('Another writer owns this workspace') from exc
        try: yield root
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Score must be a finite number')
    return float(value)


def normalize_tasks(path):
    data = read(path); base = Path(path).resolve().parent
    if isinstance(data, list): raw = data
    elif isinstance(data, dict):
        raw = [dict(t, split=split) for split in ('train', 'validation') for t in data.get(split, [])]
    else: raise ValueError('Tasks must be a list, or an object with train and validation lists')
    rows = []; ids = set()
    for index, task in enumerate(raw):
        if not isinstance(task, dict): raise ValueError('Every task must be an object')
        split = task.get('split'); split = 'validation' if split == 'val' else split
        if split not in ('train', 'validation'): raise ValueError('Improvement tasks use train or validation splits')
        uid = str(task.get('id', f'{split}-{index+1}'))
        if not uid.strip() or uid in ids: raise ValueError('Task IDs must be nonempty and unique across splits')
        instruction = task.get('instruction')
        if not isinstance(instruction, str) or not instruction.strip(): raise ValueError('Task instruction is required')
        files = task.get('files', [])
        if not isinstance(files, list) or not all(isinstance(p, str) for p in files): raise ValueError('Task files must be paths')
        files = [str((base/p).resolve()) for p in files]
        if any(not Path(p).exists() for p in files): raise ValueError('A declared task file does not exist')
        row = {**task, 'id': uid, 'split': split, 'files': files}; rows.append(row); ids.add(uid)
    if not any(t['split']=='train' for t in rows) or not any(t['split']=='validation' for t in rows):
        raise ValueError('Provide at least one training task and one validation task')
    return rows


def _load(root):
    config = read(root/'config.json')
    if config.get('schema_version') != SCHEMA or read(root/'config.sha256.json')['sha256'] != digest(config):
        raise ValueError('Workspace configuration changed; start a new workspace for changed conditions')
    s = {'config': config, 'phase': 'baseline', 'round': 1, 'best_score': None,
         'current_skill': config['initial_skill'], 'tasks': [], 'requests': {}, 'results': {},
         'patterns': {}, 'feedback': [], 'history': [], 'candidate': None, 'events': 0, 'last_hash': None}
    inherited=config.get('initial_knowledge')
    if inherited:
        if file_hash(root/inherited['file'])!=inherited['sha256']:raise ValueError('Inherited knowledge changed')
        knowledge=read(root/inherited['file']);s['patterns']=knowledge['patterns'];s['feedback']=knowledge['feedback']
        for note in s['feedback']:
            if file_hash(root/note['file'])!=note['sha256']:raise ValueError('Inherited human feedback changed')
    for i,p in enumerate(sorted((root/'events').glob('*.json')), 1):
        e = read(p)
        if e['sequence'] != i or e['previous'] != s['last_hash']: raise ValueError('Event history is incomplete or changed')
        for rel,h in e.get('artifacts', {}).items():
            f = root/rel
            if not f.resolve().is_relative_to(root) or file_hash(f)!=h: raise ValueError('Recorded artifact changed: '+rel)
        kind=e['type']; value=e['value']
        if kind=='tasks': s['tasks']=value['tasks']
        elif kind=='request': s['requests'][value['id']]={**value,'status':'pending'}
        elif kind=='result':
            s['results'][value['request_id']]=value; s['requests'][value['request_id']]['status']='complete'
        elif kind=='failure': s['requests'][value['request_id']].update(status='failed',error=value['error'],failed_output=value.get('output'))
        elif kind=='retry': s['requests'][value['request_id']]['status']='superseded'
        elif kind=='wiki':
            s['patterns'].update(value['patterns']);s['requests'][value['request_id']].update(status='complete',submission=value['submission']);s['phase']='proposer'
        elif kind=='proposal':
            s['candidate']=value;s['requests'][value['request_id']].update(status='complete',proposal=value);s['phase']='validation'
        elif kind=='phase': s.update(value)
        elif kind=='gate':
            s['history'].append(value)
            if value['accepted']: s.update(best_score=value['candidate_score'],current_skill=value['skill'])
            s['candidate']=None; s['round']+=1
            s['phase']='complete' if s['round']>config['rounds'] else 'train'
        elif kind=='feedback': s['feedback'].append(value)
        else: raise ValueError('Unknown journal event: '+kind)
        s['events']=i;s['last_hash']=file_hash(p)
    if s['current_skill'] and file_hash(root/s['current_skill']['file'])!=s['current_skill']['sha256']:
        raise ValueError('Retained skill changed')
    return s


def _event(root,s,kind,value,artifacts=()):
    e={'sequence':s['events']+1,'previous':s['last_hash'],'at':now(),'type':kind,'value':value,
       'artifacts':{Path(p).relative_to(root).as_posix():file_hash(p) for p in artifacts}}
    write(root/'events'/f'{e["sequence"]:08}.json',e,immutable=True)
    return _load(root)


def _store_file(root, path, name):
    data=Path(path).read_bytes();target=root/'artifacts'/uuid4().hex/name
    target.parent.mkdir(parents=True);target.write_bytes(data)
    return {'file':target.relative_to(root).as_posix(),'sha256':file_hash(target)},target


def start(root, *, tasks=None, skill=None, rounds=1, direction='maximize', min_improvement=0., scorer=None, scorer_timeout=120, project=None, from_workspace=None, trust_scorer=False):
    if isinstance(rounds,bool) or not isinstance(rounds,int) or rounds<1 or direction not in ('maximize','minimize') or finite(min_improvement)<0 or finite(scorer_timeout)<=0:
        raise ValueError('Use positive rounds/timeouts, a valid direction and nonnegative minimum improvement')
    if scorer is not None and (not isinstance(scorer,list) or not scorer or not all(isinstance(x,str) for x in scorer)):
        raise ValueError('Scorer must be a nonempty JSON command array, not a shell command')
    root=Path(root).resolve()
    if root.exists() and any(root.iterdir()): raise ValueError('Workspace is not empty; use next/status to resume')
    loaded=normalize_tasks(tasks) if tasks else []
    if skill and not Path(skill).is_file():raise ValueError('Initial skill file does not exist')
    if project and not Path(project).is_dir():raise ValueError('Project directory does not exist')
    previous=_load(Path(from_workspace).resolve()) if from_workspace else None
    if previous and not skill and previous['current_skill']:
        skill=Path(from_workspace).resolve()/previous['current_skill']['file']
    with locked(root):
        inherited=None
        if previous:
            notes=[]
            for old in previous['feedback']:
                f=root/'feedback'/(old['id']+'.md');f.parent.mkdir(exist_ok=True);f.write_text(old['text'],encoding='utf-8')
                notes.append({**old,'file':f.relative_to(root).as_posix(),'sha256':file_hash(f)})
            knowledge={'patterns':previous['patterns'],'feedback':notes,'source_workspace_fingerprint':digest(previous['config']),'source_last_event':previous['last_hash']}
            f=root/'inherited-knowledge.json';write(f,knowledge,immutable=True)
            inherited={'file':f.relative_to(root).as_posix(),'sha256':file_hash(f)}
        initial,_ = _store_file(root,skill,'SKILL.md') if skill else (None,None)
        config={'schema_version':SCHEMA,'created_at':now(),'rounds':rounds,'direction':direction,
                'min_improvement':float(min_improvement),'scorer':scorer,'scorer_timeout':scorer_timeout,
                'project':str(Path(project or Path.cwd()).resolve()),'initial_skill':initial,'initial_knowledge':inherited,
                'execution':'host_agent','environment':'host_default','model':'caller_selected'}
        write(root/'config.json',config,immutable=True);write(root/'config.sha256.json',{'sha256':digest(config)},immutable=True)
        s=_load(root)
        if loaded:s=_event(root,s,'tasks',{'tasks':loaded})
        _wiki_view(root,s)
        if trust_scorer and scorer:
            from .scorer_trust import approve,describe
            approve(root,config,describe(root,config)['fingerprint'])
        return _status(root,s)


def set_tasks(root, tasks):
    rows=normalize_tasks(tasks)
    with locked(root) as root:
        s=_load(root)
        if s['requests'] or s['tasks']:raise ValueError('Task set already fixed; use a new workspace')
        return _status(root,_event(root,s,'tasks',{'tasks':rows}))


def _task_results(s,phase,round_number):
    return {s['requests'][rid]['task_id']:v for rid,v in s['results'].items()
            if s['requests'][rid]['phase']==phase and s['requests'][rid]['round']==round_number}


def _stage_tasks(s):
    split='train' if s['phase']=='train' else 'validation'
    return [t for t in s['tasks'] if t['split']==split]


def _advance(root,s):
    while s['phase'] in ('baseline','train','validation') and s['tasks']:
        if any(r['status'] in ('pending','failed') and r['phase']==s['phase'] and r['round']==s['round'] for r in s['requests'].values()):return s
        if s['phase']=='validation' and s['candidate']['no_action']:
            rows={}
        else:
            rows=_task_results(s,s['phase'],s['round'])
            if len(rows)!=len(_stage_tasks(s)):return s
        if s['phase']=='baseline':
            score=sum(r['score'] for r in rows.values())/len(rows)
            s=_event(root,s,'phase',{'phase':'train','best_score':score})
        elif s['phase']=='train':s=_event(root,s,'phase',{'phase':'maintainer'})
        else:
            score=sum(r['score'] for r in rows.values())/len(rows) if rows else None
            delta=None if score is None else (score-s['best_score'])*(1 if s['config']['direction']=='maximize' else -1)
            accepted=delta is not None and delta>s['config']['min_improvement']
            s=_event(root,s,'gate',{'round':s['round'],'accepted':accepted,'verdict':'NO_ACTION' if score is None else 'ACCEPT' if accepted else 'REJECT',
                                  'incumbent_score':s['best_score'],'candidate_score':score,'improvement':delta,
                                  'skill':s['candidate'].get('skill') if accepted else s['current_skill'],
                                  'candidate_skill':s['candidate'].get('skill'),'note':s['candidate']['note']})
    return s


def _wiki_view(root,s):
    folder=root/'wiki';folder.mkdir(exist_ok=True)
    lines=['# Wiki\n','Lessons from task outcomes and user feedback.\n']
    for name,item in s['patterns'].items():
        filename=hashlib.sha256(name.encode()).hexdigest()[:16]+'.md';p=folder/'patterns'/filename;p.parent.mkdir(exist_ok=True)
        p.write_text('# '+name+'\n\n'+item['content']+'\n',encoding='utf-8')
        lines.append(f'- [{name}](patterns/{filename})')
    lines.append('\n## User feedback\n')
    for f in s['feedback']:
        lines.append(f'- [{f["id"]}](../{f["file"]})')
    (folder/'index.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def _context(root,s):
    ids={rid for rid,r in s['requests'].items() if r['phase']=='train' and r['round']==s['round'] and r['status']=='complete'}
    by={t['id']:t for t in s['tasks']}
    records=[{**s['results'][rid],'source_id':rid,'task':by[s['requests'][rid]['task_id']]} for rid in sorted(ids)]
    return {'round':s['round'],'current_skill':s['current_skill'],'wiki':{name:{**v,'source_id':'pattern-'+digest([name,v])[:16]} for name,v in s['patterns'].items()},'human_feedback':s['feedback'],
            'training_records':records,'gate_history':s['history'],
            'instructions':'Learn procedures from training outcomes and feedback. Review successful and failed cases when available. Do not turn one-off reference values into reusable instructions.'}


def next_work(root,count=1):
    if isinstance(count,bool) or not isinstance(count,int) or count<1:raise ValueError('count must be a positive integer')
    with locked(root) as root:
        s=_advance(root,_load(root));_wiki_view(root,s)
        if not s['tasks']:return {**_status(root,s),'phase':'needs_tasks','action':'Provide train and validation tasks with the tasks command.'}
        failed=[r for r in s['requests'].values() if r['status']=='failed']
        if failed:return {**_status(root,s),'phase':'needs_attention','failures':failed,'action':'Resolve the failure, then explicitly retry its request.'}
        if s['phase']=='complete':return _status(root,s)
        if s['config']['scorer']:
            from .scorer_trust import describe
            info=describe(root,s['config'])
            if not info['trusted']:return {**_status(root,s),'phase':'needs_scorer_trust','scorer':info,'action':'Review scorer inspect, then authorize this fingerprint with scorer trust.'}
        active=[r for r in s['requests'].values() if r['status']=='pending' and r['phase']==s['phase'] and r['round']==s['round']]
        todo=[]
        if s['phase'] in ('baseline','train','validation'):
            done=_task_results(s,s['phase'],s['round']);busy={r['task_id'] for r in active}
            todo=[t for t in _stage_tasks(s) if t['id'] not in done and t['id'] not in busy]
        elif not active:todo=[None]
        for task in todo[:max(0,count-len(active))]:
            rid='req-'+uuid4().hex[:16]
            req={'id':rid,'kind':'task' if task else s['phase'],'phase':s['phase'],'round':s['round'],
                 'task_id':task['id'] if task else None,'model':'caller_selected','environment':'host_default',
                 'skill':s['candidate']['skill'] if s['phase']=='validation' else s['current_skill']}
            folder=root/'requests'/rid;folder.mkdir(parents=True)
            if task:
                prior=[r for r in s['requests'].values() if r['phase']==s['phase'] and r['round']==s['round'] and r['task_id']==task['id'] and r['status']=='superseded']
                if prior:req.update(retry_of=prior[-1]['id'],previous_output=prior[-1].get('failed_output'),previous_error=prior[-1].get('error'))
                req['task']={k:v for k,v in task.items() if k not in ('reference','expected','gold','score')}
                req['instruction']='Execute this task with the indicated skill using your normal tools. Save the actual output to a file, then record it; do not assign an invented score.'
            else:
                p=folder/'context.json';write(p,_context(root,s),immutable=True);req['context_file']=p.relative_to(root).as_posix()
                req['instruction']=('Consolidate experience into reusable Wiki patterns. Preserve human feedback and cite training request IDs or feedback IDs. Write a JSON object with patterns [{name, content, sources}].' if s['phase']=='maintainer' else 'Read the Wiki and relevant training trajectories; propose a reusable SKILL.md with clear applicability and concrete actions, or choose no_action. Keep factual answers out of the skill.')
            p=folder/'request.json';write(p,req,immutable=True);artifacts=[p]+([folder/'context.json'] if not task else [])
            s=_event(root,s,'request',req,artifacts);active.append(s['requests'][rid])
        return {**_status(root,s),'requests':active[:count]}


def _request(s,rid,kind):
    if rid not in s['requests']:raise ValueError('Unknown request')
    r=s['requests'][rid]
    if r['kind']!=kind:raise ValueError('Wrong operation for this request')
    if r['status'] not in ('pending','complete'):raise ValueError('Failed/superseded request requires explicit retry')
    return r


def record(root,request_id,output=None,score=None,feedback='',success=None,model=None,runtime=None,error=None,trace=None,effort=None):
    with locked(root) as root:
        s=_load(root);req=_request(s,request_id,'task')
        if req['status']=='complete':
            row=s['results'][request_id]
            if output and file_hash(output)!=row['output']['sha256']:raise ValueError('Completed output differs')
            if score is not None and finite(score)!=row['score']:raise ValueError('Completed score differs')
            return _status(root,s)
        if error:return _status(root,_event(root,s,'failure',{'request_id':request_id,'error':error}))
        if output is None:raise ValueError('An actual output file is required')
        scorer_info=None
        if s['config']['scorer']:
            from .scorer_trust import require
            scorer_info=require(root,s['config'])
        stored,p=_store_file(root,output,Path(output).name)
        judged={'score':score,'feedback':feedback,'success':success};files=[p];trace_record=None
        if trace:
            trace_record,t=_store_file(root,trace,'trace.txt');files.append(t)
        if s['config']['scorer']:
            task=next(t for t in s['tasks'] if t['id']==req['task_id'])
            try:text=p.read_text(encoding='utf-8')
            except UnicodeDecodeError:text=None
            payload={'task':task,'output':{'path':str(p),'text':text},'phase':req['phase'],'round':req['round']}
            try:
                proc=subprocess.run([scorer_info['resolved_executable'],*s['config']['scorer'][1:]],cwd=s['config']['project'],input=json.dumps(payload,ensure_ascii=False),text=True,capture_output=True,timeout=s['config']['scorer_timeout'])
                for name,data in [('scorer.stdout',proc.stdout),('scorer.stderr',proc.stderr)]:
                    f=p.parent/name;f.write_text(data,encoding='utf-8');files.append(f)
                if proc.returncode:raise RuntimeError(f'Scorer exited with code {proc.returncode}')
                judged=json.loads(proc.stdout)
            except (OSError,subprocess.SubprocessError,ValueError,RuntimeError) as exc:
                _event(root,s,'failure',{'request_id':request_id,'error':str(exc),'output':stored},files)
                raise RuntimeError('Scoring failed; output retained, resolve the failure before retry') from exc
        try:
            value=finite(judged['score']);fb=judged.get('feedback','');ok=judged.get('success')
            if not isinstance(fb,str) or ok is not None and not isinstance(ok,bool):raise ValueError('Feedback must be text and success must be boolean or null')
        except (KeyError,TypeError,ValueError) as exc:
            _event(root,s,'failure',{'request_id':request_id,'error':'Invalid scorer result','output':stored},files)
            raise ValueError('A valid finite score is required; failed scoring is not a wrong answer') from exc
        scorer_files={}
        for arg in s['config']['scorer'] or []:
            candidate=Path(arg)
            if not candidate.is_absolute():candidate=Path(s['config']['project'])/candidate
            if candidate.is_file():scorer_files[str(candidate.resolve())]=file_hash(candidate)
        row={'request_id':request_id,'scorer_files':scorer_files,'scorer_authorization':scorer_info['fingerprint'] if scorer_info else None,'score':value,'feedback':fb,'success':ok,'output':stored,'model':model,'effort':effort,'runtime':runtime,'trace':trace_record,'recorded_at':now()}
        return _status(root,_advance(root,_event(root,s,'result',row,files)))


def learn(root,request_id,patterns_file):
    data=read(patterns_file)
    if not isinstance(data,dict) or not isinstance(data.get('patterns'),list):raise ValueError('Provide a patterns JSON array')
    with locked(root) as root:
        s=_load(root);req=_request(s,request_id,'maintainer')
        if req['status']=='complete':
            if file_hash(patterns_file)!=req['submission']['sha256']:raise ValueError('Completed Wiki submission differs')
            return _status(root,s)
        context=read(root/req['context_file']);allowed={x['source_id'] for x in context['training_records']}|{x['id'] for x in context['human_feedback']}|{x['source_id'] for x in context['wiki'].values()}
        patterns={}
        for item in data['patterns']:
            name=item.get('name');content=item.get('content');sources=item.get('sources',[])
            if not isinstance(name,str) or not name.strip() or not isinstance(content,str) or not content.strip():raise ValueError('Pattern name and content are required')
            if not isinstance(sources,list) or not sources or any(x not in allowed for x in sources):raise ValueError('Cite permitted training request or human-feedback IDs')
            patterns[name]={'content':content,'sources':sources}
        stored,p=_store_file(root,patterns_file,'patterns.json')
        s=_event(root,s,'wiki',{'request_id':request_id,'patterns':patterns,'submission':stored},[p]);_wiki_view(root,s)
        return _status(root,s)


def propose(root,request_id,skill=None,note='',no_action=False):
    if (skill is None)==(not no_action):raise ValueError('Provide a skill file or no_action, exclusively')
    with locked(root) as root:
        s=_load(root);req=_request(s,request_id,'proposer')
        if req['status']=='complete':
            previous=req['proposal']
            if previous['no_action']!=no_action or previous['note']!=note or skill and file_hash(skill)!=previous['skill']['sha256']:raise ValueError('Completed proposal differs')
            return _status(root,s)
        files=[];stored=None
        if skill:
            if not Path(skill).read_text(encoding='utf-8').strip():raise ValueError('Skill must not be empty')
            stored,p=_store_file(root,skill,'SKILL.md');files=[p]
        s=_event(root,s,'proposal',{'request_id':request_id,'skill':stored,'note':note,'no_action':no_action},files)
        return _status(root,_advance(root,s))


def feedback(root,text,source=None):
    if not text.strip():raise ValueError('Feedback must not be blank')
    with locked(root) as root:
        s=_load(root);fid='feedback-'+uuid4().hex[:12];p=root/'feedback'/(fid+'.md');p.parent.mkdir(exist_ok=True);p.write_text(text,encoding='utf-8')
        value={'id':fid,'text':text,'source':source,'origin':'user_feedback','file':p.relative_to(root).as_posix(),'at':now()}
        s=_event(root,s,'feedback',value,[p]);_wiki_view(root,s);return value


def retry(root,request_id):
    with locked(root) as root:
        s=_load(root)
        if s['requests'].get(request_id,{}).get('status')!='failed':raise ValueError('Only a recorded failed request can be retried')
        return _status(root,_event(root,s,'retry',{'request_id':request_id}))


def export(root,destination):
    root=Path(root).resolve();s=_load(root);skill=s['current_skill']
    if not skill:raise ValueError('No retained skill yet; inspect the Wiki and candidate history')
    destination=Path(destination).resolve()
    if destination==root or destination.is_relative_to(root):raise ValueError('Export outside the workflow workspace')
    if destination.exists() and any(destination.iterdir()):raise ValueError('Export destination must be empty')
    destination.mkdir(parents=True,exist_ok=True);shutil.copy2(root/skill['file'],destination/'SKILL.md')
    write(destination/'provenance.json',{'workspace_fingerprint':digest(s['config']),'skill_sha256':skill['sha256'],'score':s['best_score'],'direction':s['config']['direction'],'history':[{k:g[k] for k in ('round','accepted','verdict','incumbent_score','candidate_score','improvement')} for g in s['history']]},immutable=True)
    return {'skill':str(destination/'SKILL.md'),'sha256':skill['sha256'],'score':s['best_score']}


def _status(root,s):
    current=s['current_skill'];failed=[r['id'] for r in s['requests'].values() if r['status']=='failed']
    return {'schema_version':SCHEMA,'workspace':str(root),'phase':'needs_attention' if failed else s['phase'],
            'round':min(s['round'],s['config']['rounds']),'rounds':s['config']['rounds'],'best_score':s['best_score'],
            'direction':s['config']['direction'],'skill':str(root/current['file']) if current else None,
            'completed_tasks':len(s['results']),'pending_requests':[r['id'] for r in s['requests'].values() if r['status']=='pending'],
            'failed_requests':failed,'wiki':str(root/'wiki/index.md'),'feedback_count':len(s['feedback']),'history':s['history'],
            'execution':'host_agent','model':'caller_selected','environment':'host_default'}


def status(root):
    root=Path(root).resolve();return _status(root,_load(root))


def capabilities():
    return {'product':{'execution':'host_agent','model':'caller_selected','environment':'host_default',
            'platforms':['macOS','Linux','Windows'],'scoring':'finite numeric scores; maximize or minimize',
            'hard_sample_limit':None,'hard_round_limit':None,'external_scorer':'JSON stdin/stdout command',
            'scorer_authorization':'Local fingerprint receipt; never imported from a workspace',
            'commands':['start','tasks','next','scorer','record','learn','propose','feedback','retry','export','status']},
            'research':{'spreadsheet-study':'Separate macOS isolated Luna/high research/integration path',
                        'evolve':'Legacy Codex-backed domain evolution'},
            'available_executables':{n:shutil.which(n) for n in ('python','python3','codex','claude')}}


def scorer_inspect(root):
    from .scorer_trust import describe
    root=Path(root).resolve();return describe(root,_load(root)['config'])


def scorer_trust(root,fingerprint):
    from .scorer_trust import approve
    with locked(root) as root:return approve(root,_load(root)['config'],fingerprint)
