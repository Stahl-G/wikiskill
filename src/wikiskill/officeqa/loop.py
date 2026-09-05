"""OfficeQA Eq. 4 loop: train → maintainer → proposer → val accept/rollback."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from wikiskill.settings import RESOURCES
from typing import Any, Callable

from wikiskill.codex_identity import ModelIdentityError
from wikiskill.officeqa.dataset import (
    DEFAULT_CORPUS_DIR,
    DEFAULT_CSV_PATH,
    DEFAULT_SPLIT_DIR,
    OfficeQACase,
    load_cases,
)
from wikiskill.officeqa.rollout import rollout_case
from wikiskill.officeqa.wiki_agents import (
    build_maintainer,
    build_proposer,
)
from wikiskill.wiki import (
    SkillImpactEntry,
    append_skill_impact,
)

PROTOCOL_PATH = (
    RESOURCES / "officeqa" / "protocol.json"
)
EXIT_ACCEPT = 0
EXIT_REJECT = 1
EXIT_INFRA = 2
_INFRA_FAIL_REASONS = frozenset(
    {"exec_failed", "exec_raised", "model_identity", "score_failed"}
)
_TRY_AGAIN_RE = re.compile(r"try again at\s+(\d{1,2}:\d{2}\s*[AP]M)", re.I)
_TRY_AGAIN_DATE_RE = re.compile(
    r"try again at\s+([A-Z][a-z]{2} \d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)",
    re.I,
)
_ORDINAL_DAY_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)")
_USAGE_LIMIT_MARKERS = ("usage limit", "try again at")


class OfficeQAInfraError(RuntimeError):
    """A loop step failed before a complete Eq. 4 val gate could be scored."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def protocol_sha256(path: Path = PROTOCOL_PATH) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"OfficeQA protocol lockfile missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean_accuracy(rows: list[dict[str, Any]]) -> float:
    if not rows:
        raise ValueError("cannot score an empty OfficeQA split")
    infra = [
        str(row.get("uid") or row.get("case_id") or "?")
        for row in rows
        if row.get("fail_reason") in _INFRA_FAIL_REASONS
    ]
    if infra:
        reasons = sorted(
            {
                str(row.get("fail_reason"))
                for row in rows
                if row.get("fail_reason") in _INFRA_FAIL_REASONS
            }
        )
        raise OfficeQAInfraError(
            f"{', '.join(reasons)} rows are infra, not wrong answers: "
            + ", ".join(infra)
        )
    return sum(float(row.get("score") or 0.0) for row in rows) / len(rows)


def eq4_accepted(r_cand: float, r_best: float) -> bool:
    """Eq. 4: accept iff candidate strictly beats incumbent. Tie is reject."""
    return r_cand > r_best


def eq4_guard(r_cand: float, r_best: float) -> str:
    if r_cand > r_best:
        return "IMPROVED"
    if r_cand == r_best:
        return "TIE"
    return "WORSE"


def _arm_id(wiki_dir: Path) -> str:
    if wiki_dir.name == "wiki":
        return wiki_dir.parent.name
    return wiki_dir.name


def complete_non_infra_rows(
    path: Path, expected: int
) -> list[dict[str, Any]] | None:
    """Return last-uid-wins rows if the split is complete and has no infra."""
    last = load_jsonl_last_uid_wins(path)
    if len(last) != expected:
        return None
    if any(row.get("fail_reason") in _INFRA_FAIL_REASONS for row in last.values()):
        return None
    return list(last.values())


def maybe_resume_candidate(
    workdir_root: Path, train_outcomes: Path, expected_train: int
) -> tuple[float, str] | None:
    """Reuse candidate-SKILL.md when train is complete so val can resume.

    Crash is not a reject. An incomplete val must not rerun Maintainer or
    Proposer, and must not change r_best.
    """
    rows = complete_non_infra_rows(train_outcomes, expected_train)
    if rows is None:
        return None
    skill_path = workdir_root / "candidate-SKILL.md"
    if not skill_path.is_file():
        return None
    text = skill_path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    return mean_accuracy(rows), text


def load_jsonl_last_uid_wins(path: Path) -> dict[str, dict[str, Any]]:
    last: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return last
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        uid = str(row.get("uid") or row.get("case_id") or "")
        if not uid:
            raise ValueError(f"{path} has a JSONL row with no uid")
        last[uid] = row
    return last


