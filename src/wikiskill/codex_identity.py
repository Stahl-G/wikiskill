"""Assert Codex actually ran the requested model (no silent gpt-reserve downgrade)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODEL_LINE_RE = re.compile(r"(?m)^model:\s*(\S+)")
RESERVE_TOKEN = "gpt-reserve"


class ModelIdentityError(RuntimeError):
    """Requested model did not match the Codex echo; the rollout is void."""


def extract_thread_id(events_text: str) -> str:
    for line in (events_text or "").split('\n'):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            thread_id = str(event.get("thread_id") or "")
            if thread_id:
                return thread_id
    return ""


def model_from_session_file(path: Path) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").split('\n'):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        blob = json.dumps(payload)
        if RESERVE_TOKEN in blob.lower():
            return RESERVE_TOKEN
        if event.get("type") == "turn_context":
            model = payload.get("model")
            if isinstance(model, str) and model.strip():
                return model.strip()
            settings = (payload.get("collaboration_mode") or {}).get("settings") or {}
            nested = settings.get("model")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return ""


def find_session_rollout(
    thread_id: str, *, now: datetime | None = None
) -> Path | None:
    if not thread_id:
        return None
    now = now or datetime.now(timezone.utc)
    root = Path.home() / ".codex" / "sessions"
    days: list[str] = []
    local = datetime.now().astimezone()
    for stamp in (now, local, now - timedelta(days=1), local - timedelta(days=1)):
        day = stamp.strftime("%Y/%m/%d")
        if day not in days:
            days.append(day)
    for day in days:
        matches = sorted((root / day).glob(f"rollout-*-{thread_id}.jsonl"))
        if matches:
            return matches[-1]
    return None


def extract_reported_model(
    *,
    stdout: str = "",
    stderr: str = "",
    events_text: str = "",
    session_path: Path | None = None,
    thread_id: str = "",
) -> str:
    blob = "\n".join((stdout or "", stderr or "", events_text or ""))
    if RESERVE_TOKEN in blob.lower():
        return RESERVE_TOKEN
    match = MODEL_LINE_RE.search(blob)
    if match:
        return match.group(1).strip()
    path = session_path
    if path is None:
        tid = thread_id or extract_thread_id(events_text)
        path = find_session_rollout(tid)
    if path is not None:
        return model_from_session_file(path)
    return ""


def assert_requested_model(requested: str, reported: str) -> None:
    if not reported:
        raise ModelIdentityError(
            f"missing Codex model echo; cannot verify requested {requested!r}"
        )
    if RESERVE_TOKEN in reported.lower():
        raise ModelIdentityError(
            f"gpt-reserve silent downgrade (reported={reported!r}, requested={requested!r})"
        )
    if reported != requested:
        raise ModelIdentityError(
            f"model echo {reported!r} != requested {requested!r}; pause this arm"
        )
