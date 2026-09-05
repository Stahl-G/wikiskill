"""OfficeQA Eq. 4 helpers: jsonl cap, tie reject, infra is not a wrong answer."""

from __future__ import annotations

import json
import threading
from types import SimpleNamespace
from pathlib import Path

import pytest

from wikiskill.officeqa.loop import (
    OfficeQAInfraError,
    eq4_accepted,
    eq4_guard,
    load_jsonl_last_uid_wins,
    maybe_resume_candidate,
    mean_accuracy,
    retry_wait_seconds,
    rewrite_jsonl_last_uid_wins,
    run_split,
    upsert_jsonl,
)
from wikiskill.wiki import SkillImpactEntry


def test_eq4_tie_is_reject() -> None:
    assert eq4_accepted(0.75, 0.75) is False
    assert eq4_guard(0.75, 0.75) == "TIE"
    assert eq4_accepted(0.875, 0.8333333333333334) is True
    assert eq4_accepted(0.7083333333333334, 0.8333333333333334) is False
    assert eq4_guard(0.7083333333333334, 0.8333333333333334) == "WORSE"


def test_mean_accuracy_refuses_exec_failed() -> None:
    rows = [
        {"uid": "UID0001", "score": 1.0, "fail_reason": ""},
        {"uid": "UID0002", "score": 0.0, "fail_reason": "exec_failed"},
    ]
    with pytest.raises(OfficeQAInfraError, match="UID0002"):
        mean_accuracy(rows)


def test_upsert_replaces_uid_and_caps(tmp_path: Path) -> None:
    path = tmp_path / "val.jsonl"
    lock = threading.Lock()
    upsert_jsonl(path, {"uid": "UID0001", "score": 0.0}, lock, max_rows=2)
    upsert_jsonl(path, {"uid": "UID0002", "score": 1.0}, lock, max_rows=2)
    upsert_jsonl(path, {"uid": "UID0001", "score": 1.0}, lock, max_rows=2)
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    by_uid = {row["uid"]: row for row in rows}
    assert by_uid["UID0001"]["score"] == 1.0
    with pytest.raises(ValueError, match="split-size cap"):
        upsert_jsonl(path, {"uid": "UID0003", "score": 0.0}, lock, max_rows=2)


def test_rewrite_jsonl_last_uid_wins_split_order(tmp_path: Path) -> None:
    path = tmp_path / "val-s0.jsonl"
    path.write_text(
        json.dumps({"uid": "UID0001", "score": 0.0})
        + "\n"
        + json.dumps({"uid": "UID0002", "score": 1.0})
        + "\n"
        + json.dumps({"uid": "UID0001", "score": 1.0})
        + "\n"
    )
    ordered = rewrite_jsonl_last_uid_wins(
        path, uid_order=["UID0001", "UID0002"], max_rows=2
    )
    assert [row["uid"] for row in ordered] == ["UID0001", "UID0002"]
    assert ordered[0]["score"] == 1.0
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    assert len(lines) == 2
    assert load_jsonl_last_uid_wins(path)["UID0001"]["score"] == 1.0


def test_run_split_retries_exec_failed_and_does_not_score_it(tmp_path: Path) -> None:
    case = SimpleNamespace(uid="UID0001")
    calls = {"n": 0}

    def fake_rollout(current, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "uid": current.uid,
                "score": 0.0,
                "fail_reason": "exec_failed",
                    "error": "transient sandbox collapse",
                "workspace": str(tmp_path / current.uid),
            }
        return {
            "uid": current.uid,
            "score": 1.0,
            "fail_reason": "",
            "error": "",
            "workspace": str(tmp_path / current.uid),
        }

    rows = run_split(
        (case,),  # type: ignore[arg-type]
        workdir=tmp_path / "wd",
        outcomes_path=tmp_path / "out.jsonl",
        model="gpt-5.6-luna",
        reasoning_effort="medium",
        skill_text="",
        max_workers=1,
        timeout_seconds=5,
        max_exec_attempts=3,
        retry_sleep=lambda _attempt, _stderr: 0,
        rollout_fn=fake_rollout,
    )
    assert calls["n"] == 2
    assert rows[0]["score"] == 1.0
    lines = [line for line in (tmp_path / "out.jsonl").read_text().splitlines() if line.strip()]
    assert len(lines) == 1


def test_far_usage_limit_is_infra_not_a_reject() -> None:
    msg = (
        "You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage "
        "to purchase more credits or try again at Sep 10th, 2099 11:05 AM."
    )
    with pytest.raises(OfficeQAInfraError, match="usage limit retry"):
        retry_wait_seconds(msg, 1)


def test_infra_failure_is_a_valid_skill_impact_verdict() -> None:
    entry = SkillImpactEntry(
        schema_version="wikiskill.skill_impact.v1",
        iteration=4,
        recorded_at="2026-09-04T14:00:00Z",
        prereg={
            "target_component": "paper_eq4",
            "minimum_effect": 1,
            "protocol_sha256": "a" * 64,
            "pair_id": "officeqa-terra-it4",
        },
        proposal_kind="no_action",
        incumbent_skill_sha256="0" * 64,
        incumbent_descriptive={"r_best": 0.875},
        gate_verdict="INFRA_FAILURE",
        accepted=False,
        notes="arm=terra; infra_failure; incumbent and r_best unchanged",
    )
    assert entry.accepted is False
    assert entry.gate_verdict == "INFRA_FAILURE"


def test_maybe_resume_candidate_requires_complete_train_and_skill(tmp_path: Path) -> None:
    train = tmp_path / "train.jsonl"
    train.write_text(
        json.dumps({"uid": "a", "score": 1.0, "fail_reason": ""}) + "\n"
        + json.dumps({"uid": "b", "score": 0.0, "fail_reason": "wrong_answer"})
        + "\n",
        encoding="utf-8",
    )
    assert maybe_resume_candidate(tmp_path, train, 2) is None
    (tmp_path / "candidate-SKILL.md").write_text("# skill\n", encoding="utf-8")
    resumed = maybe_resume_candidate(tmp_path, train, 2)
    assert resumed is not None
    train_r, skill = resumed
    assert train_r == 0.5
    assert skill.startswith("# skill")
    train.write_text(
        json.dumps({"uid": "a", "score": 1.0, "fail_reason": ""}) + "\n"
        + json.dumps({"uid": "b", "score": 0.0, "fail_reason": "score_failed"})
        + "\n",
        encoding="utf-8",
    )
    assert maybe_resume_candidate(tmp_path, train, 2) is None
