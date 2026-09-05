"""Exclusive lock so two K=4 drivers cannot share one arm directory."""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from contextlib import contextmanager

_HELD: list[int] = []


def acquire_k4_lock(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".k4.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit(f"K=4 already running for {root} ({path})") from exc
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode("utf-8"))
    _HELD.append(fd)


@contextmanager
def workspace_lock(root: Path):
    """Release the lock when an embedded/API invocation returns."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.k4.lock').open('a+') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f'Workspace already running: {root}') from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
