import json

import pytest

from wikiskill.jsonl import JSONLRecordError, loads_jsonl, read_jsonl
from wikiskill.tool_audit import audit_calls


def event(code, output='Script completed'):
    return [
        {'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'call_id': 'x', 'input': code}},
        {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'x', 'output': output}},
    ]


def test_jsonl_unicode_separators_are_string_content(tmp_path):
    rows = [{'text': 'first\u2028second\u2029third\u0085fourth'}, {'score': 1}]
    text = '\r\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\r\n'
    path = tmp_path / 'session.jsonl';path.write_text(text)
    assert len(text.splitlines()) > 2
    assert loads_jsonl(text) == read_jsonl(path) == rows


def test_actual_truncation_is_explicit_and_never_skipped():
    with pytest.raises(JSONLRecordError, match='physical line 2'):
        loads_jsonl('{"ok":true}\n{"text":"unfinished', source='session.jsonl')


def test_embedded_python_eval_is_not_javascript_eval():
    code = '''const r = await tools.mcp__documents__run_python({code: `
from pathlib import Path
def numeric(v):
    return eval(v[1:], {"__builtins__": {}}, {})
`}); text(r);'''
    assert audit_calls(event(code)) == []
    assert audit_calls(event('eval("tools.apply_patch(\\"bad\\")")'))[0]['kind'] == 'undeclared_api'


def test_template_interpolation_is_actual_javascript_not_payload_text():
    code = 'await tools.mcp__documents__read_file({path: `safe ${eval("bad")}`})'
    assert any(x['kind'] == 'undeclared_api' for x in audit_calls(event(code)))


def test_comments_and_literal_host_api_words_are_data():
    code = '// tools.exec_command({cmd:"bad"})\nconst msg="globalThis.fetch() eval()"; text(msg);'
    assert audit_calls(event(code)) == []


def test_real_forbidden_api_and_blocked_attempt_stay_distinct():
    code = 'await tools.exec_command({cmd:"pwd"})'
    assert audit_calls(event(code))[0]['kind'] == 'undeclared_api'
    assert audit_calls(event(code, 'Script failed TypeError: tools.exec_command is not a function'))[0]['kind'] == 'blocked_api_attempt'
    code = 'const t=tools; await t["apply_patch"]("bad")'
    assert audit_calls(event(code))[0]['kind'] == 'undeclared_api'


def test_formula_parse_syntax_error_does_not_become_hidden_retry():
    result = audit_calls(event('const x = ;', 'Script failed SyntaxError: unexpected token'))
    assert result == [{'call_id': 'x', 'kind': 'invalid_orchestration_syntax'}]
