"""Drive one LiveMath item through ``codex exec`` and score the ``<answer>`` tag."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wikiskill.benchmarks.livemath import (
    SYSTEM_PROMPT,
    LiveMathCase,
    has_answer_tag,
    score_answer,
)
from wikiskill.codex_identity import (
    ModelIdentityError,
    assert_requested_model,
    extract_reported_model,
    extract_thread_id,
)
from wikiskill.officeqa.rollout import (
    DEFAULT_TIMEOUT_SECONDS,
    SCRATCH_DIR,
    SKILL_SECTION_HEADER,
    run_codex_exec,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_prompt(case: LiveMathCase, skill_text: str) -> str:
    skill_section = ""
    if skill_text.strip():
        skill_section = f"{SKILL_SECTION_HEADER}\n\n{skill_text.strip()}"
    return SYSTEM_PROMPT.format(skill_section=skill_section) + "\n\n" + case.user_prompt()


def rollout_case(
    case: LiveMathCase,
    *,
    workdir: Path,
    model: str,
    reasoning_effort: str = "medium",
    skill_text: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    split: str = "val",
) -> dict[str, Any]:
    workspace = Path(workdir) / case.uid
    workspace.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(case, skill_text)
    skill_sha = _sha256_text(skill_text) if skill_text.strip() else hashlib.sha256(b"").hexdigest()
    prompt_sha = _sha256_text(prompt)
    scratch = workspace / SCRATCH_DIR
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "injected_prompt.md").write_text(prompt, encoding="utf-8")
    last_message_path = scratch / "last_message.txt"

    started = _now()
    returncode: int | None = None
    stdout = ""
    stderr = ""
    error = ""
    try:
        proc = run_codex_exec(
            prompt=prompt,
            workdir=workspace,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout_seconds=timeout_seconds,
            json_events=True,
            output_last_message=last_message_path,
        )
        returncode = proc.returncode
        stderr = proc.stderr
        (scratch / "codex_events.jsonl").write_text(proc.stdout, encoding="utf-8")
        if last_message_path.is_file():
            stdout = last_message_path.read_text(encoding="utf-8")
        else:
            stdout = proc.stdout
    except ModelIdentityError:
        raise
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    (scratch / "codex_stdout.txt").write_text(stdout, encoding="utf-8")
    (scratch / "codex_stderr.txt").write_text(stderr, encoding="utf-8")
    tagged = has_answer_tag(stdout)
    score = 0.0 if returncode not in (0,) or error else score_answer(
        case.correct_label, stdout
    )
    events_text = ""
    events_path = scratch / "codex_events.jsonl"
    if events_path.is_file():
        events_text = events_path.read_text(encoding="utf-8", errors="replace")
    thread_id = extract_thread_id(events_text)
    reported_model = extract_reported_model(
        stdout=stdout,
        stderr=stderr,
        events_text=events_text,
        thread_id=thread_id,
    )
    if not reported_model and thread_id and not error:
        for _ in range(5):
            time.sleep(0.2)
            reported_model = extract_reported_model(thread_id=thread_id)
            if reported_model:
                break
    identity_error = ""
    try:
        if not error:
            assert_requested_model(model, reported_model)
    except ModelIdentityError as exc:
        identity_error = str(exc)
        score = 0.0
    finished = _now()
    if identity_error:
        fail_reason = "model_identity"
    elif returncode is None or error:
        fail_reason = "exec_raised"
    elif returncode != 0:
        fail_reason = "exec_failed"
    elif score >= 1.0:
        fail_reason = ""
    elif not tagged:
        fail_reason = "missing_final_answer"
    else:
        fail_reason = "wrong_answer"
    record = {
        "schema_version": "briefloop.livemath.outcome.v1",
        "case_id": case.uid,
        "uid": case.uid,
        "split": split,
        "model": model,
        "requested_model": model,
        "reported_model": reported_model,
        "thread_id": thread_id,
        "reasoning_effort": reasoning_effort,
        "skill_sha256": skill_sha,
        "prompt_sha256": prompt_sha,
        "score": score,
        "predicted": stdout.strip()[:500],
        "has_final_answer_tag": tagged,
        "returncode": returncode,
        "workspace": str(workspace),
        "fail_reason": fail_reason,
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": (finished - started).total_seconds(),
        "error": identity_error or error or stderr[-2000:],
    }
    (scratch / "outcome.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    if identity_error:
        raise ModelIdentityError(identity_error)
    return record
