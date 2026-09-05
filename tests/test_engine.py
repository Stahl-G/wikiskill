from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from wikiskill import engine
from wikiskill.cli import main


def test_demo_uses_real_driver_and_resume_does_not_repeat(tmp_path):
    root=tmp_path/'demo'
    assert main(['demo',str(root)])==0
    before=(root/'events.jsonl').read_bytes()
    result=engine.evolve(root)
    assert result['r_best']==0.5
    assert [x['verdict'] for x in result['history']]==['ACCEPT','REJECT','NOT_GATED']
    assert (root/'skills/iteration-001.md').read_text()=='# Demo useful skill\n'
    assert not (root/'skills/iteration-002.md').exists()
    assert (root/'wiki/patterns/demo.md').exists()
    assert (root/'events.jsonl').read_bytes()==before
    # A missing derived impact projection can be recovered from commit events.
    (root/'wiki/skill-impact.md').unlink()
    engine.evolve(root)
    assert len(engine.events(root))==4
    assert (root/'wiki/skill-impact.md').read_text().count('```json')==3


def test_failed_attempt_is_retained_and_only_missing_task_resumes(tmp_path):
    calls=[]
    fail=True
    cases=[SimpleNamespace(uid=x,split='train') for x in ['a','b','c']]
    config={'model':'fake','effort':'none','timeout':2,'workers':2}
    def rollout(case,**kw):
        calls.append(case.uid)
        return {'uid':case.uid,'score':0 if case.uid=='b' else 1,'fail_reason':'exec_failed' if fail and case.uid=='b' else '', 'workspace':str(kw['workdir'])}
    with pytest.raises(RuntimeError):engine.batch(tmp_path,'iteration/train',config,cases,rollout,'')
    progress=engine.read(tmp_path/'progress.json')
    assert progress['completed']==2 and len(progress['errors'])==1
    assert len(list(tmp_path.glob('iteration/train/attempts/*/failure.json')))==1
    fail=False
    result=engine.batch(tmp_path,'iteration/train',config,cases,rollout,'')
    assert len(result)==3 and calls.count('a')==calls.count('c')==1 and calls.count('b')==2
    assert len(list(tmp_path.glob('iteration/train/attempts/*/result.json')))==4
    with pytest.raises(ValueError,match='changed on resume'):
        engine.batch(tmp_path,'iteration/train',config,cases,rollout,'different skill')


def test_manifest_mutation_refused(tmp_path):
    root=tmp_path/'demo'
    main(['demo',str(root)])
    config=engine.read(root/'manifest.json');config['model']='another-model';engine.save(root/'manifest.json',config)
    with pytest.raises(ValueError,match='Manifest changed'):engine.evolve(root)


def test_train_val_overlap_refused(tmp_path,monkeypatch):
    cfg={'domain':'demo','model':'offline-demo','optimizer_model':'offline-demo','effort':'none','optimizer_effort':'none','workers':1,'iterations':1,'timeout':1}
    engine.initialize(tmp_path,cfg)
    monkeypatch.setattr(engine,'load_domain',lambda *a:([SimpleNamespace(uid='same')],None))
    with pytest.raises(ValueError,match='overlap'):engine.evolve(tmp_path)


def test_packaged_results_recompute():
    from wikiskill.results import verify
    result=verify()
    assert result['verified'] and result['cells']
