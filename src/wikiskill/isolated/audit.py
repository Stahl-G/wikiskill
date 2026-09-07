"""Read-only postflight audit, including the disclosed metadata-denials revision."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib

from wikiskill.codex_identity import assert_requested_model, model_from_session_file
from wikiskill.jsonl import read_jsonl
from .tools_server import specs


class IntegrityError(RuntimeError):
    """An isolation or frozen-record invariant failed; do not resample."""


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value, *, exclusive: bool = True) -> None:
    with Path(path).open('x' if exclusive else 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify_native_complete(archive: Path) -> dict:
    archive = Path(archive)
    complete = json.loads((archive/'native-complete.json').read_text())
    artifacts = complete.get('artifacts')
    if not isinstance(artifacts, dict) or not artifacts:
        raise IntegrityError('Empty native completion manifest')
    required = {'request.json', 'session.jsonl', 'events.jsonl', 'config.toml', 'invocation.json', 'final.txt', 'outer.sb'}
    if not required.issubset(artifacts):
        raise IntegrityError('Native completion omits required artifacts')
    for name, digest in artifacts.items():
        if Path(name).name != name or name in ('.', '..'):
            raise IntegrityError('Invalid completion artifact path')
        path = archive/name
        if path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise IntegrityError('Native completion changed: '+name)
    actual = {p.name for p in archive.iterdir() if p.name not in ('audit.json', 'native-complete.json', 'failure.json')}
    if actual != set(artifacts):
        raise IntegrityError('Native completion artifact inventory changed')
    return complete


def check_empty_discovery(name: str, raw) -> None:
    key = {'list_mcp_resources': 'resources', 'list_mcp_resource_templates': 'resourceTemplates'}[name]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IntegrityError('Unverifiable discovery response') from exc
    if (not isinstance(raw, dict) or raw.get(key) != [] or set(raw)-{key, 'server', 'nextCursor'}
            or raw.get('server') not in (None, 'paper') or raw.get('nextCursor') not in (None, '')):
        raise IntegrityError('Discovery returned resources or unknown data')


def audit(archive: Path, mode: str, *, model='gpt-5.6-luna', effort='high') -> dict:
    if (model, effort) != ('gpt-5.6-luna', 'high'):
        raise IntegrityError('This isolated backend supports only gpt-5.6-luna/high')
    archive = Path(archive)
    session = read_jsonl(archive/'session.jsonl')
    contexts = [event['payload'] for event in session if event.get('type') == 'turn_context']
    if not contexts or any((context.get('model'), context.get('effort')) != (model, effort) for context in contexts):
        raise IntegrityError('Session model/effort mismatch')
    assert_requested_model(model, model_from_session_file(archive/'session.jsonl'))
    outputs = {event['payload'].get('call_id'): event['payload'].get('output') for event in session
               if event.get('type') == 'response_item' and event['payload'].get('type') == 'function_call_output'}
    allowed = {tool['name'] for tool in specs(mode)}
    used, metadata, blocked = [], [], []
    for event in session:
        payload = event.get('payload', {})
        if event.get('type') != 'response_item':
            continue
        if payload.get('type') in ('custom_tool_call', 'web_search_call', 'computer_call',
                                   'code_interpreter_call', 'image_generation_call'):
            raise IntegrityError('Unexpected non-paper tool route')
        if payload.get('type') != 'function_call':
            continue
        name = payload.get('name', '')
        if name in ('list_mcp_resources', 'list_mcp_resource_templates'):
            check_empty_discovery(name, outputs.get(payload.get('call_id')))
            metadata.append({'call_id': payload['call_id'], 'name': name, 'empty': True})
            continue
        if name == 'view_image':
            returned = outputs.get(payload.get('call_id'))
            if returned != 'view_image is not allowed because you do not support image inputs':
                raise IntegrityError('Image capability was not explicitly denied')
            args = json.loads(payload['arguments'])
            workspace = Path(json.loads((archive/'invocation.json').read_text())['workspace']).resolve()
            if not Path(args['path']).is_absolute() or not Path(args['path']).resolve().is_relative_to(workspace):
                raise IntegrityError('Image attempt targeted another workspace')
            blocked.append({'call_id': payload['call_id'], 'name': name, 'reason': returned, 'received_image': False})
            continue
        # Accept historical bare paper-tool names, but never another server's name.
        plain = name.removeprefix('mcp__paper__')
        if plain not in allowed:
            raise IntegrityError('Unexpected task function: '+name)
        used.append(plain)
    cfg = tomllib.loads((archive/'config.toml').read_text())
    disabled = ('code_mode', 'code_mode_host', 'code_mode_only', 'memories', 'shell_tool', 'unified_exec',
                'apps', 'plugins', 'multi_agent', 'multi_agent_v2', 'browser_use', 'computer_use')
    if any(cfg.get('features', {}).get(key) is not False for key in disabled):
        raise IntegrityError('A forbidden runtime capability is enabled or unspecified')
    if set(cfg.get('mcp_servers', {})) != {'paper'}:
        raise IntegrityError('Unexpected MCP server configuration')
    if any(cfg.get('memories', {}).get(key) is not False for key in ('generate_memories', 'use_memories')):
        raise IntegrityError('Memory generation/use enabled')
    if cfg.get('approval_policy') != 'never' or cfg.get('permissions', {}).get('experiment', {}).get('network', {}).get('enabled') is not False:
        raise IntegrityError('Approval/network policy changed')
    if any(event.get('item', {}).get('type') == 'command_execution' for event in read_jsonl(archive/'events.jsonl')):
        raise IntegrityError('Unrestricted native shell route')
    receipts = read_jsonl(archive/'tool-events.jsonl') if (archive/'tool-events.jsonl').exists() else []
    if any(record.get('tool') not in allowed for record in receipts):
        raise IntegrityError('Tool receipt outside role set')
    return {'mode': mode, 'used': used, 'tool_receipts': len(receipts), 'empty_discovery_probes': metadata,
            'blocked_native_attempts': blocked, 'custom_code_calls': 0,
            'model_identity_scope': 'Codex client metadata, not server weights'}
