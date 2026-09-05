"""Drive one OfficeQA item through ``codex exec`` and score the transcript."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wikiskill.codex_identity import (
    ModelIdentityError,
    assert_requested_model,
    extract_reported_model,
    extract_thread_id,
)
from wikiskill.officeqa.dataset import (
    OfficeQACase,
    OfficeQADatasetError,
)
from wikiskill.officeqa.scoring import score_stdout

SCRATCH_DIR = Path("scratch") / "officeqa-rollout"
SKILL_SECTION_HEADER = "## Active skill (injected verbatim)"
DEFAULT_TIMEOUT_SECONDS = 1200

_COMMON_FRAME = """You are answering one OfficeQA question from local U.S. Treasury Bulletin text files.

The only evidence you may use is the files listed below, already copied into this workspace under `docs/`. Search them with glob, rg/grep, and Read. Do not use the network. Do not browse FRASER or any other website.

Write a short working trace if you need one, then emit the scored answer in this exact wrapper — the scorer reads the last <FINAL_ANSWER>…</FINAL_ANSWER> span and ignores everything else:

<FINAL_ANSWER>
your answer
</FINAL_ANSWER>

The scored span must be a single-line direct answer (a number, a short phrase, or a short list). Do not put an explanation inside the wrapper. Do not use <answer> tags.
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_prompt(case: OfficeQACase, skill_text: str) -> str:
    files = "\n".join(f"- docs/{name}" for name in case.source_files)
    prompt = (
        f"{_COMMON_FRAME}\n"
        f"## Question\n\n{case.question}\n\n"
        f"## Local source files\n\n{files}\n"
    )
    if skill_text.strip():
        prompt += f"\n{SKILL_SECTION_HEADER}\n\n{skill_text}\n"
    return prompt


def stage_workspace(case: OfficeQACase, workspace: Path) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    docs = workspace / "docs"
    docs.mkdir(parents=True)
    for name, source in zip(case.source_files, case.corpus_paths, strict=True):
        shutil.copy2(source, docs / name)
    (workspace / "question.md").write_text(
        f"# {case.uid}\n\n{case.question}\n", encoding="utf-8"
    )


def run_codex_exec(
    *,
    prompt: str,
    workdir: Path,
    model: str,
    reasoning_effort: str,
    timeout_seconds: int,
    json_events: bool = False,
    output_last_message: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "codex",
        "exec",
        "--cd",
        str(workdir),
        "-s",
        "workspace-write",
        "--skip-git-repo-check",
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
        "-m",
        model,
    ]
    if json_events:
        cmd.append("--json")
    if output_last_message is not None:
        cmd += ["--output-last-message", str(output_last_message)]
    cmd.append("-")
    env = dict(os.environ)
    env.pop("CODEX_HOME", None)
    return subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout_seconds,
    )


def _fail_reason(*, returncode: int | None, tagged: bool, score: float) -> str:
    if returncode is None:
        return "exec_raised"
    if returncode != 0:
        return "exec_failed"
    if score >= 1.0:
        return ""
    if not tagged:
        return "missing_final_answer"
    return "wrong_answer"


def rollout_case(
    case: OfficeQACase,
    *,
    workdir: Path,
    model: str,
    reasoning_effort: str = "medium",
    skill_text: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    tolerance: float = 0.0,
) -> dict[str, Any]:
    """Stage, exec, score.  Gold answers are used only to score, not written."""
    if case.missing_files:
        raise OfficeQADatasetError(
            f"{case.uid} is missing source files: {list(case.missing_files)}"
        )
    workspace = Path(workdir) / case.uid
    prompt = build_prompt(case, skill_text)
    skill_sha = _sha256_text(skill_text) if skill_text.strip() else hashlib.sha256(b"").hexdigest()
    prompt_sha = _sha256_text(prompt)
    stage_workspace(case, workspace)
    scratch = workspace / SCRATCH_DIR
    scratch.mkdir(parents=True)
    (scratch / "injected_prompt.md").write_text(prompt, encoding="utf-8")

    started = _now()
    returncode: int | None = None
    stdout = ""
    stderr = ""
    error = ""
    last_message_path = scratch / "last_message.txt"
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
    except Exception as exc:  # noqa: BLE001 - recorded, then scored as 0
        error = f"{type(exc).__name__}: {exc}"

    (scratch / "codex_stdout.txt").write_text(stdout, encoding="utf-8")
    (scratch / "codex_stderr.txt").write_text(stderr, encoding="utf-8")
    score, predicted, tagged = score_stdout(
        case.answer, stdout, tolerance=tolerance
    )
    if returncode not in (0, None) or error:
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
    record = {
        "schema_version": "briefloop.officeqa.outcome.v1",
        "case_id": case.uid,
        "uid": case.uid,
        "split": case.split,
        "difficulty": case.difficulty,
        "model": model,
        "requested_model": model,
        "reported_model": reported_model,
        "thread_id": thread_id,
        "reasoning_effort": reasoning_effort,
        "skill_sha256": skill_sha,
        "prompt_sha256": prompt_sha,
        "score": score,
        "predicted": predicted,
        "has_final_answer_tag": tagged,
        "returncode": returncode,
        "workspace": str(workspace),
        "fail_reason": (
            "model_identity"
            if identity_error
            else _fail_reason(returncode=returncode, tagged=tagged, score=score)
            or (error and "exec_raised")
            or ""
        ),
        "source_files": list(case.source_files),
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": (finished - started).total_seconds(),
        "error": identity_error or error,
    }
    (scratch / "outcome.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    if identity_error:
        raise ModelIdentityError(identity_error)
    return record
