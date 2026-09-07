import json
import pytest
from wikiskill.officeqa.wiki_agents import stratified_sample,compact_event_log
from wikiskill.paper_alignment.contracts import proposal,ContractError,wiki_update


def test_portable_maintainer_reserves_successes():
    rows=[{'uid':str(i),'score':float(i>=20)} for i in range(50)]
    sampled=stratified_sample(rows,seed=7)
    assert len(sampled)==8
    assert sum(int(i)<20 for i in sampled)==5
    assert sum(int(i)>=20 for i in sampled)==3
    assert sampled==stratified_sample(list(reversed(rows)),seed=7)


def test_mcp_and_code_mode_do_not_disappear_from_trace_summary():
    events=[{'type':'item.completed','item':{'type':'mcp_tool_call','tool':'read','arguments':{'path':'corpus/a.txt'},'result':'evidence text'}},
            {'type':'response_item','payload':{'type':'custom_tool_call','name':'exec','input':'await tools.example()'}}]
    text=compact_event_log('\n'.join(json.dumps(e) for e in events))
    assert 'corpus/a.txt' in text and 'evidence text' in text and 'tools.example' in text


def test_paper_proposal_requires_four_traces_and_applicability():
    change={'action':'create','name':'safe_skill','skill_md':'---\nname: safe_skill\ndescription: Test\n---\n## When to Apply\nA\n## When NOT to Apply\nB\n## Instructions\nC',
            'purpose_md':'## Origin\nA\n## Patterns Addressed\nB\n## Evolution History\nC'}
    with pytest.raises(ContractError,match='four'):proposal(change,{},['a','b','c'])
    _,skills=proposal(change,{},['a','b','c','d']);assert 'safe_skill' in skills
    change['skill_md']=change['skill_md'].replace('## When NOT to Apply','## Other')
    with pytest.raises(ContractError):proposal(change,{},['a','b','c','d'])


def test_incremental_wiki_update_does_not_allow_path_escape():
    update={'create_patterns':[{'name':'../outside.md','content':'bad'}],'update_patterns':[],'update_index':'outside','append_log':'test'}
    with pytest.raises(ContractError):wiki_update(update,{})
