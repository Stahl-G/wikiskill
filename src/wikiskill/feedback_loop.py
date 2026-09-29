"""Public feedback-first extension to the WikiSkill product journal.

Reuse product/native-agent requests for Maintainer and Proposer. The host supplies
real paired results; deterministic selection records the lightweight policy.
The original numeric task loop remains unchanged.
"""
from pathlib import Path
from . import product as p


def begin(root, *, feedback, skill=None, rounds=1, previous=None, runtime='codex', requirement_sources=None):
    import tempfile
    from collections import Counter
    root=Path(root).resolve();root.parent.mkdir(parents=True,exist_ok=True)
    feedback=list(feedback)
    if any(not isinstance(item.get('text'),str) or not item['text'].strip() for item in feedback):
        raise ValueError('Feedback must not be blank')
    if any(x.get('learning_intent')=='explicit_requirement' and (x.get('origin')!='human' or not isinstance(x.get('source'),str) or not x['source'].strip()) for x in feedback):raise ValueError('Explicit requirements need a human origin and source ID')
    manifest=root.with_name('.'+root.name+'.feedback-init.json')
    intent={'feedback':feedback,'rounds':rounds,'runtime':runtime,
            'skill_sha256':p.file_hash(skill) if skill else None}
    if requirement_sources is not None:intent['requirement_sources']=sorted(set(requirement_sources))
    if manifest.exists():
        if p.read(manifest)!=intent:raise ValueError('Feedback initialization conditions changed; keep this study and start a new one')
    else:p.write(manifest,intent,immutable=True)
    if not (root/'config.json').exists():
        if root.exists() and any(root.iterdir()):raise ValueError('Incomplete unrecognized study; existing files were preserved')
        # Publish the complete base configuration atomically. An interrupted
        # staging directory is retained; it contains no executed model requests.
        staging=Path(tempfile.mkdtemp(prefix='.'+root.name+'-initializing-',dir=root.parent))
        p.start(staging,skill=skill,rounds=rounds,from_workspace=previous,agent_runtime=runtime)
        if root.exists():root.rmdir()  # Only the empty directory checked above.
        staging.rename(root)
    with p.locked(root):
        state=p._load(root)
        if state['config']['rounds']!=rounds:raise ValueError('Feedback rounds changed')
        if state.get('feedback_mode') and state['phase']!='baseline':
            p._wiki_view(root,state)
            return work(root)
        if state['requests'] or state['tasks']:raise ValueError('Existing study is not an unstarted feedback study')
        counts=Counter(p.digest({'text':row['text'],'source':row.get('source')}) for row in state['feedback'])
        wanted=Counter()
        for item in feedback:
            key=p.digest({'text':item['text'],'source':item.get('source')});wanted[key]+=1
            if counts[key]>=wanted[key]:continue
            fid='feedback-init-'+key[:24]+'-'+str(wanted[key])
            path=root/'feedback'/(fid+'.md');path.parent.mkdir(exist_ok=True)
            if path.exists() and path.read_text(encoding='utf-8')!=item['text']:raise ValueError('Initialization feedback artifact changed')
            path.write_text(item['text'],encoding='utf-8')
            value={'id':fid,'text':item['text'],'source':item.get('source'),'origin':item.get('origin','user_feedback'),
                   'learning_intent':item.get('learning_intent','feedback'),
                   'file':path.relative_to(root).as_posix(),'at':p.now()}
            state=p._event(root,state,'feedback',value,[path]);counts[key]+=1
        sources=sorted(set(requirement_sources)) if requirement_sources is not None else [x['source'] for x in feedback if x.get('origin')=='human' and x.get('learning_intent')=='explicit_requirement']
        allowed={x.get('source') for x in state['feedback'] if x.get('origin')=='human' and x.get('learning_intent')=='explicit_requirement'}
        if not set(sources)<=allowed:raise ValueError('Explicit requirement source is not recorded human intent')
        if not state.get('feedback_mode'):state=p._event(root,state,'feedback_mode',{'explicit_requirement_sources':sources})
        state=p._event(root,state,'phase',{'phase':'maintainer', **({'current_skill':None} if skill is None else {})})
        p._wiki_view(root,state)
    return work(root)


def skip(root, *, reason, cases):
    """An ineligible batch never creates a comparison or an adoption decision."""
    root=Path(root).resolve()
    with p.locked(root):
        state=p._load(root)
        if state['phase']!='complete':
            p._event(root,state,'phase',{'phase':'complete','comparison_skipped':{'reason':reason,'cases':cases}})
    return work(root)


def work(root):
    root=Path(root).resolve();s=p._load(root)
    if not s.get('feedback_mode'):raise ValueError('Not a feedback study')
    return {'phase':s['phase'],'round':s['round'],'rounds':s['config']['rounds'],
            'candidate':s['candidate'],'current_skill':s['current_skill'],
            'patterns':s['patterns'],'history':s['history'],'feedback':s['feedback'],
            'explicit_requirement_sources':s.get('explicit_requirement_sources',[]),
            'comparison_skipped':s.get('comparison_skipped')}


def finish(root, *, pairs, reason='', evidence_file=None):
    root=Path(root).resolve()
    with p.locked(root):
        s=p._load(root)
        if s['phase']!='validation' or not s['candidate']:raise ValueError('No candidate awaiting comparison')
        candidate=s['candidate'];no_action=candidate['no_action']
        if not no_action:
            if not pairs or len({x['case_id'] for x in pairs})!=len(pairs):raise ValueError('Provide distinct paired task results')
            if any(x.get('verdict') not in ('better','tie','worse') or not isinstance(x.get('regressions'),list) for x in pairs):
                raise ValueError('Each pair needs a verdict and explicit regressions')
        better=sum(x['verdict']=='better' for x in pairs)
        worse=sum(x['verdict']=='worse' for x in pairs)
        requirements=[x for x in s['feedback'] if x.get('source') in s.get('explicit_requirement_sources',[]) and x.get('learning_intent')=='explicit_requirement' and x.get('origin')=='human']
        explicit=bool(requirements)
        required_ids={x['source'] for x in requirements}
        if explicit and not no_action:
            for pair in pairs:
                checks=pair.get('requirement_checks',[])
                if (not isinstance(checks,list) or len(checks)!=len(required_ids)
                    or {x.get('source') for x in checks}!=required_ids
                    or any(type(x.get('fulfilled')) is not bool or not isinstance(x.get('evidence'),str) or not x['evidence'].strip() for x in checks)):
                    raise ValueError('Explicit requirements need complete evidence-backed checks')
        fulfilled=not explicit or (not no_action and all(c['fulfilled'] for pair in pairs for c in pair['requirement_checks']))
        accepted=not no_action and fulfilled and not any(x['regressions'] for x in pairs) and (worse==0 if explicit else better>worse)
        pending=explicit and not accepted

        files=[]
        if evidence_file:
            record,path=p._store_file(root,evidence_file,'comparison.json');files.append(path)
        else:record=None
        value={'round':s['round'],'accepted':accepted,'no_action':no_action,
               'verdict':'ACCEPT' if accepted else 'REVISION_REQUIRED' if pending else 'NO_ACTION' if no_action else 'REJECT',
               'requirements_pending':pending,'requirement_sources':sorted(required_ids),
               'skill':candidate['skill'] if accepted else s['current_skill'],
               'candidate_skill':candidate['skill'],'pairs':pairs,'reason':reason,
               'evidence':record,'incumbent_score':None,'candidate_score':None,'improvement':None,
               'policy':'explicit_human_requirement' if explicit else 'lightweight_pairwise'}
        p._event(root,s,'feedback_gate',value,files)
    return work(root)
