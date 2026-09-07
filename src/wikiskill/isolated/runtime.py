"""Fresh role sessions with paper tools and the research macOS OS boundary.

The only inference entrypoint is execute. preflight runs local probes without
model calls. Interrupted attempts remain inspectable; native-complete attempts
can only repeat deterministic postflight. Credentials never enter the payload.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from importlib.resources import files
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import sysconfig
import tempfile
import time

from wikiskill.codex_identity import extract_thread_id
from wikiskill.jsonl import read_jsonl
from .audit import IntegrityError, audit, sha, verify_native_complete, write_json
from .tools_server import MODES, shell_environment, specs

DISABLE = ('memories', 'chronicle', 'apps', 'plugins', 'hooks', 'multi_agent',
           'browser_use', 'browser_use_external', 'computer_use', 'in_app_browser',
           'image_generation', 'shell_snapshot', 'skill_search', 'workspace_dependencies',
           'shell_tool', 'unified_exec', 'code_mode', 'code_mode_host', 'code_mode_only',
           'multi_agent_v2', 'goals', 'tool_suggest')
READONLY = ('corpus', 'traces', 'training-traces', 'wiki', 'current', 'training_reference.json', 'question.md')
EXCLUDED_PAYLOAD = {'scratch', '.git', '.codex', '.agents', 'isolation', 'outcome.json', 'result.json',
                    'codex_stdout.txt', 'codex_stderr.txt', 'run.json'}


def _identity(model: str, effort: str) -> None:
    if (model, effort) != ('gpt-5.6-luna', 'high'):
        raise IntegrityError('This isolated backend supports only gpt-5.6-luna/high')


def catalog_path() -> Path:
    return Path(str(files('wikiskill').joinpath('resources/isolated/model-catalog-direct.json')))


def python_read_paths() -> tuple[Path, ...]:
    """Only executable/library locations, never the venv's enclosing checkout.

    Computation uses this venv's executable with -S: only copied tool_libs are
    importable. The trusted MCP controller separately sees the installed wheel.
    """
    paths = {Path(sys.executable).absolute(), Path(sys.executable).resolve(), Path(sys.prefix)/'pyvenv.cfg'}
    paths.add(Path(sysconfig.get_path('stdlib')).resolve())
    libdir = sysconfig.get_config_var('LIBDIR')
    if libdir:
        # libpython's directory can live in a bundled runtime under the home directory.
        paths.add(Path(libdir).resolve())
    return tuple(sorted(path for path in paths if path.exists()))


def python_package_paths() -> tuple[Path, ...]:
    """Deny installed packages, including the bundled historical scored data."""
    paths = {Path(sysconfig.get_path(key)).resolve() for key in ('purelib', 'platlib')}
    paths.add(Path(sys.base_prefix)/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages')
    return tuple(sorted(paths))


def outer_policy(workspace: Path, control: Path) -> str:
    exceptions = [f'(require-not (subpath {json.dumps(str(workspace.resolve()))}))']
    for path in python_read_paths():
        kind = 'subpath' if path.is_dir() else 'literal'
        exceptions.append(f'(require-not ({kind} {json.dumps(str(path))}))')
    roots = ('/Users', '/private/tmp', '/tmp', '/private/var/folders', '/var/folders', '/Volumes', '/System/Volumes/Data/Users')
    denies = '\n'.join(f'(deny file-read-data (require-all (subpath "{root}") '+ ' '.join(exceptions)+'))' for root in roots)
    denies += f'\n(deny file-write* (require-all (subpath "/") (require-not (subpath {json.dumps(str(workspace.resolve()))})) (require-not (subpath "/dev"))))'
    readonly = '\n'.join(f'(deny file-write* (subpath {json.dumps(str(workspace/name))}))' for name in READONLY)
    packages = '\n'.join(f'(deny file-read-data (subpath {json.dumps(str(path))}))' for path in python_package_paths())
    # Control must remain unreadable even if an installation was placed unusually.
    return ('(version 1)\n(allow default)\n(deny network*)\n'+denies+'\n'+readonly+'\n'+packages+'\n'
            +f'(deny file-read-data (subpath {json.dumps(str(control.resolve()))}))\n'
            +'(deny signal (require-not (target self)))\n')


def config_text(workspace: Path, control: Path, mode: str, system: str, model: str, effort: str) -> str:
    config = '\n'.join([
        'model_catalog_json = '+json.dumps(str(catalog_path())),
        'developer_instructions = '+json.dumps(system),
        'model = '+json.dumps(model), 'model_reasoning_effort = '+json.dumps(effort),
        'approval_policy = "never"', 'default_permissions = "experiment"',
        'project_doc_max_bytes = 0', 'web_search = "disabled"',
        '[features]', *(name+' = false' for name in DISABLE),
        '[memories]', 'generate_memories = false', 'use_memories = false',
        '[permissions.experiment.filesystem]', '":root" = "deny"', '":minimal" = "read"',
        '":tmpdir" = "deny"', '":slash_tmp" = "deny"',
        '"/Library/Frameworks/Python.framework" = "read"', '"/opt/homebrew" = "read"',
        *(json.dumps(str(path))+' = "read"' for path in python_read_paths()),
        *(json.dumps(str(path))+' = "deny"' for path in python_package_paths()),
        '[permissions.experiment.filesystem.":workspace_roots"]', '"." = "write"',
        '[permissions.experiment.network]', 'enabled = false',
        '[shell_environment_policy]', 'inherit = "none"', '[shell_environment_policy.set]',
        'PATH = '+json.dumps(str(Path(sys.executable).parent)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'),
        'ZDOTDIR = '+json.dumps(str(workspace/'tmp')), 'TMPDIR = '+json.dumps(str(workspace/'tmp')),
        '[agents]', 'enabled = false', '[tools.update_plan]', 'enabled = false',
        '[mcp_servers.paper]', 'command = '+json.dumps(sys.executable),
        'args = '+json.dumps(['-I', '-m', 'wikiskill.isolated.tools_server', '--mode', mode, '--workspace', str(workspace),
                             '--control', str(control), '--python', sys.executable]),
        'startup_timeout_sec = 20', 'tool_timeout_sec = 130', 'required = true',
        'default_tools_approval_mode = "approve"', ''])
    skill_paths = [control/'skills/.system'/name/'SKILL.md' for name in
                   ('imagegen', 'openai-docs', 'plugin-creator', 'skill-creator', 'skill-installer')]
    for base in (Path.home()/'.agents/skills', Path.home()/'.codex/skills'):
        skill_paths.extend(base.glob('*/SKILL.md'))
    for path in skill_paths:
        config += '\n[[skills.config]]\npath = '+json.dumps(str(path))+'\nenabled = false\n'
    return config


def _resources(libreoffice_app: Path, model: str, effort: str) -> dict:
    _identity(model, effort)
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        raise IntegrityError('This pinned isolation backend requires macOS sandbox-exec')
    if not shutil.which('codex'):
        raise IntegrityError('Codex CLI is unavailable on PATH')
    app = Path(libreoffice_app)
    if not app.is_absolute() or not (app/'Contents/MacOS/soffice').is_file():
        raise IntegrityError('libreoffice_app must be an absolute LibreOffice .app directory')
    for name in ('openpyxl', 'et_xmlfile', 'yaml'):
        if importlib.util.find_spec(name) is None:
            raise IntegrityError('Missing installed runtime dependency: '+name)
    catalog = json.loads(catalog_path().read_text())
    if len(catalog.get('models', [])) != 1 or catalog['models'][0].get('slug') != model:
        raise IntegrityError('Packaged model catalog mismatch')
    if catalog['models'][0].get('input_modalities') != ['text']:
        raise IntegrityError('Model catalog unexpectedly permits image input')
    return {'python': sys.executable, 'libreoffice_app': str(app.resolve()),
            'catalog_sha256': sha(catalog_path()), 'model': model, 'effort': effort}


def create_context(mode: str, system: str, model: str, effort: str, *, authenticate=True):
    _identity(model, effort)
    if mode not in MODES:
        raise IntegrityError('Unsupported isolated mode: '+mode)
    workspace = Path(tempfile.mkdtemp(prefix='wikiskill-episode-', dir='/private/tmp')).resolve()
    control = Path(tempfile.mkdtemp(prefix='wikiskill-control-', dir='/private/tmp')).resolve()
    (workspace/'tmp').mkdir()
    try:
        (control/'config.toml').write_text(config_text(workspace, control, mode, system, model, effort))
        (control/'outer.sb').write_text(outer_policy(workspace, control))
        if authenticate:
            source = Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')))/'auth.json'
            if not source.is_file():
                raise IntegrityError('Codex auth.json is unavailable in the caller CODEX_HOME')
            shutil.copyfile(source, control/'auth.json')
            (control/'auth.json').chmod(0o600)
    except BaseException:
        (control/'auth.json').unlink(missing_ok=True)
        raise
    env = {key: value for key, value in os.environ.items() if key in (
        'PATH', 'LANG', 'LC_ALL', 'USER', 'LOGNAME', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
        'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(CODEX_HOME=str(control), TMPDIR=str(workspace/'tmp'), ZDOTDIR=str(workspace/'tmp'), PYTHONNOUSERSITE='1')
    return workspace, control, env, [shutil.which('codex') or 'codex']


def copy_payload(source: Path, target: Path) -> None:
    for path in source.iterdir():
        if path.name in EXCLUDED_PAYLOAD:
            continue
        if path.is_symlink() or (path.is_dir() and any(p.is_symlink() for p in path.rglob('*'))):
            raise IntegrityError('Role payload contains a symlink')
        dest = target/path.name
        if path.is_dir():
            shutil.copytree(path, dest)
        elif path.is_file():
            shutil.copy2(path, dest)
        else:
            raise IntegrityError('Role payload is not a regular file/directory')


def install_spreadsheet_dependencies(workspace: Path, libreoffice_app: Path) -> None:
    libs = workspace/'tool_libs'
    libs.mkdir(exist_ok=True)
    for name in ('openpyxl', 'et_xmlfile'):
        spec = importlib.util.find_spec(name)
        if not spec or not spec.submodule_search_locations:
            raise IntegrityError('Missing workbook dependency: '+name)
        shutil.copytree(next(iter(spec.submodule_search_locations)), libs/name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    binary = workspace/'bin'
    binary.mkdir(exist_ok=True)
    for name in ('python', 'python3'):
        path = binary/name
        path.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' -S "$@"\n')
        path.chmod(0o755)
    local_app = workspace/'LibreOfficeDev.app'
    copied = subprocess.run(['/bin/cp', '-cR', str(libreoffice_app.resolve()), str(local_app)], capture_output=True)
    if copied.returncode:
        if local_app.exists():
            shutil.rmtree(local_app)
        shutil.copytree(libreoffice_app, local_app, symlinks=True)
    path = binary/'soffice'
    path.write_text('#!/bin/sh\nexec '+shlex.quote(str(local_app/'Contents/MacOS/soffice'))+' '
                    +shlex.quote('-env:UserInstallation='+(workspace/'lo-profile').as_uri())+' "$@"\n')
    path.chmod(0o755)


def inspect_context(prefix, env, workspace: Path) -> dict:
    proc = subprocess.run(prefix+['debug', 'prompt-input', 'Isolated research task.'], cwd=workspace,
                          env=env, capture_output=True, text=True, timeout=60, check=True)
    data = json.loads(proc.stdout)
    text = '\n'.join(content.get('text', '') for message in data for content in message.get('content', []))
    markers = ('MEMORY_SUMMARY', 'Use memory by default', '~/.codex/memories', '### Available skills')
    if any(marker in text for marker in markers):
        raise IntegrityError('Uncontrolled runtime memory or personal skill instructions')
    import hashlib
    return {'memory_injected': False, 'personal_skill_catalog': False,
            'input_sha256': hashlib.sha256(proc.stdout.encode()).hexdigest()}


def verify_boundary(workspace: Path, control: Path, env=None, prefix=None) -> dict:
    """Eight guaranteed existing canaries, through the actual shell policy."""
    sibling = Path(tempfile.mkdtemp(prefix='wikiskill-denied-', dir='/private/tmp')).resolve()
    names = ('benchmark-answer.txt', 'cross-arm-trace.jsonl', 'memory.md', 'validation.csv')
    for name in names:
        (sibling/name).write_text('synthetic evaluator-only canary')
    (control/'probe-auth.json').write_text('synthetic authentication canary')
    targets = [str(sibling/name) for name in names]+[str(control/name) for name in ('config.toml', 'probe-auth.json')]+[str(catalog_path())]
    (workspace/'allowed.txt').write_text('permitted evidence')
    (workspace/'escape').symlink_to(sibling/names[0])
    script = '''import json, pathlib, socket
assert pathlib.Path('allowed.txt').read_text() == 'permitted evidence'
paths = TARGETS + ['escape']
results = {}
for value in paths:
    try:
        with open(value) as stream: stream.read(1)
        results[value] = 'READABLE'
    except PermissionError: results[value] = 'DENIED'
assert set(results.values()) == {'DENIED'}, results
pathlib.Path('scratch-ok.txt').write_text('write works')
s = socket.socket()
try:
    s.bind(('127.0.0.1', 0))
    raise AssertionError('tool network unexpectedly enabled')
except PermissionError: pass
print(json.dumps({'forbidden_read_tests':len(paths), 'denied':len(paths), 'network_denied':True, 'scratch_write':True}))
'''.replace('TARGETS', repr(targets))
    try:
        proc = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(control/'outer.sb'), sys.executable, '-S', '-c', script],
                              cwd=workspace, env=shell_environment(workspace, sys.executable),
                              capture_output=True, text=True, timeout=60)
        if proc.returncode:
            raise IntegrityError('Read isolation probe failed: '+proc.stdout+proc.stderr)
        result = json.loads(proc.stdout)
        if result.get('forbidden_read_tests') != 8 or result.get('denied') != 8:
            raise IntegrityError('Eight forbidden reads were not denied')
        return result
    finally:
        (workspace/'escape').unlink(missing_ok=True)
        (workspace/'allowed.txt').unlink(missing_ok=True)
        (workspace/'scratch-ok.txt').unlink(missing_ok=True)
        (control/'probe-auth.json').unlink(missing_ok=True)
        shutil.rmtree(sibling)


def _probe_mcp(workspace: Path, control: Path, mode: str) -> dict:
    requests = [{'jsonrpc': '2.0', 'id': i, 'method': method} for i, method in enumerate(
        ('initialize', 'tools/list', 'resources/list', 'resources/templates/list'), 1)]
    proc = subprocess.run([sys.executable, '-I', '-m', 'wikiskill.isolated.tools_server', '--mode', mode,
                           '--workspace', str(workspace), '--control', str(control), '--python', sys.executable],
                          input='\n'.join(json.dumps(request) for request in requests)+'\n',
                          cwd=workspace, capture_output=True, text=True, timeout=30)
    if proc.returncode:
        raise IntegrityError('Installed MCP module failed to launch: '+proc.stderr)
    responses = [json.loads(line) for line in proc.stdout.split('\n') if line.strip()]
    if (len(responses) != 4 or responses[1].get('result', {}).get('tools') != specs(mode)
            or responses[2].get('result') != {'resources': []}
            or responses[3].get('result') != {'resourceTemplates': []}):
        raise IntegrityError('MCP tool inventory/empty discovery probe failed')
    return {'module_launch': True, 'mode': mode, 'tools': [tool['name'] for tool in specs(mode)],
            'resources_empty': True, 'resource_templates_empty': True}


def preflight(*, libreoffice_app: Path, model='gpt-5.6-luna', effort='high') -> dict:
    resources = _resources(libreoffice_app, model, effort)
    workspace, control, env, prefix = create_context('spreadsheet', 'Isolated research preflight.', model, effort, authenticate=False)
    try:
        install_spreadsheet_dependencies(workspace, Path(libreoffice_app))
        context = inspect_context(prefix, env, workspace)
        boundary = verify_boundary(workspace, control)
        # The controller is unsandboxed and can read auth. Prove its isolated
        # import ignores attacker-controlled CWD and sitecustomize on reconnect.
        (workspace/'sitecustomize.py').write_text('raise RuntimeError("workspace sitecustomize executed")\n')
        (workspace/'wikiskill').mkdir()
        (workspace/'wikiskill/__init__.py').write_text('raise RuntimeError("workspace package executed")\n')
        mcp = [_probe_mcp(workspace, control, mode) for mode in MODES]
        (workspace/'sitecustomize.py').unlink()
        shutil.rmtree(workspace/'wikiskill')
        from .tools_server import RoleTools
        shell = RoleTools(workspace, control, 'spreadsheet', sys.executable)
        result = shell.call('bash', {'command': "python -c 'import openpyxl; print(openpyxl.__version__)' && soffice --headless --version"})
        if result['exit_code'] or 'LibreOffice' not in result['stdout']:
            raise IntegrityError('Spreadsheet dependency sandbox probe failed: '+json.dumps(result))
        history = Path(str(files('wikiskill').joinpath('resources/research/snapshot.json')))
        if not history.is_file():
            raise IntegrityError('Packaged research resource is missing; cannot verify its read denial')
        code = ('import pathlib\ntry:\n pathlib.Path('+repr(str(history))+').read_bytes()\n'
                'except PermissionError:\n print("PACKAGED_RESEARCH_DENIED")\n'
                'else:\n raise AssertionError("packaged research unexpectedly readable")\n')
        package_probe = shell.call('bash', {'command': 'python -c '+shlex.quote(code)})
        if package_probe['exit_code'] or package_probe['stdout'].strip() != 'PACKAGED_RESEARCH_DENIED':
            raise IntegrityError('Installed historical research read isolation failed')
        return {'ok': True, 'model_calls': 0, 'resources': resources, 'context': context,
                'boundary': boundary, 'mcp': mcp, 'spreadsheet_dependencies': result,
                'packaged_research_denied': True, 'controller_cwd_shadowing_denied': True}
    finally:
        (control/'auth.json').unlink(missing_ok=True)
        shutil.rmtree(workspace)
        shutil.rmtree(control)


def _copy_records(workspace: Path, control: Path, archive: Path, *, thread_id='') -> None:
    for name in ('config.toml', 'outer.sb', 'final.txt', 'submission.json', 'tool-events.jsonl'):
        if (control/name).is_file() and not (archive/name).exists():
            shutil.copy2(control/name, archive/name)
    sessions = list((control/'sessions').rglob('*'+thread_id+'.jsonl')) if thread_id else []
    if len(sessions) == 1 and not (archive/'session.jsonl').exists():
        shutil.copy2(sessions[0], archive/'session.jsonl')
    if (workspace/'output.xlsx').exists() and not (archive/'output.xlsx').exists():
        if (workspace/'output.xlsx').is_symlink():
            raise IntegrityError('Output workbook is a symlink')
        shutil.copy2(workspace/'output.xlsx', archive/'output.xlsx')


def execute(payload: Path, system: str, user: str, mode: str, timeout=1800, *,
            libreoffice_app: Path, model='gpt-5.6-luna', effort='high') -> Path:
    _identity(model, effort)
    if mode not in MODES:
        raise IntegrityError('Unsupported isolated mode: '+mode)
    payload = Path(payload).resolve()
    archive = payload.parent/'runtime'
    system = system.replace('\r\n', '\n').replace('\r', '\n')
    user = user.replace('\r\n', '\n').replace('\r', '\n')
    request = {'mode': mode, 'system': system, 'user_template': user, 'timeout': timeout, 'model': model,
               'effort': effort, 'libreoffice_app': str(Path(libreoffice_app).absolute())}
    if (archive/'native-complete.json').exists():
        if json.loads((archive/'request.json').read_text()) != request:
            raise IntegrityError('Completed request changed')
        verify_native_complete(archive)
        report = audit(archive, mode, model=model, effort=effort)
        if not (archive/'audit.json').exists():
            write_json(archive/'audit.json', report)
        return archive
    if archive.exists():
        raise IntegrityError('Unsealed native attempt preserved; no automatic model retry')
    archive.mkdir(parents=True)
    write_json(archive/'request.json', request)
    workspace = control = None
    thread_id = ''
    try:
        _resources(libreoffice_app, model, effort)
        workspace, control, env, prefix = create_context(mode, system, model, effort)
        copy_payload(payload, workspace)
        if mode == 'spreadsheet':
            install_spreadsheet_dependencies(workspace, Path(libreoffice_app))
        context = inspect_context(prefix, env, workspace)
        boundary = verify_boundary(workspace, control)
        rendered = user.replace('__WORKSPACE__', str(workspace))
        (archive/'system.md').write_text(system)
        (archive/'user.md').write_text(rendered)
        cmd = prefix+['exec', '--strict-config', '--ignore-rules', '--skip-git-repo-check', '--cd', str(workspace),
                      '-m', model, '--json', '--output-last-message', str(control/'final.txt'), '-']
        write_json(archive/'invocation.json', {'argv': cmd, 'workspace': str(workspace), 'control': str(control),
                   'mode': mode, 'model': model, 'effort': effort, 'boundary': boundary, 'context': context,
                   'system_sha256': sha(archive/'system.md')})
        start = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        child = subprocess.Popen(cmd, cwd=workspace, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = child.communicate(rendered, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                stdout, stderr = child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                stdout, stderr = child.communicate()
        (archive/'events.jsonl').write_text(stdout)
        (archive/'stderr.log').write_text(stderr)
        thread_id = extract_thread_id(stdout)
        _copy_records(workspace, control, archive, thread_id=thread_id)
        if timed_out:
            raise IntegrityError('Episode timeout; raw partial output preserved')
        events = read_jsonl(archive/'events.jsonl')
        if (child.returncode or not any(event.get('type') == 'turn.completed' for event in events)
                or not (archive/'session.jsonl').exists() or not (archive/'final.txt').exists()):
            raise IntegrityError('Native call incomplete')
        artifacts = {path.name: sha(path) for path in archive.iterdir() if path.is_file()
                     and path.name not in ('audit.json', 'native-complete.json', 'failure.json')}
        write_json(archive/'native-complete.json', {'duration': time.monotonic()-start, 'started_at': started_at,
                   'finished_at': datetime.now(timezone.utc).isoformat(), 'artifacts': artifacts})
        write_json(archive/'audit.json', audit(archive, mode, model=model, effort=effort))
        return archive
    except BaseException as exc:
        preservation_error = None
        if workspace is not None and control is not None:
            try:
                _copy_records(workspace, control, archive, thread_id=thread_id)
            except Exception as copy_error:
                preservation_error = f'{type(copy_error).__name__}: {copy_error}'
        if not (archive/'failure.json').exists():
            record = {'error': f'{type(exc).__name__}: {exc}'}
            if preservation_error:
                record['record_preservation_error'] = preservation_error
            write_json(archive/'failure.json', record)
        raise
    finally:
        if control is not None:
            (control/'auth.json').unlink(missing_ok=True)
