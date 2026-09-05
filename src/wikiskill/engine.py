"""A resumable, domain-independent validation-gated evolution driver.

The append-only event ledger is authoritative. Each inference attempt has a
fresh directory. Completed task rows are projections, not the only raw record.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import json
import shutil
import threading

from .k4_lock import workspace_lock
from .settings import RESOURCES
from .officeqa.loop import eq4_accepted, mean_accuracy
from .officeqa.wiki_agents import build_maintainer, build_proposer
from .wiki import append_skill_impact, SkillImpactEntry

EMPTY_SHA = sha256(b'').hexdigest()
INFRA = {'exec_failed', 'exec_raised', 'score_failed', 'model_identity'}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')
    temporary.replace(path)


def read(path):
    return json.loads(Path(path).read_text())


def append(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, default=str) + '\n')
        handle.flush()


def events(root):
    p = root / 'events.jsonl'
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()] if p.exists() else []


def state(root):
    manifest = read(root / 'manifest.json')
    result = {'workspace': str(root), 'domain': manifest['domain'], 'model': manifest['model'],
              'r_best': None, 'next_iteration': 1, 'skill': 'skills/S0.md', 'skill_sha256': EMPTY_SHA,
              'history': [], 'status': 'initialized'}
    for e in events(root):
        if e['type'] == 'baseline':
            result.update(r_best=e['score'], status='evolving')
        elif e['type'] == 'gate':
            result['history'].append(e)
            result['next_iteration'] = e['iteration'] + 1
            if e['accepted']:
                result.update(r_best=e['candidate_score'], skill=e['skill'], skill_sha256=e['skill_sha256'])
    if result['r_best'] == 1:
        result['status'] = 'early_stop_validation_ceiling'
    elif result['next_iteration'] > manifest['iterations']:
        result['status'] = 'evolution_complete'
    return result


def initialize(root, config):
    root = Path(root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(f'Workspace is not empty: {root}; use evolve to resume')
    if config['workers'] < 1 or config['iterations'] < 1 or config['timeout'] < 1:
        raise ValueError('workers, iterations and timeout must be positive')
    root.mkdir(parents=True, exist_ok=True)
    config = dict(config, created_at=now(), engine_version='0.1.0')
    template = 'officeqa' if config['domain'] in {'officeqa', 'officeqa-retrieval', 'demo'} else config['domain']
    shutil.copytree(RESOURCES / template / 'wiki', root / 'wiki')
    (root / 'wiki/patterns').mkdir(exist_ok=True)
    (root / 'skills').mkdir()
    (root / 'skills/S0.md').write_text('')
    config['prompt_hashes'] = {p.name: sha256(p.read_bytes()).hexdigest() for p in (root/'wiki/prompts').glob('*.md')}
    save(root / 'manifest.json', config)
    save(root / 'manifest-lock.json', {'sha256': digest(config)})
    return state(root)


def load_domain(config, split):
    """Load train/val only. Held-out campaigns require an independent design."""
    if split not in {'train', 'val'}:
        raise ValueError('Evolution only reads train and val')
    domain = config['domain']
    if domain == 'demo':
        cases = [SimpleNamespace(uid=f'{split}-{i}', split=split) for i in range(4)]
        def rollout(case, **kw):
            skill = kw['skill_text']
            limit = 2 if skill == '# Demo useful skill\n' else 1 if not skill else 0
            return {'uid': case.uid, 'split': split, 'score': float(int(case.uid[-1]) < limit),
                    'model': 'offline-demo', 'reported_model': 'offline-demo', 'returncode': 0,
                    'fail_reason': '', 'has_final_answer_tag': True, 'predicted': 'synthetic',
                    'workspace': str(kw['workdir']), 'skill_sha256': sha256(skill.encode()).hexdigest()}
        return cases, rollout
    split_dir = Path(config['split_dir']) if config.get('split_dir') else RESOURCES / ('officeqa' if domain.startswith('officeqa') else domain) / ('id_split-v2' if domain == 'livemath' else 'id_split')
    if domain.startswith('officeqa'):
        from .officeqa.dataset import load_cases
        from .officeqa.rollout import rollout_case
        from .officeqa.retrieval import rollout_retrieval_case
        corpus = Path(config['corpus'])
        cases = load_cases(split, csv_path=Path(config['csv']), corpus_dir=corpus, split_dir=split_dir)
        if domain == 'officeqa-retrieval':
            from functools import partial
            return cases, partial(rollout_retrieval_case, corpus_dir=corpus/'treasury_bulletins_parsed/transformed' if (corpus/'treasury_bulletins_parsed/transformed').exists() else corpus)
        return cases, rollout_case
    from importlib import import_module
    from functools import partial
    adapter = import_module(f'wikiskill.benchmarks.{domain}')
    rollout = import_module(f'wikiskill.{domain}.rollout').rollout_case
    data = Path(config['data'])
    if domain == 'livemath':
        cases = adapter.load_month_files(sorted(data.glob('qa_*_final.json')))
    elif domain in {'sealqa', 'spreadsheet'}:
        cases = adapter.load_cases(data)
    else:
        # The packaged split records use paths relative to ALFWorld data root.
        items = read(split_dir / f'{split}.json')
        return [adapter.AlfWorldCase(uid=x['uid'],game_path=data/x['uid'],split=split) for x in items], partial(rollout,split=split)
    index = {c.uid: c for c in cases}
    ids = [x['uid'] if isinstance(x, dict) else x for x in read(split_dir / f'{split}.json')]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate split IDs')
    return [index[uid] for uid in ids], partial(rollout, split=split)


def batch(root, phase, config, cases, rollout, skill):
    """Resume valid rows, preserve every attempt, drain before surfacing errors."""
    directory = root / phase
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / 'outcomes.jsonl'
    identity = digest({'cases': [asdict(c) if is_dataclass(c) else vars(c) for c in cases],
                       'skill_sha256': sha256(skill.encode()).hexdigest(), 'config': config})
    binding = directory / 'binding.json'
    if binding.exists() and read(binding)['sha256'] != identity:
        raise ValueError('Dataset/config/skill changed on resume; use a new workspace')
    save(binding, {'sha256': identity})
    cached = {x['uid']: x for line in output.read_text().splitlines() if line.strip() for x in [json.loads(line)]} if output.exists() else {}
    ids = [c.uid for c in cases]
    if not cases or len(ids) != len(set(ids)) or set(cached)-set(ids):
        raise ValueError('Empty, duplicated, or unexpected task IDs')
    valid = {k:v for k,v in cached.items() if v.get('score') in (0,1) and v.get('fail_reason') not in INFRA}
    lock = threading.Lock()
    errors = []
    def update():
        save(root/'progress.json', {'updated_at':now(), 'phase':phase, 'completed':len(valid),
             'total':len(cases), 'errors':errors, 'status':'needs_attention' if errors else 'running'})
    def one(case):
        attempt = directory/'attempts'/uuid4().hex
        attempt.mkdir(parents=True)
        try:
            row = rollout(case, workdir=attempt, model=config['model'], reasoning_effort=config['effort'],
                          skill_text=skill, timeout_seconds=config['timeout'])
            row['split'] = case.split if hasattr(case,'split') else phase.rsplit('/',1)[-1].split('-')[0]
            if row.get('uid') != case.uid:
                raise ValueError('Rollout returned an unexpected task ID')
            save(attempt/'result.json', row)
            if row.get('score') not in (0,1) or row.get('fail_reason') in INFRA:
                raise RuntimeError(f"{case.uid}: {row.get('fail_reason', 'invalid score')}")
            return row
        except Exception as exc:
            save(attempt/'failure.json', {'type':type(exc).__name__, 'error':str(exc), 'at':now()})
            raise
    update()
    with ThreadPoolExecutor(max_workers=config['workers']) as pool:
        futures = {pool.submit(one,c):c.uid for c in cases if c.uid not in valid}
        for future in as_completed(futures):
            uid = futures[future]
            try:
                row = future.result()
                with lock:
                    valid[uid] = row
                    append(output, row)
            except Exception as exc:
                errors.append({'uid':uid, 'error':str(exc)})
            update()
    if errors:
        raise RuntimeError(f'{len(errors)} tasks need attention. Resolve infrastructure and resume; completed tasks are retained.')
    return [valid[uid] for uid in ids]


def evolve(root):
    root = Path(root).resolve()
    with workspace_lock(root):
        config = read(root/'manifest.json')
        if digest(config) != read(root/'manifest-lock.json')['sha256']:
            raise ValueError('Manifest changed; create a new experiment')
        for name,expected in config['prompt_hashes'].items():
            if sha256((root/'wiki/prompts'/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Agent prompt changed during evolution')
        sync_impacts(root)
        train, train_rollout = load_domain(config, 'train')
        val, val_rollout = load_domain(config, 'val')
        if set(c.uid for c in train) & set(c.uid for c in val):
            raise ValueError('Train/val overlap')
        current = state(root)
        if current['r_best'] is None:
            rows = batch(root,'baseline/val',config,val,val_rollout,'')
            append(root/'events.jsonl', {'type':'baseline','score':mean_accuracy(rows),'n':len(rows),'at':now()})
            current = state(root)
        while current['status'] == 'evolving':
            iteration = current['next_iteration']
            directory = root/f'iterations/{iteration:03d}'
            skill = (root/current['skill']).read_text()
            if sha256(skill.encode()).hexdigest() != current['skill_sha256']:
                raise ValueError('Incumbent skill changed')
            train_rows = batch(root,f'iterations/{iteration:03d}/train',config,train,train_rollout,skill)
            proposal_file = directory/'proposal.json'
            if not proposal_file.exists():
                if config['domain'] == 'demo':
                    candidate = '# Demo useful skill\n' if iteration==1 else '# Demo worse skill\n' if iteration==2 else ''
                    result = {'action':'skill' if candidate else 'no_action','skill_md':candidate,
                              'purpose':{'summary':'Deterministic offline contract demo','motivated_by_patterns':[]},'rationale':'synthetic demonstration'}
                    (root/'wiki/patterns/demo.md').write_text(f'# Demo observations\n\nIteration {iteration}; synthetic data.\n')
                else:
                    marker = directory/'maintainer-complete.json'
                    outcome_file = directory/'train/outcomes.jsonl'
                    if not marker.exists():
                        # Retain before/after Wiki snapshots for review and recovery.
                        backup = directory/'wiki-before'
                        if not backup.exists():shutil.copytree(root/'wiki',backup)
                        maintainer = build_maintainer(model=config['optimizer_model'],workdir=directory/'maintainer',reasoning_effort=config['optimizer_effort'])
                        maintainer([outcome_file],iteration=iteration,wiki_dir=root/'wiki')
                        save(marker, {'at':now()})
                    proposer = build_proposer(model=config['optimizer_model'],workdir=directory/'proposer',reasoning_effort=config['optimizer_effort'])
                    result = proposer(skill,[outcome_file],iteration=iteration,wiki_dir=root/'wiki').model_dump(mode='json')
                save(proposal_file,result)
            proposal = read(proposal_file)
            candidate = proposal['skill_md']
            score = None
            if proposal['action'] == 'skill':
                rows = batch(root,f'iterations/{iteration:03d}/val',config,val,val_rollout,candidate)
                score = mean_accuracy(rows)
            accepted = score is not None and eq4_accepted(score, current['r_best'])
            event = {'type':'gate','iteration':iteration,'at':now(),'accepted':accepted,
                     'verdict':'ACCEPT' if accepted else 'NOT_GATED' if score is None else 'REJECT',
                     'incumbent_score':current['r_best'],'candidate_score':score,
                     'skill_sha256':sha256(candidate.encode()).hexdigest(),
                     'skill':f'skills/iteration-{iteration:03d}.md' if accepted else current['skill']}
            if accepted:
                target = root/event['skill']
                if target.exists() and target.read_text()!=candidate:raise ValueError('Frozen skill mismatch')
                target.write_text(candidate)
            # Model-facing impact contains accepted and rejected proposals alike.
            import difflib
            impact = SkillImpactEntry(schema_version='wikiskill.skill_impact.v1',iteration=iteration,
                recorded_at=event['at'],prereg={'target_component':'paper_eq4','minimum_effect':1,
                'protocol_sha256':digest(config),'pair_id':f'{config["domain"]}-it{iteration}'},
                proposal_kind=proposal['action'],skill_sha256=event['skill_sha256'],
                purpose_summary=proposal.get('purpose',{}).get('summary',''),
                motivated_by_patterns=proposal.get('purpose',{}).get('motivated_by_patterns',[]),
                unified_diff='' if proposal['action']=='no_action' else ''.join(difflib.unified_diff(skill.splitlines(True),candidate.splitlines(True))),
                incumbent_skill_sha256=current['skill_sha256'],incumbent_descriptive={'r_best':current['r_best']},
                candidate_descriptive={'accuracy':score} if score is not None else {},
                gate_verdict=event['verdict'],accepted=accepted)
            event['impact'] = impact.model_dump(mode='json')
            append(root/'events.jsonl',event)
            sync_impacts(root)
            current=state(root)
        save(root/'progress.json',{'updated_at':now(),'status':current['status']})
        return current


def sync_impacts(root):
    """Repair the agent-facing projection from committed gate events on resume."""
    from .wiki import load_skill_impacts
    path=root/'wiki/skill-impact.md'
    present={(e.prereg.pair_id,e.recorded_at) for e in load_skill_impacts(path)}
    for event in events(root):
        payload=event.get('impact')
        if payload and (payload['prereg']['pair_id'],payload['recorded_at']) not in present:
            entry=SkillImpactEntry.model_validate(payload)
            append_skill_impact(path,entry)
            present.add((entry.prereg.pair_id,entry.recorded_at))
