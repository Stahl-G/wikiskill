from pathlib import Path
import pytest
from wikiskill.paper_alignment.contracts import canonical_pattern, wiki_update, read_wiki, ContractError


@pytest.mark.parametrize('name,expected', [('foo','foo.md'),('foo_bar','foo_bar.md'),('foo-bar.md','foo-bar.md'),('wiki/patterns/Table_Check.MD','Table_Check.md'),('patterns/月份 对齐','月份 对齐.md')])
def test_harmless_name_styles_are_normalized(name,expected):
    assert canonical_pattern(name)==expected


def test_complete_multi_pattern_submission_keeps_all_content():
    names=['relative-glob.md','answer_shape.md','table-check.md','interval-endpoint','midpoint_change']
    contents=[f'Unchanged research content {i}.' for i in range(5)]
    p={'create_patterns':[{'name':name,'content':body} for name,body in zip(names,contents)],'update_patterns':[],
       'update_index':'\n'.join(f'- [Pattern](wiki/patterns/{name})' for name in names),'append_log':'Five findings.'}
    normalized,wiki=wiki_update(p,{})
    assert len(normalized['create_patterns'])==5
    assert [item['content'] for item in normalized['create_patterns']]==contents
    assert 'patterns/interval-endpoint.md' in wiki and 'patterns/midpoint_change.md' in wiki
    assert 'wiki/patterns/interval-endpoint.md)' in wiki['index.md']


@pytest.mark.parametrize('name',['../escape','/absolute','wiki/patterns/../../escape','foo\\bar','C:outside','..','bad\x00name'])
def test_path_escape_is_not_a_filename_style(name):
    with pytest.raises(ContractError):canonical_pattern(name)


def test_alias_collision_cannot_overwrite_a_pattern():
    p={'create_patterns':[{'name':'foo','content':'first'},{'name':'foo.md','content':'second'}],
       'update_patterns':[],'update_index':'foo','append_log':'test'}
    with pytest.raises(ContractError,match='Duplicate'):wiki_update(p,{})
    p['create_patterns']=[{'name':'FOO','content':'overwrite'}]
    with pytest.raises(ContractError,match='overwrite'):wiki_update(p,{'patterns/foo.md':'original'})


def test_existing_extensionless_file_can_be_read_and_updated(tmp_path):
    (tmp_path/'patterns').mkdir();(tmp_path/'patterns/old_note').write_text('Original body.')
    existing=read_wiki(tmp_path)
    p={'create_patterns':[],'update_patterns':[{'name':'old_note.md','edits':[{'op':'append','content':'More evidence.'}]}],
       'update_index':'- [old](wiki/patterns/old_note.md)','append_log':'Appended.'}
    _,wiki=wiki_update(p,existing)
    assert wiki['patterns/old_note']=='Original body.\n\nMore evidence.\n'
    assert 'patterns/old_note.md' not in wiki
