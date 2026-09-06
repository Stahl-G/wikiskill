"""AST-aware admission checks for recorded Code Mode calls.

This is an audit layer, not an operating-system sandbox. Embedded Python,
formula strings and comments are data; their words are not JavaScript calls.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess


class ToolAuditError(RuntimeError):
    pass


def analyze_javascript(programs: list[str], *, node: str | None = None) -> list[dict]:
    if not programs:
        return []
    executable = node or shutil.which('node')
    if not executable:
        raise ToolAuditError('Node.js is required for AST auditing; completed model artifacts remain recoverable')
    parser = Path(__file__).parent / 'resources/runtime/audit_js.mjs'
    try:
        proc = subprocess.run([executable, str(parser)], input=json.dumps(programs),
                              capture_output=True, text=True, timeout=30, check=True)
        parsed = json.loads(proc.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise ToolAuditError(f'JavaScript audit parser failed: {type(exc).__name__}; preserve completed output') from exc
    if len(parsed) != len(programs):
        raise ToolAuditError('JavaScript parser returned the wrong number of records')
    return parsed


def audit_calls(session: list[dict], *, web_allowed: bool = False, node: str | None = None) -> list[dict]:
    payloads = [v['payload'] for v in session if v.get('type') == 'response_item']
    outputs = {p.get('call_id'): p for p in payloads
               if p.get('type') in ('custom_tool_call_output', 'function_call_output')}
    calls = [p for p in payloads if p.get('type') in ('custom_tool_call', 'function_call')]
    custom = [p for p in calls if p['type'] == 'custom_tool_call']
    parsed = iter(analyze_javascript([p.get('input', '') for p in custom], node=node))
    audit = []
    metadata = {'update_plan', 'list_mcp_resources', 'list_mcp_resource_templates', 'wait'}

    def allowed(name):
        return name.startswith('mcp__documents__') or name in metadata or (web_allowed and name in {'web__run', 'web_run'})

    for p in calls:
        returned = json.dumps(outputs.get(p.get('call_id')))
        if p['type'] == 'custom_tool_call':
            syntax = next(parsed)
            if syntax['parse_error']:
                # A failed compilation runs no JavaScript. A successful host
                # execution with an unparseable record requires explicit review.
                if 'Script failed' in returned and 'SyntaxError' in returned:
                    audit.append({'call_id': p.get('call_id'), 'kind': 'invalid_orchestration_syntax'})
                    continue
                raise ToolAuditError(f"Cannot audit completed call {p.get('call_id')}: {syntax['parse_error']}")
            entries, hazards = syntax['calls'], syntax['hazards']
            if syntax['catalog']:
                audit.append({'call_id': p.get('call_id'), 'kind': 'catalog_discovery'})
        else:
            entries = [{'name': p.get('name', ''), 'strings': [p.get('arguments', '')]}]
            hazards = []
        forbidden = [x['name'] for x in entries if not allowed(x['name'])]
        if forbidden or hazards:
            blocked = bool(forbidden) and not hazards and all('tools.' + n + ' is not a function' in returned for n in forbidden)
            audit.append({'call_id': p.get('call_id'), 'kind': 'blocked_api_attempt' if blocked else 'undeclared_api',
                          'tools': forbidden, 'hazards': hazards})
        for entry in entries:
            if entry['name'] in {'web__run', 'web_run'} and re.search(
                    r'sealqa|vtllms|huggingface\.co|github\.com|answer[ -]?key', '\n'.join(entry['strings']), re.I):
                audit.append({'call_id': p.get('call_id'), 'kind': 'undeclared_api', 'reason': 'benchmark-answer-source query'})
    return audit
