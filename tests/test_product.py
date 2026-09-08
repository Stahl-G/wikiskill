import json
import sys
from pathlib import Path
import pytest
from wikiskill import product as p
from wikiskill.cli import main


@pytest.fixture(autouse=True)
def private_trust_store(tmp_path,monkeypatch):
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'local-trust'))


def tasks(tmp_path,n=2):
    f=tmp_path/'tasks.json'
    f.write_text(json.dumps({split:[{'id':f'{split}:{i}','instruction':'Summarize the input','input':'ticket text','reference':'reserved evaluation material'} for i in range(n)] for split in ('train','validation')}))
    return f


def finish_tasks(root,tmp_path,score):
    work=p.next_work(root,count=100)
    for r in work['requests']:
        assert 'reference' not in r['task']
        out=tmp_path/(r['id']+'.txt');out.write_text('actual output')
        p.record(root,r['id'],out,score=score,feedback='Measured by the test fixture',model='arbitrary-model',runtime='arbitrary-host')
    return p.status(root)


def learn_propose(root,tmp_path,body='# Candidate',no_action=False):
    r=p.next_work(root)['requests'][0];ctx=p.read(root/r['context_file'])
    assert r['kind']=='maintainer' and all(x['task']['split']=='train' for x in ctx['training_records'])
    src=ctx['training_records'][0]['source_id']
    f=tmp_path/('patterns-'+r['id']+'.json');f.write_text(json.dumps({'patterns':[{'name':'Readable topic / no filename restriction','content':'Check the requested content before delivery.','sources':[src]}]}))
    p.learn(root,r['id'],f)
    r=p.next_work(root)['requests'][0];assert r['kind']=='proposer'
    f=tmp_path/('candidate-'+r['id']+'.txt');f.write_text(body)
    p.propose(root,r['id'],None if no_action else f,no_action=no_action)
    return r,f


def test_generic_two_rounds_continuous_scores_and_wiki_retained(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path),rounds=2)
    note=p.feedback(root,'Please make the result easier to check.')
    finish_tasks(root,tmp_path,20.0);finish_tasks(root,tmp_path,15.0)
    learn_propose(root,tmp_path);finish_tasks(root,tmp_path,25.0)
    assert p.status(root)['history'][0]['accepted']
    first=p.status(root)['skill']
    finish_tasks(root,tmp_path,22.0);learn_propose(root,tmp_path,body='# Worse');finish_tasks(root,tmp_path,21.0)
    s=p.next_work(root);assert s['phase']=='complete' and s['best_score']==25.0 and s['skill']==first
    assert [g['verdict'] for g in s['history']]==['ACCEPT','REJECT']
    assert (root/'feedback'/f'{note["id"]}.md').read_text()=='Please make the result easier to check.'
    assert 'Readable topic' in (root/'wiki/index.md').read_text()
    before=list((root/'events').glob('*.json'));assert p.next_work(root)['phase']=='complete';assert list((root/'events').glob('*.json'))==before
    exported=p.export(root,tmp_path/'exported');assert Path(exported['skill']).read_text()=='# Candidate'


def test_minimize_tie_and_no_action(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path),direction='minimize',rounds=2)
    finish_tasks(root,tmp_path,10);finish_tasks(root,tmp_path,9);learn_propose(root,tmp_path);finish_tasks(root,tmp_path,10)
    assert p.status(root)['history'][0]['verdict']=='REJECT'
    finish_tasks(root,tmp_path,8);learn_propose(root,tmp_path,no_action=True)
    assert p.status(root)['phase']=='complete' and p.status(root)['history'][-1]['verdict']=='NO_ACTION'
    with pytest.raises(ValueError,match='No retained'):p.export(root,tmp_path/'exported')


def test_no_research_size_or_model_cap_and_feedback_without_tasks(tmp_path):
    root=tmp_path/'notes';p.start(root,rounds=12);p.feedback(root,'A direct human observation')
    assert p.next_work(root)['phase']=='needs_tasks'
    p.set_tasks(root,tasks(tmp_path,n=30));w=p.next_work(root,count=20)
    assert len(w['requests'])==20 and all(r['model']=='caller_selected' for r in w['requests'])
    assert p.capabilities()['product']['hard_sample_limit'] is None
    with pytest.raises(ValueError):p.set_tasks(root,tasks(tmp_path))


def test_external_scorer_failure_retains_output_and_explicit_retry(tmp_path):
    grader=tmp_path/'grade.py';grader.write_text('raise SystemExit(2)')
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1),scorer=[sys.executable,str(grader)],project=tmp_path,trust_scorer=True)
    req=p.next_work(root)['requests'][0];out=tmp_path/'answer.txt';out.write_text('answer')
    with pytest.raises(RuntimeError,match='Scoring failed'):p.record(root,req['id'],out)
    assert p.next_work(root)['phase']=='needs_attention'
    assert len(list((root/'artifacts').glob('*/answer.txt')))==1
    p.retry(root,req['id']);new=p.next_work(root)['requests'][0]
    assert new['id']!=req['id'] and new['retry_of']==req['id'] and new['previous_output']
    grader.write_text('import sys,json\nx=json.load(sys.stdin)\nassert x["task"]["reference"]\nprint(json.dumps({"score": 3.5, "feedback":"graded", "success":True}))')
    p.scorer_trust(root,p.scorer_inspect(root)['fingerprint'])
    p.record(root,new['id'],root/new['previous_output']['file'])
    assert p.status(root)['best_score']==3.5


