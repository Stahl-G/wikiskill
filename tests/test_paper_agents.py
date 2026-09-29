import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from wikiskill import engine
from wikiskill.paper_alignment.agents import PaperAgents, paper_prompts, handoff, PROMPTS
from wikiskill.isolated.tools_server import RoleTools

SKILL='---\nname: compare_periods\ndescription: Verify period labels before comparison.\n---\n## When to Apply\nPeriod comparisons.\n## When NOT to Apply\nNo comparison requested.\n## Instructions\nRead both period labels before calculating the change.\n'
PURPOSE='## Origin\nSynthetic TRAIN traces.\n## Patterns Addressed\nPeriod alignment.\n## Evolution History\nInitial creation.\n'

@pytest.mark.parametrize('no_action',[False,True])
def test_original_engine_with_actual_paper_role_contracts(tmp_path,no_action):
    calls=[]
    def invoke(directory,payload,system,user,mode,model,effort):
        calls.append(mode)
        original=(PROMPTS/(mode+'.paper.md')).read_text().replace('{task_desc}','financial questions')
        assert system==original
        facts=json.loads(user);assert facts['executor_visibility']['wiki'] is False
        assert 'No action is allowed' not in user and 'must not be retried' not in user
        assert all(x['split']=='train' for x in json.loads(payload['trace-summary.json']))
        assert {'wiki/index.md','wiki/log.md','wiki/skill-impact.md'}<=set(payload)
        work=directory/'input';control=directory/'runtime';control.mkdir(parents=True)
        for name,text in payload.items():p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        server=RoleTools(work,control,mode,'python3');receipts=[]
        if mode=='maintainer':
            existing=json.loads(payload['skills.json'])
            value={'create_patterns':[] if (work/'wiki/patterns/periods.md').exists() else [{'name':'periods','content':'Read both period labels.'}],
                   'update_patterns':[],'update_index':'# Wiki\n- [periods](wiki/patterns/periods.md): Read period labels.','append_log':'Reviewed TRAIN.'}
        else:
            assert json.loads(payload['skills.json'])=={}
            for item in json.loads(payload['trace-summary.json'])[:4]:
                args={'path':item['path']};server.call('read_file',args);receipts.append({'tool':'read_file','arguments':args,'ok':True})
            value={'action':'no_action'} if no_action else {'action':'create','name':'compare_periods','skill_md':SKILL,'purpose_md':PURPOSE}
        server.call('finish',{'proposal':value});(control/'tool-events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in receipts));(control/'final.txt').write_text('Fixture submission.')
        return control
    agents=PaperAgents(invoke,seed=3)
    config={'domain':'synthetic-finance','model':'fixture','optimizer_model':'fixture','effort':'medium','optimizer_effort':'medium','workers':1,'iterations':4,'timeout':1}
    root=tmp_path/'study';engine.initialize(root,config,wiki_template='officeqa',agent_prompts=paper_prompts('financial questions'))
    def load(config,split):
        assert split in ('train','val')
        cases=[SimpleNamespace(uid=f'{split}-{i}',split=split) for i in range(4 if split=='train' else 2)]
        def rollout(case,**kw):
            archive=kw['workdir']/'runtime';archive.mkdir();(archive/'session.jsonl').write_text('')
            return {'uid':case.uid,'question':'Compare the two periods.','predicted':'fixture','workspace':str(kw['workdir']),'score':int(bool(kw['skill_text'])),'fail_reason':''}
        return cases,rollout
    state=engine.evolve(root,domain_loader=load,maintainer_factory=agents.maintainer_factory,proposer_factory=agents.proposer_factory)
    assert calls==['maintainer','proposer']*(4 if no_action else 1)
    assert [g['verdict'] for g in state['history']]==(['NOT_GATED']*4 if no_action else ['ACCEPT'])
    assert state['r_best']==(0 if no_action else 1)
    before=(root/'events.jsonl').read_bytes();engine.evolve(root,domain_loader=load,maintainer_factory=agents.maintainer_factory,proposer_factory=agents.proposer_factory);assert before==(root/'events.jsonl').read_bytes()

def test_learning_rejects_validation_records(tmp_path):
    p=tmp_path/'rows.jsonl';p.write_text(json.dumps({'uid':'reserved','split':'val'})+'\n')
    with pytest.raises(ValueError,match='TRAIN only'):PaperAgents(None)._rows([p])

def test_handoff_contains_state_not_outcome_instructions():
    value=json.loads(handoff(1,{}))
    assert value['active_skills_file']=='skills.json'
    assert value['executor_visibility']=={'wiki':False,'active_skill_names':[]}
    assert set(value)=={'iteration','wiki_index','skill_impact','active_skills_file','training_trace_index','executor_visibility'}
