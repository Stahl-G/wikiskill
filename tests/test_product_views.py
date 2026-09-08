import json
from pathlib import Path

from wikiskill import product as p
from wikiskill import product_views as views
from wikiskill.cli import main
from test_product import tasks, finish_tasks, learn_propose


def test_reports_follow_incumbent_and_do_not_change_journal(tmp_path):
    root=tmp_path/'flow'
    p.start(root,tasks=tasks(tmp_path,n=1),rounds=3)
    finish_tasks(root,tmp_path,2);finish_tasks(root,tmp_path,2)
    learn_propose(root,tmp_path,body='first');finish_tasks(root,tmp_path,4)
    finish_tasks(root,tmp_path,4);learn_propose(root,tmp_path,body='second');finish_tasks(root,tmp_path,3)
    finish_tasks(root,tmp_path,4);learn_propose(root,tmp_path,no_action=True)
    before={f.name:f.read_bytes() for f in (root/'events').iterdir()}
    r=views.report(root)
    assert r['baseline_score']==2 and r['retained_score']==4
    assert [g['verdict'] for g in r['rounds']]==['ACCEPT','REJECT','NO_ACTION']
    assert r['rounds'][1]['pairs'][0]=={'id':'validation:0','incumbent':4,'candidate':3,'outcome':'regressed'}
    assert '-first' in r['rounds'][1]['diff'] and '+second' in r['rounds'][1]['diff']
    assert not r['rounds'][2]['pairs'] and r['rounds'][2]['candidate_score'] is None
    assert 'NO_ACTION' in views.report_markdown(r)
    assert {f.name:f.read_bytes() for f in (root/'events').iterdir()}==before


def test_readiness_has_no_dispatch_or_scorer_side_effects(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'trust'))
    source=tmp_path/'source.txt';source.write_text('input')
    f=tasks(tmp_path,n=1);data=json.loads(f.read_text())
    for split,rows in data.items():rows[0].update(files=['source.txt'],group='source-family')
    f.write_text(json.dumps(data))
    root=tmp_path/'flow'
    import sys
    p.start(root,tasks=f,scorer=[sys.executable,'-c','raise Exception("must not run")'])
    result=views.preflight(root)
    assert not result['ready'] and len(result['shared_sources'])==2
    assert not p.status(root)['pending_requests']
    assert main(['preflight',str(root)])==2
    capsys.readouterr()
    p.scorer_trust(root,p.scorer_inspect(root)['fingerprint'])
    assert views.preflight(root)['ready']
    source.unlink()
    assert views.preflight(root)['missing_files']==[str(source)]
    assert main(['status',str(root),'--human'])==0
    assert '0/1 completed' in capsys.readouterr().out
    assert main(['doctor'])==0
    assert 'Stahl-G/wikiskill' in capsys.readouterr().out


def test_partial_minimize_and_failed_status(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=2),direction='minimize')
    req=p.next_work(root)['requests'][0]
    output=tmp_path/'out';output.write_text('actual')
    p.record(root,req['id'],output,score=1)
    assert views.report(root)['baseline_score'] is None
    req=p.next_work(root)['requests'][0]
    p.record(root,req['id'],error='tool unavailable')
    s=p.status(root)
    assert s['progress']['completed']==1 and len(s['failures'])==1
    assert 'tool unavailable' in views.status_text(s)
    assert not views.preflight(root)['ready']
    p.retry(root,req['id']);req=p.next_work(root)['requests'][0];p.record(root,req['id'],output,score=1)
    finish_tasks(root,tmp_path,1);learn_propose(root,tmp_path);finish_tasks(root,tmp_path,0)
    r=views.report(root)
    assert r['rounds'][0]['pairs'][0]['outcome']=='improved'
    assert main(['report',str(root),'--format','json'])==0


def test_changed_task_input_blocks_work_but_not_reports(tmp_path):
    f=tasks(tmp_path,n=1);data=json.loads(f.read_text());source=tmp_path/'input';source.write_text('original')
    data['validation'][0]['files']=[str(source)];f.write_text(json.dumps(data))
    root=tmp_path/'flow';p.start(root,tasks=f);req=p.next_work(root)['requests'][0]
    assert 'file_sha256' not in req['task']
    source.write_text('changed')
    import pytest
    with pytest.raises(ValueError,match='Task input changed'):p.next_work(root)
    output=tmp_path/'out';output.write_text('output')
    with pytest.raises(ValueError,match='Task input changed'):p.record(root,req['id'],output,score=1)
    assert not views.preflight(root)['ready'] and views.report(root)['phase']=='baseline'
    source.write_text('original');p.record(root,req['id'],output,score=1)
    assert p.status(root)['best_score']==1


def test_trust_setup_permission_failure_has_recovery_without_restart(tmp_path,monkeypatch):
    import sys
    from unittest.mock import patch
    denied=tmp_path/'denied-trust';monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(denied))
    original_mkdir=Path.mkdir
    def mkdir(path,*args,**kwargs):
        if path==denied:raise PermissionError('test host restriction')
        return original_mkdir(path,*args,**kwargs)
    root=tmp_path/'flow'
    import pytest
    with patch.object(Path,'mkdir',mkdir):
        with pytest.raises(RuntimeError,match='WIKISKILL_TRUST_DIR'):
            p.start(root,tasks=tasks(tmp_path,n=1),scorer=[sys.executable,'-c','print(\'{"score": 1}\')'],trust_scorer=True)
    assert (root/'config.json').exists()
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'writable-trust'))
    p.scorer_trust(root,p.scorer_inspect(root)['fingerprint'])
    assert views.preflight(root)['ready']
    assert len(p.next_work(root)['requests'])==1
