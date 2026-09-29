import json
import pytest
from wikiskill import feedback_loop as f, native_agents as n, product as p
from wikiskill.k4_lock import workspace_lock

REQUIREMENT={'text':'Always cite the filing page.','source':'comment-1','origin':'human','learning_intent':'explicit_requirement'}
NOTE={'text':'Too long.','source':'comment-2'}


@pytest.fixture(autouse=True)
def private_trust_store(tmp_path,monkeypatch):
    monkeypatch.setenv('WIKISKILL_TRUST_DIR',str(tmp_path/'local-trust'))


def learn_and_propose(root,tmp_path,body,agent):
    for kind in ('maintainer','proposer'):
        request=n.dispatch(root,'opencode')['handoffs'][0]
        n.bind(root,request['request_id'],f'{agent}-{kind}','opencode','fresh')
        rid=request['request_id'];assert p._load(root)['requests'][rid]['kind']==kind
        if kind=='maintainer':
            ctx=p.read(root/p._load(root)['requests'][rid]['context_file'])
            sources=[x['id'] for x in ctx['human_feedback']]
            patterns=tmp_path/f'{agent}-patterns.json';patterns.write_text(json.dumps({'patterns':[{'name':'Cite pages','content':'Cite the filing page.','sources':sources}]}))
            p.learn(root,rid,patterns)
        else:
            skill=tmp_path/f'{agent}-SKILL.md';skill.write_text(body,encoding='utf-8')
            p.propose(root,rid,skill)


def pair(case,verdict,fulfilled=True,regressions=()):
    return {'case_id':case,'verdict':verdict,'regressions':list(regressions),
            'requirement_checks':[{'source':'comment-1','fulfilled':fulfilled,'evidence':'Page 12 cited.' if fulfilled else 'No page cited.'}]}


def test_explicit_requirement_requires_revision_until_fulfilled(tmp_path):
    root=tmp_path/'study'
    assert f.begin(root,feedback=[REQUIREMENT,NOTE],rounds=2,runtime='opencode')['phase']=='maintainer'
    learn_and_propose(root,tmp_path,'# Cite pages\n',agent='a')
    with pytest.raises(ValueError,match='evidence-backed'):f.finish(root,pairs=[{'case_id':'c1','verdict':'better','regressions':[]}])
    state=f.finish(root,pairs=[pair('c1','better',fulfilled=False),pair('c2','tie')])
    assert state['history'][-1]['verdict']=='REVISION_REQUIRED' and state['phase']=='maintainer' and state['current_skill'] is None
    learn_and_propose(root,tmp_path,'# Cite pages\nName the page number.\n',agent='b')
    state=f.finish(root,pairs=[pair('c1','better'),pair('c2','tie')])
    assert state['history'][-1]['verdict']=='ACCEPT' and state['phase']=='complete'
    assert state['history'][-1]['policy']=='explicit_human_requirement'


def test_lightweight_policy_without_explicit_requirements(tmp_path):
    root=tmp_path/'study';f.begin(root,feedback=[NOTE],runtime='opencode')
    learn_and_propose(root,tmp_path,'# Shorter\n',agent='a')
    state=f.finish(root,pairs=[{'case_id':'c1','verdict':'better','regressions':[]},{'case_id':'c2','verdict':'tie','regressions':[]}])
    assert state['history'][-1]['verdict']=='ACCEPT' and state['history'][-1]['policy']=='lightweight_pairwise'


def test_begin_is_idempotent_and_frozen(tmp_path):
    root=tmp_path/'study'
    f.begin(root,feedback=[REQUIREMENT,NOTE],runtime='opencode')
    again=f.begin(root,feedback=[REQUIREMENT,NOTE],runtime='opencode')
    assert len(again['feedback'])==2 and again['explicit_requirement_sources']==['comment-1']
    with pytest.raises(ValueError,match='conditions changed'):f.begin(root,feedback=[NOTE],runtime='opencode')


@pytest.mark.parametrize('item',[{**REQUIREMENT,'origin':'model'},{**REQUIREMENT,'source':' '},{'text':'  '}])
def test_invalid_feedback_is_refused(tmp_path,item):
    with pytest.raises(ValueError):f.begin(tmp_path/'study',feedback=[item])


def test_skip_completes_without_comparison(tmp_path):
    root=tmp_path/'study';f.begin(root,feedback=[NOTE],runtime='opencode')
    state=f.skip(root,reason='no comparable sources',cases=['c1'])
    assert state['phase']=='complete' and state['comparison_skipped']=={'reason':'no comparable sources','cases':['c1']}
    assert state['history']==[]


def test_engine_workspace_lock_blocks_second_holder(tmp_path):
    with workspace_lock(tmp_path):
        with pytest.raises(RuntimeError,match='already running'):
            with workspace_lock(tmp_path):pass
    with workspace_lock(tmp_path):pass