def rewrite_jsonl_last_uid_wins(
    path: Path, *, uid_order: list[str], max_rows: int
) -> list[dict[str, Any]]:
    """Replace a JSONL file with last-uid-wins rows in split order. Cap = split size."""
    if max_rows < 1:
        raise ValueError("max_rows must be >= 1")
    if len(uid_order) > max_rows:
        raise ValueError(
            f"uid_order length {len(uid_order)} exceeds max_rows={max_rows}"
        )
    last = load_jsonl_last_uid_wins(path)
    missing = [uid for uid in uid_order if uid not in last]
    extra = sorted(uid for uid in last if uid not in set(uid_order))
    if missing or extra:
        raise ValueError(
            f"{path} last-uid-wins mismatch: missing={missing} extra={extra}"
        )
    ordered = [last[uid] for uid in uid_order]
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in ordered),
        encoding="utf-8",
    )
    return ordered


def upsert_jsonl(
    path: Path,
    row: dict[str, Any],
    lock: threading.Lock,
    *,
    max_rows: int,
) -> None:
    """Replace the row for this uid; never append a duplicate; never exceed split size."""
    uid = str(row.get("uid") or row.get("case_id") or "")
    if not uid:
        raise ValueError("jsonl row has no uid")
    if max_rows < 1:
        raise ValueError("max_rows must be >= 1")
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        kept: list[dict[str, Any]] = []
        if path.is_file() and path.stat().st_size:
            for existing in path.read_text(encoding="utf-8").splitlines():
                if not existing.strip():
                    continue
                payload = json.loads(existing)
                existing_uid = str(payload.get("uid") or payload.get("case_id") or "")
                if existing_uid != uid:
                    kept.append(payload)
        kept.append(row)
        if len(kept) > max_rows:
            raise ValueError(
                f"{path} would exceed split-size cap {max_rows} (uid={uid})"
            )
        path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in kept),
            encoding="utf-8",
        )


def _parse_try_again(stderr: str) -> datetime | None:
    text = stderr or ""
    dated = _TRY_AGAIN_DATE_RE.search(text)
    if dated:
        stamp = _ORDINAL_DAY_RE.sub(r"\1", dated.group(1).replace(",", "").strip())
        try:
            naive = datetime.strptime(stamp, "%b %d %Y %I:%M %p")
        except ValueError:
            return None
        local = datetime.now().astimezone().tzinfo
        return naive.replace(tzinfo=local)
    match = _TRY_AGAIN_RE.search(text)
    if not match:
        return None
    clock = datetime.strptime(match.group(1).strip().upper(), "%I:%M %p").time()
    now = datetime.now().astimezone()
    target = now.replace(hour=clock.hour, minute=clock.minute, second=0, microsecond=0)
    if target <= now:
        return None
    return target


def retry_wait_seconds(stderr: str, attempt: int, *, base: int = 60, cap: int = 900) -> int:
    target = _parse_try_again(stderr)
    if target is not None:
        wait = int((target - datetime.now().astimezone()).total_seconds())
        if wait > cap:
            raise OfficeQAInfraError(
                f"usage limit retry is {wait}s away ({target.isoformat()}); "
                "not a wrong answer and not an Eq.4 reject"
            )
        return min(max(wait, 5), cap)
    return min(base * (2 ** (attempt - 1)), cap)


def _infra_blob(row: dict[str, Any]) -> str:
    parts = [str(row.get("error") or ""), str(row.get("predicted") or "")]
    workspace = Path(str(row.get("workspace") or ""))
    for rel in (
        "scratch/officeqa-rollout/codex_stderr.txt",
        "scratch/officeqa-rollout/codex_events.jsonl",
    ):
        path = workspace / rel
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8", errors="replace")[-12000:])
    return "\n".join(parts)


