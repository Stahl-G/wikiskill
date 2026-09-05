"""Spreadsheet scoring must use openpyxl and never treat scorer crashes as 0."""

from __future__ import annotations

from pathlib import Path

import pytest

from wikiskill.officeqa.loop import (
    OfficeQAInfraError,
    mean_accuracy,
)


def test_mean_accuracy_treats_score_failed_as_infra() -> None:
    with pytest.raises(OfficeQAInfraError, match="score_failed"):
        mean_accuracy(
            [{"uid": "47933", "score": 0.0, "fail_reason": "score_failed"}]
        )


def test_run_split_resumes_completed_rows(tmp_path: Path) -> None:
    import json
    from types import SimpleNamespace

    from wikiskill.officeqa.loop import run_split

    outcomes = tmp_path / "out.jsonl"
    outcomes.write_text(
        json.dumps({"uid": "a", "score": 1.0, "fail_reason": ""}) + "\n",
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_rollout(case, **_kwargs):
        calls.append(str(case.uid))
        return {"uid": str(case.uid), "score": 1.0, "fail_reason": ""}

    rows = run_split(
        (SimpleNamespace(uid="a"), SimpleNamespace(uid="b")),
        workdir=tmp_path,
        outcomes_path=outcomes,
        model="gpt-5.6-sol",
        reasoning_effort="medium",
        skill_text="",
        max_workers=1,
        timeout_seconds=1,
        rollout_fn=fake_rollout,
    )
    assert calls == ["b"]
    assert [row["uid"] for row in rows] == ["a", "b"]


def test_run_split_retries_score_failed_last_wins(tmp_path: Path) -> None:
    import json
    from types import SimpleNamespace

    from wikiskill.officeqa.loop import run_split

    outcomes = tmp_path / "out.jsonl"
    outcomes.write_text(
        json.dumps({"uid": "395-36", "score": 0.0, "fail_reason": "score_failed"})
        + "\n"
        + json.dumps({"uid": "kept", "score": 1.0, "fail_reason": ""})
        + "\n",
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_rollout(case, **_kwargs):
        calls.append(str(case.uid))
        return {"uid": str(case.uid), "score": 0.0, "fail_reason": "wrong_answer"}

    rows = run_split(
        (
            SimpleNamespace(uid="395-36"),
            SimpleNamespace(uid="kept"),
        ),
        workdir=tmp_path,
        outcomes_path=outcomes,
        model="gpt-5.5",
        reasoning_effort="medium",
        skill_text="",
        max_workers=1,
        timeout_seconds=1,
        rollout_fn=fake_rollout,
    )
    assert calls == ["395-36"]
    by_uid = {row["uid"]: row for row in rows}
    assert by_uid["kept"]["fail_reason"] == ""
    assert by_uid["395-36"]["fail_reason"] == "wrong_answer"


def test_score_workbook_matches_cached_values(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    from wikiskill.benchmarks.spreadsheet import score_workbook

    gold = tmp_path / "gold.xlsx"
    out = tmp_path / "out.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["A1"] = 2
    ws["A2"] = 4
    wb.save(gold)
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.title = "Sheet1"
    ws2["A1"] = 2
    ws2["A2"] = 4
    wb2.save(out)
    score, matched, total = score_workbook(out, gold, "Sheet1", "A1:A2")
    assert (score, matched, total) == (1.0, 2, 2)


def test_score_workbook_missing_agent_sheet_is_zero(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    from wikiskill.benchmarks.spreadsheet import score_workbook

    gold = tmp_path / "gold.xlsx"
    out = tmp_path / "out.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MyResult"
    ws["A1"] = 1
    ws["A2"] = 2
    wb.save(gold)
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.title = "Other"
    ws2["A1"] = 1
    wb2.save(out)
    score, matched, total = score_workbook(out, gold, "MyResult", "A1:A2")
    assert (score, matched, total) == (0.0, 0, 2)


def test_score_workbook_missing_golden_sheet_raises(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    from wikiskill.benchmarks.spreadsheet import score_workbook

    gold = tmp_path / "gold.xlsx"
    out = tmp_path / "out.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Other"
    wb.save(gold)
    wb2 = openpyxl.Workbook()
    wb2.active.title = "MyResult"
    wb2.save(out)
    with pytest.raises(KeyError, match="golden missing sheet"):
        score_workbook(out, gold, "MyResult", "A1:A2")


def test_hygiene_cleared_writes_ledger_note(tmp_path: Path) -> None:
    import json

    from wikiskill.spreadsheet.loop import (
        hygiene_ledger_note,
        mark_hygiene_cleared,
    )

    payload = {
        "status": "RETRY_STARTED",
        "planned_ledger_note": "32 条 usage-limit train 记录经重试清除后测量",
    }
    path = tmp_path / "usage-limit-hygiene.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    mark_hygiene_cleared(tmp_path)
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated["status"] == "CLEARED"
    assert updated["cleared_at"]
    assert hygiene_ledger_note(tmp_path).startswith("32 条")
    assert "32 条 usage-limit" in (tmp_path / "notes.md").read_text(encoding="utf-8")
