"""Deterministic paper JSON contracts; roles submit content, controller applies."""
from pathlib import Path
import json
import re
import yaml


class ContractError(ValueError):
    pass


def canonical_pattern(name):
    if not isinstance(name,str):raise ContractError('Pattern name must be a string')
    if name.startswith('wiki/patterns/'):name=name[len('wiki/patterns/'):]
    elif name.startswith('patterns/'):name=name[len('patterns/'):]
    if not re.fullmatch(r'[a-z0-9-]+\.md',name):raise ContractError('Expected safe pattern-name.md basename')
    return name


def patch(text,edits):
    if not isinstance(edits,list) or not edits:raise ContractError('Patch requires a nonempty edits list')
    for edit in edits:
        if not isinstance(edit,dict) or edit.get('op') not in ('append','replace','insert_after'):
            raise ContractError('Unknown patch operation')
        content=edit.get('content')
        if not isinstance(content,str):raise ContractError('Patch content must be text')
        if edit['op']=='append':text=text.rstrip()+'\n\n'+content.strip()+'\n';continue
        target=edit.get('target')
        if not isinstance(target,str) or not target or text.count(target)!=1:
            raise ContractError('Patch target must occur exactly once')
        if target.strip()==text.strip():raise ContractError('Patch a specific section rather than replacing the whole file')
        replacement=content if edit['op']=='replace' else target+content
        text=text.replace(target,replacement,1)
    return text


def wiki_update(value,existing):
    keys={'create_patterns','update_patterns','update_index','append_log'}
    if not isinstance(value,dict) or set(value)!=keys:raise ContractError('Use the four paper Wiki edit fields exactly')
    if not isinstance(value['update_index'],str) or not value['update_index'].strip():raise ContractError('Complete update_index required')
    if not isinstance(value['append_log'],str) or not value['append_log'].strip():raise ContractError('append_log required')
    result=dict(existing);touched=set();normalized={**value,'create_patterns':[],'update_patterns':[]}
    for kind in ('create_patterns','update_patterns'):
        if not isinstance(value[kind],list):raise ContractError(f'{kind} must be a list')
        for entry in value[kind]:
            name=canonical_pattern(entry.get('name'));key='patterns/'+name
            if name in touched:raise ContractError('Duplicate pattern mutation')
            touched.add(name)
            if kind=='create_patterns':
                if set(entry)!={'name','content'} or key in result or not isinstance(entry['content'],str) or not entry['content'].strip():raise ContractError('Create requires a new name and nonempty content')
                result[key]=entry['content'];normalized[kind].append({'name':name,'content':entry['content']})
            else:
                if set(entry)!={'name','edits'} or key not in result:raise ContractError('Update requires an existing pattern and edits')
                result[key]=patch(result[key],entry['edits']);normalized[kind].append({'name':name,'edits':entry['edits']})
    for key in result:
        if key.startswith('patterns/') and key.split('/')[-1] not in value['update_index']:
            raise ContractError('update_index must retain every existing pattern')
    result['index.md']=value['update_index']
    return normalized,result


def validate_skill(name,skill,purpose):
    if not re.fullmatch(r'[a-z][a-z0-9_]*',name):raise ContractError('Skill name must be snake_case')
    if not isinstance(skill,str) or not isinstance(purpose,str):raise ContractError('SKILL.md and PURPOSE.md must be text')
    match=re.match(r'\A---\s*\n(.*?)\n---\s*\n',skill,re.S)
    if not match:raise ContractError('SKILL.md needs YAML frontmatter')
    metadata=yaml.safe_load(match[1])
    if not isinstance(metadata,dict) or metadata.get('name')!=name or not metadata.get('description'):
        raise ContractError('Frontmatter requires matching name and description')
    for heading in ('When to Apply','When NOT to Apply','Instructions'):
        if not re.search(r'^#{1,6}\s+'+re.escape(heading)+r'\s*$',skill,re.I|re.M):raise ContractError('Missing skill section: '+heading)
    for heading in ('Origin','Patterns Addressed','Evolution History'):
        if not re.search(r'^#{1,6}\s+'+re.escape(heading)+r'\s*$',purpose,re.I|re.M):raise ContractError('Missing purpose section: '+heading)
    for banned in ('/Users/','ground_truth','golden.xlsx','answer_key','score_answer','r_best'):
        if banned.lower() in skill.lower():raise ContractError('Skill contains evaluator/private-host vocabulary')


def proposal(value,skills,read_trace_ids):
    if not isinstance(value,dict):raise ContractError('Proposal must be an object')
    action=value.get('action')
    if action=='no_action':
        if set(value)!={'action'}:raise ContractError('no_action has no payload')
        return value,dict(skills)
    if len(set(read_trace_ids))<4:raise ContractError('Read at least four distinct execution traces before proposing a change')
    name=value.get('name','');result={k:dict(v) for k,v in skills.items()}
    if action=='create':
        if set(value)!={'action','name','skill_md','purpose_md'} or name in result:raise ContractError('Create requires a new skill and both Markdown files')
        validate_skill(name,value['skill_md'],value['purpose_md'])
        result[name]={'skill_md':value['skill_md'],'purpose_md':value['purpose_md']}
    elif action=='patch':
        if set(value)!={'action','name','edits'} or name not in result:raise ContractError('Patch requires an existing skill')
        result[name]['skill_md']=patch(result[name]['skill_md'],value['edits'])
        validate_skill(name,result[name]['skill_md'],result[name]['purpose_md'])
    else:raise ContractError('Use create, patch or no_action')
    return value,result


def skill_text(skills):
    return '\n\n'.join(skills[name]['skill_md'].strip() for name in sorted(skills))


def read_wiki(root):
    return {str(p.relative_to(root)):p.read_text() for p in sorted(root.rglob('*.md'))} if root.exists() else {}
