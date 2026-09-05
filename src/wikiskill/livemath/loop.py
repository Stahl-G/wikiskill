"""LiveMath Eq. 4 loop: train → maintainer → proposer → val accept/rollback."""

from __future__ import annotations

import json
import shutil
from functools import partial
from pathlib import Path
from typing import Any

from wikiskill.benchmarks.livemath import (
    LiveMathCase,
    load_month_files,
)
from wikiskill.livemath.rollout import rollout_case
from wikiskill.officeqa.loop import (
    EXIT_ACCEPT,
    EXIT_INFRA,
    EXIT_REJECT,
    _now,
    _sha256_text,
    eq4_accepted,
    eq4_guard,
    load_jsonl_last_uid_wins,
    load_r_best,
    maybe_resume_candidate,
    mean_accuracy,
    protocol_sha256,
    run_split,
    save_r_best,
)
from wikiskill.officeqa.wiki_agents import (
    build_maintainer,
    build_proposer,
)
from wikiskill.wiki import SkillImpactEntry, append_skill_impact

from wikiskill.settings import RESOURCES, DATA_ROOT
PROTOCOL_PATH = RESOURCES / "livemath" / "protocol.json"
DATA = DATA_ROOT / "livemath"
SPLIT_DIR = RESOURCES / "livemath" / "id_split-v2"
WIKI_TEMPLATE = RESOURCES / "livemath" / "wiki"
PUBLIC_IMPACT = Path("runs") / "skill-impact.md"


def load_split_cases(split: str, limit: int | None = None) -> tuple[LiveMathCase, ...]:
    files = sorted(DATA.glob("qa_*_final.json"))
    by_uid = {case.uid: case for case in load_month_files(files)}
    items = json.loads((SPLIT_DIR / f"{split}.json").read_text(encoding="utf-8"))
    uids = [item["uid"] for item in items]
    if limit is not None:
        uids = uids[:limit]
    missing = [uid for uid in uids if uid not in by_uid]
    if missing:
        raise ValueError(f"LiveMath split uids missing from pool: {missing[:5]}")
    return tuple(by_uid[uid] for uid in uids)


