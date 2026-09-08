"""Package the entry skill and native agent definitions from their source files."""
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT/'src/wikiskill/resources/product'


def expected():
    result = {}
    descriptions = {
        'executor': 'Execute one WikiSkill task in a fresh context and return an actual output artifact.',
        'maintainer': 'Maintain WikiSkill knowledge from supplied training evidence after training completes.',
        'proposer': 'Propose a WikiSkill candidate after the current Wiki update has been submitted.',
    }
    for role, description in descriptions.items():
        name = 'wikiskill-'+role
        body = (TARGET/'roles'/f'{role}.md').read_text(encoding='utf-8')
        result[TARGET/'agents/codex'/f'{name}.toml'] = ('name = '+json.dumps(name)+'\ndescription = '+json.dumps(description)+'\ndeveloper_instructions = '+json.dumps(body)+'\n').encode()
        result[TARGET/'agents/claude-code'/f'{name}.md'] = ('---\nname: '+name+'\ndescription: '+description+'\nmodel: inherit\n---\n\n'+body).encode()
    source = ROOT/'skills/wikiskill'
    for path in source.rglob('*'):
        if path.is_file() and path.suffix in ('.md','.yaml'):
            result[TARGET/'entry-skill'/path.relative_to(source)] = path.read_bytes()
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    wanted=expected()
    extras={p for folder in ('agents','entry-skill') for p in (TARGET/folder).rglob('*') if p.is_file()}-set(wanted)
    if extras:
        raise SystemExit('Unexpected generated assets: '+', '.join(str(p.relative_to(ROOT)) for p in extras))
    bad=[]
    for path, data in wanted.items():
        if args.check:
            if not path.is_file() or path.read_bytes()!=data:bad.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if bad:raise SystemExit('Stale native assets: '+', '.join(bad))
    print('Native host assets match sources.' if args.check else 'Native host assets generated.')


if __name__=='__main__':main()
