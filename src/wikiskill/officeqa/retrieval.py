"""OfficeQA Full retrieval-mode rollout: whole corpus, no staged docs/.

Staged OfficeQA copies cited bulletins into ``docs/`` and lists them in the
prompt. This variant keeps the same cases, scorer, and FINAL_ANSWER contract
but withholds the file list: the agent must search ``corpus/``. Scores are a
separate evidence mode and must never be mixed with staged tables.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from wikiskill.codex_identity import (
    ModelIdentityError,
    assert_requested_model,
    extract_reported_model,
    extract_thread_id,
)
from wikiskill.officeqa.dataset import (
    DEFAULT_CORPUS_DIR,
    OfficeQACase,
    OfficeQADatasetError,
)
from wikiskill.officeqa.rollout import (
    SCRATCH_DIR,
    SKILL_SECTION_HEADER,
    _fail_reason,
    _now,
    _sha256_text,
    run_codex_exec,
)
from wikiskill.officeqa.scoring import score_stdout


DEFAULT_RETRIEVAL_CORPUS = (
    DEFAULT_CORPUS_DIR / "treasury_bulletins_parsed" / "transformed"
)
RETRIEVAL_TIMEOUT_SECONDS = 1800
EVIDENCE_MODE = "retrieval"

RETRIEVAL_FRAME = """You are answering one OfficeQA question against a local corpus of U.S. Treasury Bulletin text files.

The corpus is in this workspace under `corpus/` — hundreds of plain-text Treasury bulletins. No file list is provided: you must locate the evidence yourself using glob, rg/grep, and Read. Do not use the network. Do not browse FRASER or any other website.

Work like a professional archivist: narrow by year and document family first, then search entity and measure terms (including period naming variants), then read the relevant tables closely. Multi-step arithmetic is allowed after extracting exact operands.

Write a short working trace if you need one, then emit the scored answer in this exact wrapper — the scorer reads the last <FINAL_ANSWER>…</FINAL_ANSWER> span and ignores everything else:

<FINAL_ANSWER>
your answer
</FINAL_ANSWER>

The scored span must be a single-line direct answer (a number, a short phrase, or a short list). Do not put an explanation inside the wrapper. Do not use <answer> tags.
"""


def build_retrieval_prompt(case: OfficeQACase, skill_text: str) -> str:
    prompt = f"{RETRIEVAL_FRAME}\n## Question\n\n{case.question}\n"
    if skill_text.strip():
        prompt += f"\n{SKILL_SECTION_HEADER}\n\n{skill_text}\n"
    leaked = [name for name in case.source_files if name and name in prompt]
    if leaked:
        raise OfficeQADatasetError(
            f"retrieval prompt must not name source files: {leaked}"
        )
    if "docs/" in prompt:
        raise OfficeQADatasetError("retrieval prompt must not point at staged docs/")
    return prompt


def stage_retrieval_workspace(workspace: Path, corpus_dir: Path) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    target = corpus_dir.resolve()
    if not target.is_dir():
        raise OfficeQADatasetError(f"retrieval corpus missing: {target}")
    (workspace / "corpus").symlink_to(target, target_is_directory=True)
    # question.md is operator context only; it does not list source files.


def rollout_retrieval_case(
    case: OfficeQACase,
    *,
    workdir: Path,
    model: str,
    reasoning_effort: str = "medium",
    skill_text: str = "",
    timeout_seconds: int = RETRIEVAL_TIMEOUT_SECONDS,
    tolerance: float = 0.0,
    corpus_dir: Path = DEFAULT_RETRIEVAL_CORPUS,
) -> dict[str, Any]:
    """Search the full corpus. Gold answers are used only to score, not written."""
    workspace = Path(workdir) / case.uid
    prompt = build_retrieval_prompt(case, skill_text)
    skill_sha = _sha256_text(skill_text) if skill_text.strip() else "0" * 64
    prompt_sha = _sha256_text(prompt)
    stage_retrieval_workspace(workspace, corpus_dir)
    (workspace / "question.md").write_text(
        f"# {case.uid}\n\n{case.question}\n", encoding="utf-8"
    )
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
        "evidence_mode": EVIDENCE_MODE,
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
