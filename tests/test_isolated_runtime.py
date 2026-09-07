"""Synthetic boundary, MCP, provenance and postflight-recovery checks; no models."""
from pathlib import Path
import json
import os
import sys
import tomllib

import pytest

from wikiskill.isolated import runtime
from wikiskill.isolated.audit import IntegrityError, audit, sha, write_json
from wikiskill.isolated.tools_server import RoleTools, safe, specs


def jsonl(path, events):
    path.write_text(''.join(json.dumps(event)+'\n' for event in events))


def archive_fixture(tmp_path, extra=()):
    archive = tmp_path/'runtime'
    archive.mkdir()
    workspace, control = tmp_path/'workspace', tmp_path/'control'
    workspace.mkdir()
    control.mkdir()
    (archive/'config.toml').write_text(runtime.config_text(workspace, control, 'spreadsheet', 'test', 'gpt-5.6-luna', 'high'))
    jsonl(archive/'session.jsonl', [{'type': 'turn_context', 'payload': {'model': 'gpt-5.6-luna', 'effort': 'high'}}]+list(extra))
    jsonl(archive/'events.jsonl', [{'type': 'turn.completed'}])
    write_json(archive/'invocation.json', {'workspace': str(workspace)})
    return archive, workspace, control


def call(name, result, *, arguments=None):
    return [{'type': 'response_item', 'payload': {'type': 'function_call', 'name': name, 'call_id': '1',
             'arguments': json.dumps(arguments or {})}},
            {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': '1', 'output': result}}]


def test_role_tools_confine_reads_and_compatible_pattern_names(tmp_path):
    workspace, control = tmp_path/'w', tmp_path/'c'
    (workspace/'wiki/patterns').mkdir(parents=True)
    control.mkdir()
    (control/'auth.json').write_text('synthetic secret')
    (workspace/'wiki/patterns/my_pattern.md').write_text('visible pattern')
    server = RoleTools(workspace, control, 'maintainer', sys.executable)
    assert server.call('read_file', {'path': 'wiki/patterns/my_pattern'}) == 'visible pattern'
    with pytest.raises(PermissionError):
        server.call('read_file', {'path': '../c/auth.json'})
    (workspace/'escape').symlink_to(control/'auth.json')
    with pytest.raises(PermissionError):
        safe(workspace, 'escape')
    with pytest.raises(PermissionError):
        server.call('bash', {'command': 'true'})
    with pytest.raises(ValueError, match='Unsupported'):
        specs('officeqa')


def test_proposer_counts_only_read_trace_files_and_terminal_finish(tmp_path):
    workspace, control = tmp_path/'w', tmp_path/'c'
    (workspace/'traces').mkdir(parents=True)
    control.mkdir()
    (workspace/'skills.json').write_text('{}')
    (workspace/'summary.md').write_text('summary')
    (workspace/'traces/a.md').write_text('real synthetic trace')
    server = RoleTools(workspace, control, 'proposer', sys.executable)
    server.call('read_file', {'path': 'summary.md'})
    assert not server.seen
    server.call('read_file', {'path': 'traces/a'})
    server.call('read_file', {'path': 'traces/a.md'})
    assert server.seen == {'a'}
    server.call('finish', {'proposal': {'action': 'no_action'}})
    assert json.loads((control/'submission.json').read_text()) == {
        'proposal': {'action': 'no_action'}, 'read_trace_ids': ['a']}
    with pytest.raises(ValueError, match='role has ended'):
        server.call('read_file', {'path': 'summary.md'})


def test_policy_does_not_grant_site_packages_or_control(tmp_path):
    cfg = tomllib.loads(runtime.config_text(tmp_path/'w', tmp_path/'c', 'spreadsheet', 'test', 'gpt-5.6-luna', 'high'))
    fs = cfg['permissions']['experiment']['filesystem']
    assert fs[':root'] == fs[':tmpdir'] == fs[':slash_tmp'] == 'deny'
    for path in runtime.python_package_paths():
        assert fs[str(path)] == 'deny'
    assert all(cfg['features'][name] is False for name in runtime.DISABLE)
    assert set(cfg['mcp_servers']) == {'paper'}
    assert cfg['mcp_servers']['paper']['args'][:3] == ['-I', '-m', 'wikiskill.isolated.tools_server']
    policy = runtime.outer_policy(tmp_path/'w', tmp_path/'c')
    assert '(deny network*)' in policy and '(deny signal ' in policy
    assert f'(deny file-read-data (subpath {json.dumps(str(tmp_path/"c"))}))' in policy
    for path in runtime.python_package_paths():
        assert f'(deny file-read-data (subpath {json.dumps(str(path))}))' in policy


@pytest.mark.parametrize('name,result', [
    ('list_mcp_resources', {'resources': [], 'server': 'paper'}),
    ('list_mcp_resource_templates', {'resourceTemplates': []}),
])
def test_audit_allows_only_empty_metadata_discovery(tmp_path, name, result):
    archive, _, _ = archive_fixture(tmp_path, call(name, json.dumps(result)))
    assert audit(archive, 'spreadsheet')['empty_discovery_probes'][0]['empty']


@pytest.mark.parametrize('name,result', [
    ('list_mcp_resources', {'resources': [{'uri': 'hidden'}]}),
    ('list_mcp_resource_templates', {'resourceTemplates': [], 'server': 'other'}),
    ('mcp__other__bash', {'exit_code': 0}),
    ('exec_command', 'denied'),
    ('view_image', 'image bytes'),
])
def test_audit_rejects_nonpaper_data_or_tools(tmp_path, name, result):
    archive, _, _ = archive_fixture(tmp_path, call(name, json.dumps(result)))
    with pytest.raises(IntegrityError):
        audit(archive, 'spreadsheet')


def test_audit_discloses_explicitly_blocked_workspace_image(tmp_path):
    blocked = 'view_image is not allowed because you do not support image inputs'
    archive, workspace, _ = archive_fixture(tmp_path)
    events = [{'type': 'turn_context', 'payload': {'model': 'gpt-5.6-luna', 'effort': 'high'}}]
    jsonl(archive/'session.jsonl', events+call('view_image', blocked, arguments={'path': str(workspace/'plot.png')}))
    assert audit(archive, 'spreadsheet')['blocked_native_attempts'][0]['received_image'] is False
    jsonl(archive/'session.jsonl', events+call('view_image', blocked, arguments={'path': str(tmp_path/'other.png')}))
    with pytest.raises(IntegrityError, match='another workspace'):
        audit(archive, 'spreadsheet')


def test_failed_attempt_is_preserved_and_not_resampled(tmp_path, monkeypatch):
    payload = tmp_path/'payload'
    payload.mkdir()
    def fail(*args):
        raise IntegrityError('synthetic startup failure')
    monkeypatch.setattr(runtime, '_resources', fail)
    with pytest.raises(IntegrityError, match='startup failure'):
        runtime.execute(payload, 's', 'u', 'spreadsheet', libreoffice_app=Path('/synthetic.app'))
    before = (tmp_path/'runtime/failure.json').read_bytes()
    with pytest.raises(IntegrityError, match='no automatic model retry'):
        runtime.execute(payload, 's', 'u', 'spreadsheet', libreoffice_app=Path('/synthetic.app'))
    assert (tmp_path/'runtime/failure.json').read_bytes() == before


def test_native_complete_recovery_never_calls_runtime_or_model(tmp_path, monkeypatch):
    archive, _, _ = archive_fixture(tmp_path)
    payload = tmp_path/'payload'
    payload.mkdir()
    request = {'mode': 'spreadsheet', 'system': 's', 'user_template': 'u', 'timeout': 1800,
               'model': 'gpt-5.6-luna', 'effort': 'high', 'libreoffice_app': '/synthetic.app'}
    write_json(archive/'request.json', request)
    (archive/'final.txt').write_text('done')
    (archive/'outer.sb').write_text('synthetic frozen policy')
    artifacts = {path.name: sha(path) for path in archive.iterdir()}
    write_json(archive/'native-complete.json', {'artifacts': artifacts})
    def forbidden(*args, **kwargs):
        raise AssertionError('resampling is forbidden')
    monkeypatch.setattr(runtime, '_resources', forbidden)
    monkeypatch.setattr(runtime, 'create_context', forbidden)
    assert runtime.execute(payload, 's', 'u', 'spreadsheet', libreoffice_app=Path('/synthetic.app')) == archive
    assert (archive/'audit.json').is_file()
    (archive/'final.txt').write_text('changed')
    with pytest.raises(IntegrityError, match='Native completion changed'):
        runtime.execute(payload, 's', 'u', 'spreadsheet', libreoffice_app=Path('/synthetic.app'))


def test_preflight_has_no_inference_and_checks_three_mcp_modes(tmp_path, monkeypatch):
    w, c = tmp_path/'w', tmp_path/'c'
    w.mkdir()
    c.mkdir()
    modes = []
    monkeypatch.setattr(runtime, '_resources', lambda *args: {'model': 'gpt-5.6-luna'})
    monkeypatch.setattr(runtime, 'create_context', lambda *args, **kwargs: (w, c, {}, ['no-model']))
    monkeypatch.setattr(runtime, 'install_spreadsheet_dependencies', lambda *args: None)
    monkeypatch.setattr(runtime, 'inspect_context', lambda *args: {'memory_injected': False})
    monkeypatch.setattr(runtime, 'verify_boundary', lambda *args: {'forbidden_read_tests': 8, 'denied': 8})
    monkeypatch.setattr(runtime, '_probe_mcp', lambda w, c, mode: modes.append(mode) or {'mode': mode})
    monkeypatch.setattr(RoleTools, 'call', lambda self, name, args: {'exit_code': 0, 'stdout':
        'PACKAGED_RESEARCH_DENIED' if 'PACKAGED_RESEARCH_DENIED' in args['command'] else 'LibreOffice synthetic'})
    result = runtime.preflight(libreoffice_app=Path('/synthetic.app'))
    assert result['model_calls'] == 0 and result['ok']
    assert tuple(modes) == runtime.MODES


def test_catalog_is_packaged_and_public_safe():
    text = runtime.catalog_path().read_text()
    catalog = json.loads(text)
    assert [model['slug'] for model in catalog['models']] == ['gpt-5.6-luna']
    assert catalog['models'][0]['input_modalities'] == ['text']
    assert all(marker not in text for marker in ('/Users/', 'private_planning', 'access_token', 'Bearer '))


@pytest.mark.parametrize('mode,model,effort', [('officeqa', 'gpt-5.6-luna', 'high'),
    ('spreadsheet', 'gpt-reserve', 'high'), ('spreadsheet', 'gpt-5.6-luna', 'low')])
def test_unsupported_identity_or_mode_is_explicit(tmp_path, mode, model, effort):
    with pytest.raises(IntegrityError):
        runtime.execute(tmp_path, 's', 'u', mode, libreoffice_app=Path('/synthetic.app'), model=model, effort=effort)
