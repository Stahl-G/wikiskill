import json
import pytest
from wikiskill.paper_alignment.outputs import maintainer_submission
from wikiskill.paper_alignment.contracts import wiki_update, ContractError
from wikiskill.skill_proposer import ProposerContractError


@pytest.mark.parametrize('fenced',[False,True])
def test_direct_json_uses_the_same_contract_as_finish(fenced):
    wiki={'index.md':'# Wiki','log.md':'# Log','skill-impact.md':'# Impact'}
    value={'create_patterns':[{'name':'period-check','content':'Verify both period labels.'}],
           'update_patterns':[],'update_index':'# Wiki\n- [period-check](wiki/patterns/period-check.md): Verify period labels.','append_log':'Reviewed traces.'}
    text=json.dumps(value)
    if fenced:text='```json\n'+text+'\n```'
    assert maintainer_submission(text,wiki)['proposal']==wiki_update(value,wiki)[0]


@pytest.mark.parametrize('text',['', 'Done.', '{"action":"no_action"}', '{"create_patterns":[]}'])
def test_no_silent_success_for_missing_or_wrong_role_output(text):
    with pytest.raises((ContractError,ProposerContractError)):
        maintainer_submission(text,{'index.md':'# Wiki'})