def seed_wiki(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    for name in ("index.md", "logs.md", "SKILL-s0.md"):
        dest = wiki_dir / name
        if not dest.is_file():
            shutil.copy2(WIKI_TEMPLATE / name, dest)
    prompts = wiki_dir / "prompts"
    if not prompts.is_dir():
        shutil.copytree(WIKI_TEMPLATE / "prompts", prompts)
    patterns = wiki_dir / "patterns"
    patterns.mkdir(exist_ok=True)
    impact = wiki_dir / "skill-impact.md"
    if not impact.is_file():
        impact.write_text(
            "# Skill Impact Tracker\n\nLiveMath WikiSkill loop. Append-only JSON entries follow.\n",
            encoding="utf-8",
        )


def _arm_id(wiki_dir: Path) -> str:
    if wiki_dir.name == "wiki":
        return wiki_dir.parent.name
    return wiki_dir.name


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
                "protocol_sha256": protocol_sha256(PROTOCOL_PATH),
                "pair_id": f"livemath-{arm}-it{iteration}",
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
    max_workers: int = 4,
    timeout_seconds: int = 600,
    train_limit: int | None = None,
    val_limit: int | None = None,
) -> int:
    """Return 0 accept/no_action, 1 Eq.4 reject, 2 infra (no gate)."""
    workdir_root.mkdir(parents=True, exist_ok=True)
    r_best = load_r_best(r_best_path)
    incumbent_text = incumbent_skill_path.read_text(encoding="utf-8")
    incumbent_sha = (
        _sha256_text(incumbent_text) if incumbent_text.strip() else "0" * 64
    )
    arm = _arm_id(wiki_dir)
    impact_path = wiki_dir / "skill-impact.md"
    train_r: float | None = None
    train_outcomes = workdir_root / "train.jsonl"
    result = None
    resumed_skill: str | None = None
    try:
        train_cases = load_split_cases("train", train_limit)
        resumed = maybe_resume_candidate(
            workdir_root, train_outcomes, len(train_cases)
        )
        if resumed is not None:
            train_r, resumed_skill = resumed
            print(
                f"it{iteration} resume candidate-SKILL.md; "
                "skip maintainer/proposer",
                flush=True,
            )
        else:
            train_rows = run_split(
                train_cases,
                workdir=workdir_root / "train",
                outcomes_path=train_outcomes,
                model=model,
                reasoning_effort=reasoning_effort,
                skill_text=incumbent_text,
                max_workers=max_workers,
                timeout_seconds=timeout_seconds,
                rollout_fn=partial(rollout_case, split="train"),
            )
            train_r = mean_accuracy(train_rows)

            maintainer = build_maintainer(
                model=optimizer_model,
                workdir=workdir_root / "maintainer",
                reasoning_effort=optimizer_reasoning_effort,
                answer_tag="<answer>",
                domain="LiveMath",
            )
            maintainer([train_outcomes], iteration=iteration, wiki_dir=wiki_dir)

            proposer = build_proposer(
                model=optimizer_model,
                workdir=workdir_root / "proposer",
                reasoning_effort=optimizer_reasoning_effort,
                answer_tag="<answer>",
                domain="LiveMath",
            )
            result = proposer(
                incumbent_text,
                [train_outcomes],
                iteration=iteration,
                wiki_dir=wiki_dir,
            )
    except Exception as exc:  # noqa: BLE001
        return _record_infra(
            impact_path=impact_path,
            iteration=iteration,
            incumbent_sha=incumbent_sha,
            r_best=r_best,
            train_r=train_r,
            notes=f"{type(exc).__name__}: {exc}",
            arm=arm,
        )

    entry: dict[str, Any] = dict(
        schema_version="wikiskill.skill_impact.v1",
        iteration=iteration,
        recorded_at=_now(),
        prereg={
            "target_component": "paper_eq4",
            "minimum_effect": 1,
            "protocol_sha256": protocol_sha256(PROTOCOL_PATH),
            "pair_id": f"livemath-{arm}-it{iteration}",
        },
        incumbent_skill_sha256=incumbent_sha,
        incumbent_descriptive={"r_best": r_best, "train_R": train_r},
    )

    if resumed_skill is None and result is not None and result.action == "no_action":
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

    if resumed_skill is not None:
        skill_md = resumed_skill
        purpose_summary = "resumed candidate-SKILL.md after incomplete val"
        motivated_by = []
        unified_diff = ""
        rationale = "infra resume: reuse candidate-SKILL.md; optimizer not rerun"
    else:
        assert result is not None
        skill_md = result.skill_md
        purpose_summary = result.purpose.summary
        motivated_by = list(result.purpose.motivated_by_patterns)
        unified_diff = result.diff
        rationale = result.rationale
        (workdir_root / "candidate-SKILL.md").write_text(skill_md, encoding="utf-8")
    try:
        val_cases = load_split_cases("val", val_limit)
        cand_outcomes = workdir_root / "val-candidate.jsonl"
        cand_rows = run_split(
            val_cases,
            workdir=workdir_root / "val-candidate",
            outcomes_path=cand_outcomes,
            model=model,
            reasoning_effort=reasoning_effort,
            skill_text=skill_md,
            max_workers=max_workers,
            timeout_seconds=timeout_seconds,
            rollout_fn=partial(rollout_case, split="val"),
        )
        r_cand = mean_accuracy(cand_rows)
    except Exception as exc:  # noqa: BLE001
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
        promoted.write_text(skill_md, encoding="utf-8")
        save_r_best(
            r_best_path, r_cand, f"iteration {iteration} accepted, skill promoted"
        )
    append_skill_impact(
        impact_path,
        SkillImpactEntry(
            **entry,
            proposal_kind="skill",
            skill_sha256=_sha256_text(skill_md),
            purpose_summary=purpose_summary,
            motivated_by_patterns=motivated_by,
            unified_diff=unified_diff,
            candidate_descriptive={"accuracy": r_cand},
            gate_verdict="ACCEPT" if accepted else "REJECT",
            hard_guard_summary=guard,
            notes=f"arm={arm}; {rationale[:300]}",
            accepted=accepted,
        ),
    )
    return EXIT_ACCEPT if accepted else EXIT_REJECT
