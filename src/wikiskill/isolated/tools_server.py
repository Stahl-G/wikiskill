"""Paper role tools: canonical staged reads and sandboxed Spreadsheet shell.

Ported from the research tools_server + tools_server_compatible entrypoints.
This trusted controller alone writes receipts/submissions outside the workspace;
the model's computation subprocess cannot read the controller or its auth file.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from wikiskill.paper_alignment.contracts import (
    ContractError, _pattern_identity, proposal, read_wiki, wiki_update,
)

MODES = ('spreadsheet', 'maintainer', 'proposer')


def safe(root: Path, name: str) -> Path:
    root = root.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise PermissionError('Outside role workspace')
    if path.exists():
        return path
    if not any(path.parent.is_relative_to(folder) for folder in (root/'wiki/patterns', root/'patterns')):
        return path
    if not path.parent.is_dir():
        return path
    identity = _pattern_identity(path.name)
    matches = [p for p in path.parent.iterdir() if p.is_file() and _pattern_identity(p.name) == identity]
    if len(matches) > 1:
        raise ContractError('Ambiguous pattern filename aliases; use the exact existing path')
    if matches:
        resolved = matches[0].resolve()
        if not resolved.is_relative_to(root):
            raise PermissionError('Outside role workspace')
        return resolved
    return path


def specs(mode: str) -> list[dict]:
    if mode not in MODES:
        raise ValueError('Unsupported isolated mode: '+mode)

    def tool(name, description, properties, required):
        return {'name': name, 'description': description,
                'inputSchema': {'type': 'object', 'properties': properties,
                                'required': required, 'additionalProperties': False}}

    if mode == 'spreadsheet':
        return [tool('bash', 'Execute shell commands within the isolated working_directory. '
                     'Python/openpyxl and LibreOffice are available. Network and other workspaces are denied.',
                     {'command': {'type': 'string'}}, ['command'])]
    read = tool('read_file', 'Read an entire staged wiki or execution-trace file. '
                'Wiki pattern filenames are resolved with or without .md when unambiguous.',
                {'path': {'type': 'string'}}, ['path'])
    edits = {'type': 'array', 'items': {'type': 'object', 'properties': {
        'op': {'type': 'string', 'enum': ['append', 'replace', 'insert_after']},
        'target': {'type': 'string'}, 'content': {'type': 'string'}},
        'required': ['op', 'content'], 'additionalProperties': False}}
    if mode == 'maintainer':
        schema = {'type': 'object', 'properties': {
            'create_patterns': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'name': {'type': 'string'}, 'content': {'type': 'string'}},
                'required': ['name', 'content'], 'additionalProperties': False}},
            'update_patterns': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'name': {'type': 'string'}, 'edits': edits},
                'required': ['name', 'edits'], 'additionalProperties': False}},
            'update_index': {'type': 'string'}, 'append_log': {'type': 'string'}},
            'required': ['create_patterns', 'update_patterns', 'update_index', 'append_log'],
            'additionalProperties': False}
    else:
        schema = {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['create', 'patch', 'no_action']},
            'name': {'type': 'string'}, 'skill_md': {'type': 'string'},
            'purpose_md': {'type': 'string'}, 'edits': edits},
            'required': ['action'], 'additionalProperties': False}
    finish = tool('finish', 'Submit the complete final paper JSON once ready; a successful call ends this role. '
                  'Do not use finish as a schema probe. Pattern filenames may omit .md and may use underscores '
                  'or hyphens; storage names are normalized automatically.', {'proposal': schema}, ['proposal'])
    return [read, finish]


def shell_environment(root: Path, python: str) -> dict[str, str]:
    return {'PATH': str(root/'bin')+':'+str(Path(python).parent)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
            'PYTHONPATH': str(root/'tool_libs'), 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
            'TMPDIR': str(root/'tmp'), 'ZDOTDIR': str(root/'tmp'),
            'XDG_CACHE_HOME': str(root/'tmp/cache'), 'LANG': 'en_US.UTF-8'}


class RoleTools:
    def __init__(self, workspace: Path, control: Path, mode: str, python: str):
        self.root, self.control = workspace.resolve(), control.resolve()
        self.mode, self.python = mode, python
        self.allowed = {s['name'] for s in specs(mode)}
        self.seen: set[str] = set()
        self.finished = False

    def call(self, name: str, args: dict):
        if name not in self.allowed:
            raise PermissionError('Tool not available for this role')
        if self.finished:
            raise ValueError('Submission already accepted; role has ended')
        if name == 'read_file':
            path = safe(self.root, args['path'])
            if not path.is_file() and path.parent == self.root/'traces':
                path = safe(self.root, str(path.relative_to(self.root))+'.md')
            if not path.is_file():
                raise ValueError('Not a file')
            content = path.read_text(encoding='utf-8')
            if path.parent == self.root/'traces':
                self.seen.add(path.stem)
            return content
        if name == 'finish':
            value = args['proposal']
            if self.mode == 'maintainer':
                normalized, _ = wiki_update(value, read_wiki(self.root/'wiki'))
            else:
                normalized, _ = proposal(value, json.loads((self.root/'skills.json').read_text()), self.seen)
            with (self.control/'submission.json').open('x', encoding='utf-8') as stream:
                json.dump({'proposal': normalized, 'read_trace_ids': sorted(self.seen)}, stream,
                          ensure_ascii=False, indent=2)
            self.finished = True
            return {'accepted': True, 'message': 'Submission recorded; finish your response without further tool calls.'}
        started = time.monotonic()
        child = subprocess.Popen([
            '/usr/bin/sandbox-exec', '-f', str(self.control/'outer.sb'),
            '/bin/bash', '--noprofile', '--norc', '-c', args['command']],
            cwd=self.root, env=shell_environment(self.root, self.python), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = child.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
            return {'exit_code': 124, 'stdout': stdout[:16000], 'stderr': stderr[:3000], 'timeout': True}
        return {'exit_code': child.returncode, 'stdout': stdout[:16000], 'stderr': stderr[:3000],
                'seconds': time.monotonic()-started}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--python', required=True)
    args = parser.parse_args()
    server = RoleTools(args.workspace, args.control, args.mode, args.python)
    for line in sys.stdin:
        request = json.loads(line)
        method, ident = request.get('method'), request.get('id')
        if ident is None:
            continue
        if method == 'initialize':
            result = {'protocolVersion': request.get('params', {}).get('protocolVersion', '2024-11-05'),
                      'capabilities': {'tools': {}}, 'serverInfo': {'name': 'wikiskill-paper-v2', 'version': '2'}}
        elif method == 'tools/list':
            result = {'tools': specs(args.mode)}
        elif method == 'ping':
            result = {}
        elif method in ('resources/list', 'resources/templates/list', 'prompts/list'):
            key = {'resources/list': 'resources', 'resources/templates/list': 'resourceTemplates',
                   'prompts/list': 'prompts'}[method]
            result = {key: []}
        elif method == 'tools/call':
            params = request['params']
            record = {'at': time.time(), 'tool': params['name'], 'arguments': params.get('arguments', {})}
            try:
                value = server.call(params['name'], params.get('arguments', {}))
                record.update(ok=True, result=value)
                result = {'content': [{'type': 'text', 'text': value if isinstance(value, str) else json.dumps(value)}]}
            except Exception as exc:
                record.update(ok=False, error=f'{type(exc).__name__}: {exc}')
                result = {'content': [{'type': 'text', 'text': record['error']}], 'isError': True}
            with (args.control/'tool-events.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False)+'\n')
        else:
            print(json.dumps({'jsonrpc': '2.0', 'id': ident,
                              'error': {'code': -32601, 'message': 'method not found'}}), flush=True)
            continue
        print(json.dumps({'jsonrpc': '2.0', 'id': ident, 'result': result}), flush=True)


if __name__ == '__main__':
    main()
