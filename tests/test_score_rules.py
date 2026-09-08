import sys
import pytest
from wikiskill.score_rules import accepted
from wikiskill.officeqa.loop import mean_accuracy, eq4_accepted, eq4_guard
from wikiskill import product as p
from test_product import tasks


@pytest.mark.parametrize('bad',[None,True,'1',float('nan'),float('inf')])
def test_missing_invalid_score_never_becomes_zero_or_gate_win(bad):
    with pytest.raises(ValueError):mean_accuracy([{'score':bad}])
    with pytest.raises(ValueError):eq4_accepted(bad,0)
    with pytest.raises(ValueError):eq4_guard(0,bad)


def test_threshold_and_direction():
    assert not accepted(2,1,minimum=1)
    assert accepted(0,2,'minimize',minimum=1)
    assert mean_accuracy([{'score':0},{'score':1}])==.5


def test_checker_cannot_change_mid_comparison(tmp_path,monkeypatch):
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'trust'))
    grader=tmp_path/'grade.py';grader.write_text('print(\'{"score": 1}\')')
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1),scorer=[sys.executable,str(grader)],trust_scorer=True)
    req=p.next_work(root)['requests'][0];out=tmp_path/'out';out.write_text('output');p.record(root,req['id'],out)
    grader.write_text('print(\'{"score": 2}\')')
    p.scorer_trust(root,p.scorer_inspect(root)['fingerprint'])
    with pytest.raises(ValueError,match='consistent comparison'):p.next_work(root)
    assert p.status(root)['best_score']==1
