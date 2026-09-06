"""Strict JSONL records split on physical LF, not Unicode text separators."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JSONLRecordError(ValueError):
    """A malformed physical JSONL record, with its source and line number."""


def loads_jsonl(text: str, *, source: str = '<memory>') -> list[Any]:
    records = []
    for number, line in enumerate(text.split('\n'), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise JSONLRecordError(
                f'{source}: physical line {number}: {exc.msg} at column {exc.colno}; '
                'record preserved, not skipped'
            ) from exc
    return records


def read_jsonl(path: str | Path) -> list[Any]:
    path = Path(path)
    return loads_jsonl(path.read_text(encoding='utf-8'), source=str(path))
