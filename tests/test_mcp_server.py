import json
import sys
import pytest
from wikiskill import mcp_server as m


@pytest.fixture(autouse=True)
def private_trust_store(tmp_path,monkeypatch):
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'local-trust'))


def tasks(tmp_path):
    f=tmp_path/'tasks.json'
    f.write_text(json.dumps({split:[{'id':f'{split}:0','instruction':'Summarize the input','input':'ticket text','reference':'reserved'}] for split in ('train','validation')}))
    return str(f)


def finish(root,score):
    for r in m.next_work(root,count=10)['requests']:
        assert r['kind']=='task' and 'reference' not in r['task']
        m.record(root,r['id'],output_text='actual output',score=score,trace_text='steps taken',model='any-model')


def test_text_inputs_run_the_full_product_loop(tmp_path):
    root=str(tmp_path/'run');m.start(root,tasks=tasks(tmp_path))
    finish(root,1.0);finish(root,1.0)
    r=m.next_work(root)['requests'][0];assert r['kind']=='maintainer'
    source=json.loads((tmp_path/'run'/r['context_file']).read_text())['training_records'][0]['source_id']
    m.learn(root,r['id'],patterns={'patterns':[{'name':'Check delivery','content':'Re-read the output.','sources':[source]}]})
    r=m.next_work(root)['requests'][0];assert r['kind']=='proposer'
    m.propose(root,r['id'],skill_text='# Candidate\nRe-read the output.')
    finish(root,2.0)
    s=m.status(root);assert s['history'][0]['verdict']=='ACCEPT'
    assert m.report(root)['retained_score']==2.0
    exported=m.export(root,str(tmp_path/'out'))
    assert (tmp_path/'out').is_dir() and 'Re-read' in open(exported['skill']).read()


def test_ambiguous_submissions_are_rejected(tmp_path):
    root=str(tmp_path/'run');m.start(root,tasks=tasks(tmp_path))
    rid=m.next_work(root)['requests'][0]['id']
    with pytest.raises(ValueError,match='exactly one'):m.record(root,rid,score=1)
    with pytest.raises(ValueError,match='exactly one'):m.record(root,rid,output_text='a',output_path=str(tmp_path/'x'),score=1)
    with pytest.raises(ValueError,match='no_action'):m.propose(root,rid,skill_text='# x',no_action=True)
    with pytest.raises(ValueError,match='exactly one'):m.learn(root,rid)


def test_server_cannot_authorize_scorers_or_install_skills(tmp_path):
    names=set(m.TOOLS)
    assert 'wikiskill_next' in names and 'wikiskill_scorer_inspect' in names
    assert not any(word in name for name in names for word in ('trust','install','restore'))
    grader=tmp_path/'grade.py';marker=tmp_path/'called'
    grader.write_text('from pathlib import Path; Path('+repr(str(marker))+').touch(); print(\'{"score": 1}\')')
    root=str(tmp_path/'run');m.start(root,tasks=tasks(tmp_path),scorer=[sys.executable,str(grader)],project=str(tmp_path))
    assert m.next_work(root)['phase']=='needs_scorer_trust' and not marker.exists()
    assert m.scorer_inspect(root)['fingerprint']
    assert 'trust_scorer' not in m.start.__code__.co_varnames


def test_registered_mcp_tools_match_the_table():
    pytest.importorskip('mcp')
    import asyncio
    listed=asyncio.run(m.build_server().list_tools())
    assert {t.name for t in listed}==set(m.TOOLS)
    record=next(t for t in listed if t.name=='wikiskill_record')
    assert {'workspace','request','output_text','score'}<=set(record.inputSchema['properties'])