def test_invalid_score_and_mutated_records_fail(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1));req=p.next_work(root)['requests'][0]
    out=tmp_path/'answer';out.write_text('answer')
    with pytest.raises(ValueError,match='finite score'):p.record(root,req['id'],out,score=float('nan'))
    assert p.status(root)['phase']=='needs_attention'
    p.retry(root,req['id']);req=p.next_work(root)['requests'][0];p.record(root,req['id'],out,score=.25)
    p.record(root,req['id'],out,score=.25)
    with pytest.raises(ValueError,match='score differs'):p.record(root,req['id'],out,score=.5)
    f=next((root/'artifacts').glob('*/answer'));f.write_text('tampered')
    with pytest.raises(ValueError,match='artifact changed'):p.status(root)


def test_pattern_cannot_cite_validation_and_proposal_is_immutable(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1));finish_tasks(root,tmp_path,0);finish_tasks(root,tmp_path,0)
    req=p.next_work(root)['requests'][0];s=p._load(root);vid=next(rid for rid,r in s['requests'].items() if r['phase']=='baseline')
    f=tmp_path/'patterns.json';f.write_text(json.dumps({'patterns':[{'name':'x','content':'lesson','sources':[vid]}]}))
    with pytest.raises(ValueError,match='training request'):p.learn(root,req['id'],f)
    q,skill=learn_propose(root,tmp_path)
    skill.write_text('# Changed')
    with pytest.raises(ValueError,match='proposal differs'):p.propose(root,q['id'],skill)


def test_product_cli_uses_host_environment_without_legacy_engine(tmp_path,capsys):
    assert main(['capabilities'])==0;assert 'host_default' in capsys.readouterr().out
    assert main(['start',str(tmp_path/'flow'),'--tasks',str(tasks(tmp_path)),'--rounds','7'])==0
    assert main(['status',str(tmp_path/'flow')])==0
    assert main(['feedback',str(tmp_path/'flow'),'--text','Use fewer generic claims'])==0
    assert main(['next',str(tmp_path/'flow')])==0


def test_lock_blocks_second_writer(tmp_path):
    with p.locked(tmp_path):
        with pytest.raises(RuntimeError,match='Another writer'):
            with p.locked(tmp_path):pass


def test_new_task_set_can_carry_skill_wiki_and_feedback(tmp_path):
    first=tmp_path/'first';p.start(first,tasks=tasks(tmp_path,n=1));p.feedback(first,'A reusable preference')
    finish_tasks(first,tmp_path,0);finish_tasks(first,tmp_path,1);learn_propose(first,tmp_path);finish_tasks(first,tmp_path,1)
    second=tmp_path/'second';p.start(second,tasks=tasks(tmp_path,n=3),from_workspace=first)
    s=p.status(second);assert s['feedback_count']==1 and s['skill'] and s['best_score'] is None
    assert 'Readable topic' in (second/'wiki/index.md').read_text()
    assert Path(s['skill']).read_text()=='# Candidate'
    assert len(p.next_work(second,count=20)['requests'])==3


def test_scorer_requires_local_consent_and_change_invalidates_it(tmp_path):
    grader=tmp_path/'grade.py';marker=tmp_path/'called';grader.write_text('from pathlib import Path; Path('+repr(str(marker))+').touch(); import json; print(json.dumps(dict(score=1)))')
    root=tmp_path/'run';p.start(root,tasks=tasks(tmp_path,n=1),scorer=[sys.executable,str(grader)],project=tmp_path)
    assert p.next_work(root)['phase']=='needs_scorer_trust' and not marker.exists()
    info=p.scorer_inspect(root);assert info['command']==[sys.executable,str(grader)] and info['working_directory']==str(tmp_path)
    p.scorer_trust(root,info['fingerprint']);req=p.next_work(root)['requests'][0]
    output=tmp_path/'out.txt';output.write_text('output');p.record(root,req['id'],output);assert marker.exists()
    marker.unlink();req=p.next_work(root)['requests'][0];grader.write_text(grader.read_text()+'\n# changed')
    with pytest.raises(RuntimeError,match='authorization'):p.record(root,req['id'],output)
    assert not marker.exists()
    with pytest.raises(ValueError,match='changed'):p.scorer_trust(root,info['fingerprint'])
    p.scorer_trust(root,p.scorer_inspect(root)['fingerprint']);p.record(root,req['id'],output);assert marker.exists()


def test_scorer_approval_does_not_travel_with_workspace(tmp_path,monkeypatch):
    import shutil
    grader=tmp_path/'grade.py';grader.write_text('import json; print(json.dumps(dict(score=1)))')
    root=tmp_path/'original';p.start(root,tasks=tasks(tmp_path,n=1),scorer=[sys.executable,str(grader)],trust_scorer=True)
    other=tmp_path/'copied';shutil.copytree(root,other)
    assert p.next_work(other)['phase']=='needs_scorer_trust'
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'another-machine'))
    assert p.next_work(root)['phase']=='needs_scorer_trust'


def test_trusted_scorer_preserves_selected_python_environment(tmp_path):
    grader=tmp_path/'grade.py'
    grader.write_text('import sys,json; print(json.dumps({"score":1,"feedback":sys.prefix}))')
    root=tmp_path/'run';p.start(root,tasks=tasks(tmp_path,n=1),scorer=[sys.executable,str(grader)],trust_scorer=True)
    assert p.scorer_inspect(root)['resolved_executable']==str(Path(sys.executable).absolute())
    req=p.next_work(root)['requests'][0];out=tmp_path/'out';out.write_text('output');p.record(root,req['id'],out)
    assert p._load(root)['results'][req['id']]['feedback']==sys.prefix
