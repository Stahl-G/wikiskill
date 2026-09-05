"""Drive one SpreadsheetBench item through ``codex exec`` and score the workbook."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wikiskill.benchmarks.spreadsheet import (
    SYSTEM_PROMPT,
    SpreadsheetCase,
    score_workbook,
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


def build_prompt(case: SpreadsheetCase, skill_text: str, workspace: Path) -> str:
    skill_section = ""
    if skill_text.strip():
        skill_section = f"{SKILL_SECTION_HEADER}\n\n{skill_text.strip()}"
    input_path = workspace / case.init_name
    output_path = workspace / "output.xlsx"
    body = (
        f"working_directory: {workspace}\n"
        f"instruction: {case.instruction}\n"
        f"input_path: {input_path}\n"
        f"output_path: {output_path}\n"
        "Write concrete values (not formulas) into the answer region. "
        "Copy input_path to output_path first if you need a starting workbook.\n"
    )
    return SYSTEM_PROMPT.format(skill_section=skill_section) + "\n\n" + body


def rollout_case(
    case: SpreadsheetCase,
    *,
    workdir: Path,
    model: str,
    reasoning_effort: str = "medium",
    skill_text: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    split: str = "val",
) -> dict[str, Any]:
    workspace = Path(workdir) / case.task_id
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    source = Path(case.task_dir)
    shutil.copy2(source / case.init_name, workspace / case.init_name)
    prompt = build_prompt(case, skill_text, workspace)
    skill_sha = _sha256_text(skill_text) if skill_text.strip() else hashlib.sha256(b"").hexdigest()
    prompt_sha = _sha256_text(prompt)
    scratch = workspace / SCRATCH_DIR
    scratch.mkdir(parents=True)
    (scratch / "injected_prompt.md").write_text(prompt, encoding="utf-8")
    last_message_path = scratch / "last_message.txt"
    output_path = workspace / "output.xlsx"

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
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "codex_events.jsonl").write_text(proc.stdout, encoding="utf-8")
        if last_message_path.is_file():
            stdout = last_message_path.read_text(encoding="utf-8")
        else:
            stdout = proc.stdout
    except ModelIdentityError:
        raise
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "codex_stdout.txt").write_text(stdout, encoding="utf-8")
    (scratch / "codex_stderr.txt").write_text(stderr, encoding="utf-8")
    score = 0.0
    matched = 0
    total = 0
    tagged = output_path.is_file()
    scoring_error = ""
    if returncode == 0 and not error and tagged:
        try:
            score, matched, total = score_workbook(
                output_path,
                source / case.golden_name,
                case.answer_sheet,
                case.answer_position,
            )
            if total == 0:
                scoring_error = "score_workbook compared zero cells"
                score = 0.0
        except Exception as exc:  # noqa: BLE001
            scoring_error = f"{type(exc).__name__}: {exc}"
            score = 0.0
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
    elif scoring_error:
        fail_reason = "score_failed"
    elif returncode is None or error:
        fail_reason = "exec_raised"
    elif returncode != 0:
        fail_reason = "exec_failed"
    elif score >= 1.0:
        fail_reason = ""
    elif not tagged:
        fail_reason = "missing_output_workbook"
    else:
        fail_reason = "wrong_answer"
    record = {
        "schema_version": "briefloop.spreadsheet.outcome.v1",
        "case_id": case.task_id,
        "uid": case.task_id,
        "split": split,
        "model": model,
        "requested_model": model,
        "reported_model": reported_model,
        "thread_id": thread_id,
        "reasoning_effort": reasoning_effort,
        "skill_sha256": skill_sha,
        "prompt_sha256": prompt_sha,
        "score": score,
        "matched_cells": matched,
        "total_cells": total,
        "predicted": stdout.strip()[:500],
        "has_output_workbook": tagged,
        "returncode": returncode,
        "workspace": str(workspace),
        "fail_reason": fail_reason,
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": (finished - started).total_seconds(),
        "error": identity_error or scoring_error or error or stderr[-2000:],
    }
    (scratch / "outcome.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    if identity_error:
        raise ModelIdentityError(identity_error)
    return record
