"""ALFWorld episode driver: one ``codex exec``, agent steps via ``act.sh``."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wikiskill.benchmarks.alfworld import (
    SYSTEM_PROMPT,
    AlfWorldCase,
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

DRIVER_DIR = Path(__file__).resolve().parent
MAX_EPISODE_STEPS = 50

EPISODE_FRAME = """You are an expert agent operating in the ALFRED Embodied Environment.

{skill_section}

## How to act

This workspace contains `./act.sh`. Each call is one environment step. The
script prints the observation, whether you won, and the admissible actions.

- `./act.sh` with no arguments resets and prints the initial observation.
- `./act.sh <action>` applies one admissible action (copy the string exactly).

Do not invent actions outside the admissible list. After each observation,
reason in <think></think> tags, then choose the next action. Keep stepping
until won=true or you cannot progress. Maximum {max_steps} steps.

The per-step format from the paper still applies when you choose an action:

{paper_prompt}

## Task

{task_description}

Initial observation is also in observation.txt after you run `./act.sh`.
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _task_description(game_path: Path) -> str:
    traj = game_path.parent / "traj_data.json"
    if traj.is_file():
        payload = json.loads(traj.read_text(encoding="utf-8"))
        anns = payload.get("turk_annotations") or {}
        anns_list = anns.get("anns") or []
        if anns_list:
            desc = anns_list[0].get("task_desc") or anns_list[0].get("high_descs")
            if isinstance(desc, str) and desc.strip():
                return desc.strip()
        if payload.get("task_type"):
            return str(payload["task_type"])
    return game_path.parent.name


def slug_for(case: AlfWorldCase) -> str:
    return Path(case.game_path).parent.name


def stage_workspace(case: AlfWorldCase, workspace: Path) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    (workspace / "game.path").write_text(str(case.game_path) + "\n", encoding="utf-8")
    shutil.copy2(DRIVER_DIR / "act.sh", workspace / "act.sh")
    shutil.copy2(DRIVER_DIR / "step.py", workspace / "step.py")
    (workspace / "act.sh").chmod(
        (workspace / "act.sh").stat().st_mode | stat.S_IXUSR | stat.S_IXGRP
    )


def build_prompt(case: AlfWorldCase, skill_text: str) -> str:
    skill_section = ""
    if skill_text.strip():
        skill_section = f"{SKILL_SECTION_HEADER}\n\n{skill_text.strip()}"
    paper_prompt = SYSTEM_PROMPT.format(
        task_description=_task_description(case.game_path),
        skill_section=skill_section,
        step_count=0,
        history_length=0,
        action_history="(none yet; call ./act.sh to see the first observation)",
        current_step=1,
        current_observation="(run ./act.sh)",
        admissible_actions="(run ./act.sh)",
    )
    return EPISODE_FRAME.format(
        skill_section=skill_section,
        max_steps=MAX_EPISODE_STEPS,
        paper_prompt=paper_prompt,
        task_description=_task_description(case.game_path),
    )


def rollout_case(
    case: AlfWorldCase,
    *,
    workdir: Path,
    model: str,
    reasoning_effort: str = "medium",
    skill_text: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    split: str = "val",
) -> dict[str, Any]:
    workspace = Path(workdir) / slug_for(case)
    prompt = build_prompt(case, skill_text)
    skill_sha = _sha256_text(skill_text) if skill_text.strip() else hashlib.sha256(b"").hexdigest()
    prompt_sha = _sha256_text(prompt)
    stage_workspace(case, workspace)
    scratch = workspace / SCRATCH_DIR
    scratch.mkdir(parents=True)
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
    status_path = workspace / "status.json"
    won = False
    steps = 0
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        won = bool(status.get("won"))
        steps = int(status.get("step") or 0)
    score = 1.0 if returncode == 0 and not error and won else 0.0
    events_text = ""
    events_path = scratch / "codex_events.jsonl"
    if events_path.is_file():
        events_text = events_path.read_text(encoding="utf-8", errors="replace")
    thread_id = extract_thread_id(events_text)
    reported_model = extract_reported_model(
        stdout=stdout, stderr=stderr, events_text=events_text, thread_id=thread_id
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
        fail_reason = "exec_raised" if returncode is None else "exec_failed"
    elif returncode != 0:
        fail_reason = "exec_failed"
    elif score >= 1.0:
        fail_reason = ""
    else:
        fail_reason = "goal_unsatisfied"
    record = {
        "schema_version": "briefloop.alfworld.outcome.v1",
        "case_id": case.uid,
        "uid": case.uid,
        "slug": slug_for(case),
        "split": split,
        "model": model,
        "requested_model": model,
        "reported_model": reported_model,
        "thread_id": thread_id,
        "reasoning_effort": reasoning_effort,
        "skill_sha256": skill_sha,
        "prompt_sha256": prompt_sha,
        "score": score,
        "won": won,
        "steps": steps,
        "predicted": stdout.strip()[:500],
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
