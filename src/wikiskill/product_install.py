"""Explicit local SKILL.md installation with recoverable, hash-checked backups.

Only SKILL.md is replaced; existing supporting files remain untouched. This does
not deploy a multi-file skill bundle or override host filesystem permissions.
"""
from pathlib import Path
from uuid import uuid4
import hashlib
import os

from . import product as p


def _target(destination):
    destination = Path(destination).absolute()
    if destination.is_symlink() or (destination/'SKILL.md').is_symlink():
        raise ValueError('Choose a real skill directory and file, not a symlink')
    return destination.resolve()


def _replace(path, data):
    temporary = path.with_name('.SKILL.' + uuid4().hex + '.tmp')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install(root, destination, *, replace=False):
    root = Path(root).resolve()
    destination = _target(destination)
    if destination == root or destination.is_relative_to(root):
        raise ValueError('Install outside the workflow workspace')
    with p.locked(root):
        state = p._load(root)
        if state['phase'] != 'complete':
            raise ValueError('Finish the current loop before installing its retained skill')
        skill = state['current_skill']
        if not skill:
            raise ValueError('No retained skill to install; Wiki and candidate records remain available')
        data = (root/skill['file']).read_bytes()
        destination.mkdir(parents=True, exist_ok=True)
        local = destination/'.wikiskill-backups'
        if local.is_symlink():
            raise ValueError('Backup directory must not be a symlink')
        with p.locked(local):
            target = destination/'SKILL.md'
            if target.exists() and not target.is_file():
                raise ValueError('SKILL.md is not a regular file')
            old = target.read_bytes() if target.exists() else None
            if old == data:
                return {'skill': str(target), 'changed': False, 'sha256': skill['sha256']}
            if old is not None and not replace:
                raise ValueError('SKILL.md already exists; inspect it and use --replace for an authorized replacement')
            token = uuid4().hex
            backup = local/token
            backup.mkdir()
            if old is not None:
                (backup/'previous.md').write_bytes(old)
            receipt = {'id': token, 'destination': str(destination), 'created_at': p.now(),
                       'installed_sha256': skill['sha256'],
                       'previous_sha256': hashlib.sha256(old).hexdigest() if old is not None else None,
                       'source_event_sha256': state['last_hash'],
                       'workspace_fingerprint': p.digest(state['config'])}
            p.write(backup/'receipt.json', receipt, immutable=True)
            _replace(target, data)
            return {'skill': str(target), 'changed': True, 'sha256': skill['sha256'],
                    'backup_id': token, 'backup': str(backup),
                    'restore': f'wikiskill restore {str(destination)!r} --backup {token}'}


def restore(destination, backup_id):
    destination = _target(destination)
    if len(backup_id) != 32 or any(c not in '0123456789abcdef' for c in backup_id):
        raise ValueError('Use the backup ID returned by install')
    local = destination/'.wikiskill-backups'
    if not local.is_dir() or local.is_symlink():
        raise ValueError('No regular backup directory found')
    with p.locked(local):
        backup = local/backup_id
        if backup.is_symlink():
            raise ValueError('Backup must not be a symlink')
        receipt = p.read(backup/'receipt.json')
        if receipt['id'] != backup_id or receipt['destination'] != str(destination):
            raise ValueError('Backup belongs to a different destination')
        old = None
        if receipt['previous_sha256'] is not None:
            old = (backup/'previous.md').read_bytes()
            if hashlib.sha256(old).hexdigest() != receipt['previous_sha256']:
                raise ValueError('Backup content changed')
        target = destination/'SKILL.md'
        current = p.file_hash(target) if target.exists() else None
        if current == receipt['previous_sha256']:
            return {'skill': str(target), 'restored': True, 'changed': False}
        if current != receipt['installed_sha256']:
            raise ValueError('Installed skill changed since this backup; preserve those edits before restoring')
        if old is None:
            target.unlink()
        else:
            _replace(target, old)
        return {'skill': str(target), 'restored': True, 'changed': True,
                'sha256': receipt['previous_sha256']}
