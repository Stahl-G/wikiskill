import json
import sys
from pathlib import Path
import pytest
from wikiskill import product as p
from wikiskill import native_agents as n
from test_product import tasks


def request(root, agent):
    handoff=n.dispatch(root,'codex')['handoffs'][0]
    n.bind(root,handoff['request_id'],agent,'codex','fresh')
    return handoff


def result(handoff, data):
    Path(handoff['result_file']).write_text(json.dumps(data))


def task(root, agent, score):
    h=request(root,agent)
    out=Path(h['output_directory'])/'answer';out.write_text('actual output')
    result(h,{'output':out.name})
    n.collect(root,h['request_id'],score=score,feedback='fixture evaluation')
    return h


def test_native_role_flow_and_context_boundaries(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1),agent_runtime='codex')
    h=n.dispatch(root,'codex')['handoffs'][0]
    payload=p.read(h['payload_file'])
    assert set(payload)=={'role','output_directory','task','skill'}
    assert 'reference' not in payload['task'] and 'phase' not in payload
    out=Path(h['output_directory'])/'answer';out.write_text('actual')
    with pytest.raises(ValueError,match='bind-agent'):p.record(root,h['request_id'],out,score=0)
    assert n.dispatch(root,'codex')['handoffs'][0]['payload_file']==h['payload_file']
    n.bind(root,h['request_id'],'baseline-1','codex','fresh');result(h,{'output':str(out)})
    n.collect(root,h['request_id'],score=0)
    # Repeated collection does not rescore or reinterpret scratch files.
    result(h,{'error':'changed scratch'});assert n.collect(root,h['request_id'])['best_score']==0
    train=task(root,'train-1',0)
    h=request(root,'maintainer-1');ctx=p.read(p.read(h['payload_file'])['context_file'])
    assert len(ctx['training_records'])==1 and ctx['training_records'][0]['source_id']==train['request_id']
    assert ctx['training_records'][0]['task']['reference']=='reserved evaluation material'
    assert not ctx['gate_history']
    result(h,{'patterns':[{'name':'lesson','content':'Use the task criteria.','sources':[train['request_id']]}]})
    n.collect(root,h['request_id'])
    h=request(root,'proposer-1');ctx=p.read(p.read(h['payload_file'])['context_file'])
    assert 'lesson' in ctx['wiki']
    skill=Path(h['output_directory'])/'any_filename';skill.write_text('# Check requirements')
    result(h,{'skill':str(skill),'note':'Use evidence'})
    n.collect(root,h['request_id'])
    task(root,'validation-1',1)
    assert p.status(root)['history'][0]['verdict']=='ACCEPT'
    assert len(p._load(root)['requests'])==5


def test_native_requires_fresh_ids_and_own_outputs(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1),agent_runtime='codex')
    with pytest.raises(ValueError,match='Runtime'):n.dispatch(root,'claude-code')
    h=n.dispatch(root,'codex')['handoffs'][0]
    with pytest.raises(ValueError,match='fresh'):n.bind(root,h['request_id'],'a','codex','fork')
    n.bind(root,h['request_id'],'a','codex','fresh')
    other=tmp_path/'other';other.write_text('other arm answer')
    result(h,{'output':str(other)})
    with pytest.raises(ValueError,match='this request'):n.collect(root,h['request_id'],score=1)
    n.fail(root,h['request_id'],'executor failed');p.retry(root,h['request_id'])
    second=n.dispatch(root,'codex')['handoffs'][0]
    with pytest.raises(ValueError,match='new subagent'):n.bind(root,second['request_id'],'a','codex','fresh')


def test_scoring_retry_reuses_original_execution(tmp_path,monkeypatch):
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'trust'))
    checker=tmp_path/'score.py';checker.write_text('raise SystemExit(1)')
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1),agent_runtime='codex',scorer=[sys.executable,str(checker)],trust_scorer=True)
    h=request(root,'actual-agent');out=Path(h['output_directory'])/'answer';out.write_text('saved')
    result(h,{'output':str(out)})
    with pytest.raises(RuntimeError):n.collect(root,h['request_id'])
    checker.write_text('print(\'{"score": 1}\')');p.scorer_trust(root,p.scorer_inspect(root)['fingerprint'])
    p.retry(root,h['request_id'])
    retry=n.dispatch(root,'codex')['handoffs'][0]
    assert retry['reused_from']==h['request_id'] and retry['delegation']['agent_id']=='actual-agent'
    assert 'payload_file' not in retry
    assert n.collect(root,retry['request_id'])['best_score']==1


def test_learning_failure_and_no_action(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1),agent_runtime='codex')
    task(root,'b',1);task(root,'t',1)
    h=request(root,'m');result(h,{'error':'agent interrupted'})
    assert n.collect(root,h['request_id'])['phase']=='needs_attention'
    p.retry(root,h['request_id']);h=request(root,'m2');result(h,{'patterns':[]});n.collect(root,h['request_id'])
    h=request(root,'p');result(h,{'no_action':True,'note':'No useful change'})
    assert n.collect(root,h['request_id'])['history'][0]['verdict']=='NO_ACTION'


def test_install_both_hosts_and_preserve_existing_configuration(tmp_path):
    import tomllib
    import yaml
    for runtime in n.RUNTIMES:
        project=tmp_path/runtime
        result=n.install(project,runtime)
        assert len(result['roles'])==3 and Path(result['entry_skill']).is_file()
        assert not n.install(project,runtime)['created']
        if runtime=='codex':
            paths=list((project/'.codex/agents').glob('*.toml'))
            for path in paths:
                config=tomllib.loads(path.read_text())
                assert set(config)=={'name','description','developer_instructions'}
        else:
            paths=list((project/'.claude/agents').glob('*.md'))
            for path in paths:
                config=yaml.safe_load(path.read_text().split('---')[1])
                assert config['model']=='inherit' and 'permissionMode' not in config
        assert len(paths)==3
        paths[0].write_text('user customized')
        with pytest.raises(ValueError,match='Existing host asset'):n.install(project,runtime)
        assert paths[0].read_text()=='user customized'


def test_dispatch_will_not_mix_direct_and_native_workflows(tmp_path):
    root=tmp_path/'direct';p.start(root,tasks=tasks(tmp_path,n=1))
    with pytest.raises(ValueError,match='--agent-runtime'):n.dispatch(root,'codex')
    assert not p.status(root)['pending_requests']
