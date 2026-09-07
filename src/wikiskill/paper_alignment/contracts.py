"""Deterministic paper JSON contracts; roles submit content, controller applies."""
from pathlib import Path, PureWindowsPath
import json
import re
import unicodedata
import yaml


class ContractError(ValueError):
    pass


def canonical_pattern(name):
    if not isinstance(name,str):raise ContractError('Pattern name must be a string')
    name=unicodedata.normalize('NFC',name.strip())
    if name.startswith('wiki/patterns/'):name=name[len('wiki/patterns/'):]
    elif name.startswith('patterns/'):name=name[len('patterns/'):]
    if not name or name in ('.','..') or '/' in name or '\\' in name or PureWindowsPath(name).drive or any(unicodedata.category(c).startswith('C') for c in name):
        raise ContractError(f'Pattern path must be one local filename, without traversal or control characters: {name!r}')
    # Suffix and spelling conventions are storage details, not content gates.
    # Keep underscores, hyphens, spaces and Unicode; normalize only the suffix.
    return name[:-3]+'.md' if name.lower().endswith('.md') else name+'.md'


def _pattern_identity(name):
    return canonical_pattern(name).casefold()


def _index_paths(index,names):
    """Repair known filename aliases without editing the semantic descriptions."""
    by_identity={_pattern_identity(name):name for name in names}
    referenced=set()
    def rewrite(match):
        prefix,target=match.groups()
        try:key=_pattern_identity(target)
        except ContractError:return match.group(0)
        if key not in by_identity:return match.group(0)
        name=by_identity[key];referenced.add(name)
        return prefix+name
    index=re.sub(r'((?:wiki/)?patterns/)([^\n<>`)]+)',rewrite,index)
    for name in names:
        if name in index or name in referenced:continue
        stem=name[:-3] if name.lower().endswith('.md') else name
        if stem in index:
            # A plain-name index is still readable. Add only its exact locator.
            index+='\n- ['+stem+'](<wiki/patterns/'+name+'>)\n'
        else:raise ContractError('update_index must retain existing pattern: '+name)
    return index


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
    existing_names={}
    for key in existing:
        if key.startswith('patterns/'):
            identity=_pattern_identity(key[len('patterns/'):])
            if identity in existing_names:raise ContractError('Ambiguous existing pattern aliases')
            existing_names[identity]=key[len('patterns/'):]
    for kind in ('create_patterns','update_patterns'):
        if not isinstance(value[kind],list):raise ContractError(f'{kind} must be a list')
        for entry in value[kind]:
            name=canonical_pattern(entry.get('name'));identity=_pattern_identity(name)
            if identity in touched:raise ContractError('Duplicate pattern mutation after filename normalization: '+name)
            touched.add(identity)
            if kind=='create_patterns' and identity in existing_names:raise ContractError('Create would overwrite existing pattern: '+name)
            if kind=='update_patterns':name=existing_names.get(identity,name)
            key='patterns/'+name
            if kind=='create_patterns':
                if set(entry)!={'name','content'} or key in result or not isinstance(entry['content'],str) or not entry['content'].strip():raise ContractError('Create requires a new name and nonempty content')
                result[key]=entry['content'];normalized[kind].append({'name':name,'content':entry['content']})
            else:
                if set(entry)!={'name','edits'} or key not in result:raise ContractError('Update requires an existing pattern and edits')
                result[key]=patch(result[key],entry['edits']);normalized[kind].append({'name':name,'edits':entry['edits']})
    normalized['update_index']=_index_paths(value['update_index'],[key[len('patterns/'):] for key in result if key.startswith('patterns/')])
    result['index.md']=normalized['update_index']
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
    if not root.exists():return {}
    files=set(root.rglob('*.md'))
    files.update(p for p in (root/'patterns').glob('*') if p.is_file() and not p.name.startswith('.'))
    if any(not p.resolve().is_relative_to(root.resolve()) for p in files):raise ContractError('Wiki file resolves outside the Wiki directory')
    return {str(p.relative_to(root)):p.read_text() for p in sorted(files)}