def run_split(
    cases: tuple[OfficeQACase, ...],
    *,
    workdir: Path,
    outcomes_path: Path,
    model: str,
    reasoning_effort: str,
    skill_text: str,
    max_workers: int,
    timeout_seconds: int,
    max_exec_attempts: int = 6,
    retry_sleep: Callable[[int, str], float] | None = None,
    rollout_fn: Callable[..., dict[str, Any]] = rollout_case,
) -> list[dict[str, Any]]:
    if not cases:
        raise ValueError("split has no cases")
    if max_exec_attempts < 1:
        raise ValueError("max_exec_attempts must be >= 1")
    outcomes_path.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    results: dict[str, dict[str, Any]] = {}
    max_rows = len(cases)
    existing = load_jsonl_last_uid_wins(outcomes_path)
    pending: list[Any] = []
    for case in cases:
        uid = str(getattr(case, "uid", "") or getattr(case, "case_id", "") or "")
        row = existing.get(uid)
        if row and row.get("fail_reason") not in _INFRA_FAIL_REASONS:
            results[uid] = row
        else:
            pending.append(case)
    if not outcomes_path.is_file():
        outcomes_path.write_text("", encoding="utf-8")
    if results or pending:
        print(
            f"split resume done={len(results)} pending={len(pending)} "
            f"n={len(cases)}",
            flush=True,
        )

    def _sleep(attempt: int, stderr: str) -> None:
        if retry_sleep is not None:
            delay = float(retry_sleep(attempt, stderr))
        else:
            delay = float(retry_wait_seconds(stderr, attempt))
        if delay > 0:
            time.sleep(delay)

    def _one(case: OfficeQACase) -> dict[str, Any]:
        last: dict[str, Any] | None = None
        for attempt in range(1, max_exec_attempts + 1):
            try:
                row = rollout_fn(
                    case,
                    workdir=workdir,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    skill_text=skill_text,
                    timeout_seconds=timeout_seconds,
                )
            except ModelIdentityError as exc:
                print(
                    f"PAUSE ARM {case.uid} model identity: {exc}",
                    flush=True,
                )
                raise
            last = row
            upsert_jsonl(outcomes_path, row, lock, max_rows=max_rows)
            if row.get("fail_reason") not in _INFRA_FAIL_REASONS:
                return row
            stderr = _infra_blob(row)
            if any(marker in stderr.lower() for marker in _USAGE_LIMIT_MARKERS):
                retry_wait_seconds(stderr, attempt)
            if attempt < max_exec_attempts:
                print(
                    f"{case.uid} {row.get('fail_reason')} attempt {attempt}/"
                    f"{max_exec_attempts}; waiting to retry (not scored as wrong)",
                    flush=True,
                )
                _sleep(attempt, stderr)
        assert last is not None
        raise OfficeQAInfraError(
            f"{case.uid} still {last.get('fail_reason')} after "
            f"{max_exec_attempts} attempts; incumbent and r_best unchanged"
        )

    def _record_done(uid: str, row: dict[str, Any]) -> None:
        results[uid] = row
        print(
            f"split progress done={len(results)} target={len(cases)} "
            f"last={uid} fail={row.get('fail_reason') or 'ok'}",
            flush=True,
        )

    if max_workers <= 1:
        for case in pending:
            _record_done(str(case.uid), _one(case))
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_one, case): str(case.uid) for case in pending}
            try:
                for future in as_completed(futures):
                    uid = futures[future]
                    _record_done(uid, future.result())
            except ModelIdentityError:
                for future in futures:
                    future.cancel()
                raise
    ordered = [results[str(case.uid)] for case in cases]
    if len(ordered) != len(cases):
        raise OfficeQAInfraError(
            f"{outcomes_path} completed {len(ordered)}/{len(cases)} cases"
        )
    return ordered


def load_r_best(path: Path) -> float:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing; run with --init-baseline before iterating"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("r_best")
    if not isinstance(value, (int, float)):
        raise ValueError(f"{path} has no numeric r_best (run --init-baseline)")
    return float(value)


def save_r_best(path: Path, value: float, note: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"r_best": value, "updated_at": _now(), "note": note},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_baseline_val(
    *,
    model: str,
    reasoning_effort: str,
    workdir: Path,
    outcomes_path: Path,
    r_best_path: Path,
    csv_path: Path = DEFAULT_CSV_PATH,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    max_workers: int = 4,
    timeout_seconds: int = 1200,
    limit: int | None = None,
) -> dict[str, Any]:
    cases = load_cases(
        "val",
        csv_path=csv_path,
        split_dir=split_dir,
        corpus_dir=corpus_dir,
        limit=limit,
    )
    rows = run_split(
        cases,
        workdir=workdir,
        outcomes_path=outcomes_path,
        model=model,
        reasoning_effort=reasoning_effort,
        skill_text="",
        max_workers=max_workers,
        timeout_seconds=timeout_seconds,
    )
    accuracy = mean_accuracy(rows)
    save_r_best(r_best_path, accuracy, f"S0 no-skill val baseline ({model})")
    return {"n": len(rows), "accuracy": accuracy, "model": model}


