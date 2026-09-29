"""Exclusive lock so two K=4 drivers cannot share one arm directory."""

from __future__ import annotations

import os
from pathlib import Path
from contextlib import contextmanager

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

_HELD: list[int] = []


def _lock(fd: int) -> None:
    if os.name == 'nt':
        # msvcrt.locking locks a byte range, so ensure byte zero exists first.
        if os.fstat(fd).st_size == 0:
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, b'0')
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(fd: int) -> None:
    if os.name == 'nt':
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)


def acquire_k4_lock(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = root / '.k4.lock'
    fd = os.open(path, os.O_CREAT | os.O_RDWR)
    try:
        _lock(fd)
    except OSError as exc:
        os.close(fd)
        raise SystemExit(f'K=4 already running for {root} ({path})') from exc
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, f'{os.getpid()}\n'.encode('utf-8'))
    _HELD.append(fd)


@contextmanager
def workspace_lock(root: Path):
    """Release the lock when an embedded/API invocation returns."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.k4.lock').open('a+b') as handle:
        try:
            _lock(handle.fileno())
        except OSError as exc:
            raise RuntimeError(f'Workspace already running: {root}') from exc
        try:
            yield
        finally:
            _unlock(handle.fileno())
