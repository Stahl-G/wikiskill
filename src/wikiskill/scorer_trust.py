"""Local, non-portable approval receipts for configured scorer commands."""
from pathlib import Path
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
import shutil


def _hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def describe(root,config):
    command=config.get('scorer')
    if not command:return {'configured':False,'trusted':True}
    project=Path(config['project']).resolve()
    executable=Path(command[0])
    if executable.is_absolute() or executable.parent!=Path('.') or '/' in command[0] or '\\' in command[0]:
        executable=(project/executable).absolute()
    else:
        found=shutil.which(command[0])
        if not found:raise ValueError('Scorer executable unavailable: '+command[0])
        executable=Path(found).absolute()
    if not executable.is_file():raise ValueError('Scorer executable is not a file')
    files={str(executable.resolve()):_hash(executable)}
    venv=executable.parent.parent/'pyvenv.cfg'
    if venv.is_file():files[str(venv.resolve())]=_hash(venv)
    for arg in command[1:]:
        try:
            path=(project/arg).resolve()
            if path.is_file():files[str(path)]=_hash(path)
        except ValueError:
            pass  # A non-path argument is still bound verbatim.
        except OSError as exc:
            if exc.errno not in (errno.ENAMETOOLONG,errno.EINVAL,errno.ENOENT,errno.ENOTDIR):raise
    binding={'workspace':str(Path(root).resolve()),'command':command,'resolved_executable':str(executable),
             'working_directory':str(project),'timeout_seconds':config['scorer_timeout'],'direct_file_sha256':files}
    fingerprint=_digest(binding);receipt=_store()/f'{fingerprint}.json'
    trusted=False
    if receipt.is_file():
        try:trusted=json.loads(receipt.read_text()).get('binding')==binding
        except (ValueError,OSError):pass
    return {'configured':True,**binding,'fingerprint':fingerprint,'trusted':trusted,
            'scope':'Runs with normal host permissions; direct files are fingerprinted, not every imported dependency.'}


def _store():
    return Path(os.environ.get('WIKISKILL_TRUST_DIR',str(Path.home()/'.wikiskill/scorer-trust')))


def approve(root,config,fingerprint):
    info=describe(root,config)
    if not info['configured']:raise ValueError('No external scorer configured')
    if info['fingerprint']!=fingerprint:raise ValueError('Scorer changed since inspection; inspect it again')
    binding={k:info[k] for k in ('workspace','command','resolved_executable','working_directory','timeout_seconds','direct_file_sha256')}
    folder=_store();folder.mkdir(parents=True,exist_ok=True)
    path=folder/(fingerprint+'.json')
    if not path.exists():
        with path.open('x',encoding='utf-8') as f:json.dump({'binding':binding,'approved_at':datetime.now(timezone.utc).isoformat()},f,indent=2)
        try:path.chmod(0o600)
        except OSError:pass
    return describe(root,config)


def require(root,config):
    info=describe(root,config)
    if info['configured'] and not info['trusted']:
        raise RuntimeError('Scorer requires local authorization. Run scorer inspect, review its command and working directory, then scorer trust with that fingerprint. No command was executed.')
    return info