def _record_infra(
    *,
    impact_path: Path,
    iteration: int,
    incumbent_sha: str,
    r_best: float,
    train_r: float | None,
    notes: str,
    arm: str,
) -> int:
    descriptive: dict[str, float] = {"r_best": r_best}
    if train_r is not None:
        descriptive["train_R"] = train_r
    append_skill_impact(
        impact_path,
        SkillImpactEntry(
            schema_version="wikiskill.skill_impact.v1",
            iteration=iteration,
            recorded_at=_now(),
            prereg={
                "target_component": "paper_eq4",
                "minimum_effect": 1,
                "protocol_sha256": protocol_sha256(),
                "pair_id": f"officeqa-{arm}-it{iteration}",
            },
            proposal_kind="no_action",
            skill_sha256="",
            incumbent_skill_sha256=incumbent_sha,
            incumbent_descriptive=descriptive,
            gate_verdict="INFRA_FAILURE",
            accepted=False,
            notes=f"arm={arm}; infra_failure; incumbent and r_best unchanged; {notes[:1500]}",
        ),
    )
    print(
        f"it{iteration} INFRA_FAILURE r_best={r_best:.4f} (not a reject): {notes[:300]}",
        flush=True,
    )
    return EXIT_INFRA


def run_iteration(
    *,
    iteration: int,
    model: str,
    reasoning_effort: str,
    optimizer_model: str,
    optimizer_reasoning_effort: str,
    incumbent_skill_path: Path,
    workdir_root: Path,
    wiki_dir: Path,
    r_best_path: Path,
    csv_path: Path = DEFAULT_CSV_PATH,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    max_workers: int = 4,
    timeout_seconds: int = 1200,
    train_limit: int | None = None,
    val_limit: int | None = None,
    reuse_train: Path | None = None,
    rollout_fn: Callable[..., dict[str, Any]] = rollout_case,
) -> int:
    """Return 0 accept/no_action, 1 Eq.4 reject, 2 infra (no gate).

    ``rollout_fn`` selects the evidence mode for every rollout in the
    iteration (train and candidate val alike): the staged default or
    ``retrieval.rollout_retrieval_case``. Mixing modes inside one arm is a
    protocol violation; callers must not swap it between iterations.
    """
    workdir_root.mkdir(parents=True, exist_ok=True)
    r_best = load_r_best(r_best_path)
    incumbent_text = incumbent_skill_path.read_text(encoding="utf-8")
    incumbent_sha = (
        _sha256_text(incumbent_text) if incumbent_text.strip() else hashlib.sha256(b"").hexdigest()
    )
    arm = _arm_id(wiki_dir)
    impact_path = wiki_dir / "skill-impact.md"
    train_r: float | None = None
    train_outcomes = workdir_root / "train.jsonl"
    try:
        if reuse_train is not None:
            train_outcomes = Path(reuse_train)
            last = load_jsonl_last_uid_wins(train_outcomes)
            train_rows = list(last.values())
            if not train_rows:
                raise ValueError(f"reuse-train file is empty: {train_outcomes}")
        else:
            train_cases = load_cases(
                "train",
                csv_path=csv_path,
                split_dir=split_dir,
                corpus_dir=corpus_dir,
                limit=train_limit,
            )
            train_rows = run_split(
                train_cases,
                workdir=workdir_root / "train",
                outcomes_path=train_outcomes,
                model=model,
                reasoning_effort=reasoning_effort,
                skill_text=incumbent_text,
                max_workers=max_workers,
                timeout_seconds=timeout_seconds,
                rollout_fn=rollout_fn,
            )
        train_r = mean_accuracy(train_rows)

        maintainer = build_maintainer(
            model=optimizer_model,
            workdir=workdir_root / "maintainer",
            reasoning_effort=optimizer_reasoning_effort,
        )
        maintainer([train_outcomes], iteration=iteration, wiki_dir=wiki_dir)

        proposer = build_proposer(
            model=optimizer_model,
            workdir=workdir_root / "proposer",
            reasoning_effort=optimizer_reasoning_effort,
        )
        result = proposer(
            incumbent_text,
            [train_outcomes],
            iteration=iteration,
            wiki_dir=wiki_dir,
        )
    except Exception as exc:  # noqa: BLE001 - crash is infra, never Eq.4 reject
        return _record_infra(
            impact_path=impact_path,
            iteration=iteration,
            incumbent_sha=incumbent_sha,
            r_best=r_best,
            train_r=train_r,
            notes=f"{type(exc).__name__}: {exc}",
            arm=arm,
        )

    entry = dict(
        schema_version="wikiskill.skill_impact.v1",
        iteration=iteration,
        recorded_at=_now(),
        prereg={
            "target_component": "paper_eq4",
            "minimum_effect": 1,
            "protocol_sha256": protocol_sha256(),
            "pair_id": f"officeqa-{arm}-it{iteration}",
        },
        incumbent_skill_sha256=incumbent_sha,
        incumbent_descriptive={"r_best": r_best, "train_R": train_r},
    )

    if result.action == "no_action":
        append_skill_impact(
            impact_path,
            SkillImpactEntry(
                **entry,
                proposal_kind="no_action",
                skill_sha256="",
                gate_verdict="NOT_GATED",
                accepted=False,
                notes=f"arm={arm}; no_action; {result.rationale[:300]}",
            ),
        )
        print(
            f"it{iteration} no_action train_R={train_r:.4f} r_best={r_best:.4f}",
            flush=True,
        )
        return EXIT_ACCEPT

    candidate_skill = workdir_root / "candidate-SKILL.md"
    candidate_skill.write_text(result.skill_md, encoding="utf-8")
    try:
        val_cases = load_cases(
            "val",
            csv_path=csv_path,
            split_dir=split_dir,
            corpus_dir=corpus_dir,
            limit=val_limit,
        )
        cand_outcomes = workdir_root / "val-candidate.jsonl"
        cand_rows = run_split(
            val_cases,
            workdir=workdir_root / "val-candidate",
            outcomes_path=cand_outcomes,
            model=model,
            reasoning_effort=reasoning_effort,
            skill_text=result.skill_md,
            max_workers=max_workers,
            timeout_seconds=timeout_seconds,
            rollout_fn=rollout_fn,
        )
        r_cand = mean_accuracy(cand_rows)
    except Exception as exc:  # noqa: BLE001 - incomplete val is not a reject
        return _record_infra(
            impact_path=impact_path,
            iteration=iteration,
            incumbent_sha=incumbent_sha,
            r_best=r_best,
            train_r=train_r,
            notes=f"val incomplete: {type(exc).__name__}: {exc}",
            arm=arm,
        )

    accepted = eq4_accepted(r_cand, r_best)
    guard = eq4_guard(r_cand, r_best)
    print(
        f"it{iteration} train_R={train_r:.4f} r_cand={r_cand:.4f} "
        f"r_best={r_best:.4f} -> {'ACCEPT' if accepted else 'REJECT'} ({guard})",
        flush=True,
    )
    if accepted:
        promoted = wiki_dir / f"SKILL-it{iteration}.md"
        promoted.write_text(result.skill_md, encoding="utf-8")
        save_r_best(
            r_best_path, r_cand, f"iteration {iteration} accepted, skill promoted"
        )
    append_skill_impact(
        impact_path,
        SkillImpactEntry(
            **entry,
            proposal_kind="skill",
            skill_sha256=_sha256_text(result.skill_md),
            purpose_summary=result.purpose.summary,
            motivated_by_patterns=list(result.purpose.motivated_by_patterns),
            unified_diff=result.diff,
            candidate_descriptive={"accuracy": r_cand},
            gate_verdict="ACCEPT" if accepted else "REJECT",
            hard_guard_summary=guard,
            notes=f"arm={arm}; {result.rationale[:300]}",
            accepted=accepted,
        ),
    )
    return EXIT_ACCEPT if accepted else EXIT_REJECT
