"""ALFWorld act.sh replay-from-history stepper."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from wikiskill.alfworld.rollout import (
    slug_for,
    stage_workspace,
)
from wikiskill.benchmarks.alfworld import AlfWorldCase, score_won

REPO = Path(__file__).resolve().parents[1]
SPLIT = REPO / "evaluation" / "benchmarks" / "alfworld" / "id_split" / "val.json"
ALF_PYTHON = Path(__import__("os").environ.get("WIKISKILL_TEST_DATA", "/nonexistent-wikiskill-test-data")) / "alfworld" / ".venv" / "bin" / "python"


def _first_val_case() -> AlfWorldCase:
    items = json.loads(SPLIT.read_text(encoding="utf-8"))
    uid = items[0]["uid"]
    return AlfWorldCase(uid=uid, game_path=Path(uid), split="val")


@pytest.mark.skipif(not ALF_PYTHON.is_file(), reason="ALFWorld venv not installed")
@pytest.mark.skipif(not SPLIT.is_file(), reason="ALFWorld split not pinned")
def test_act_sh_reset_and_step(tmp_path: Path) -> None:
    case = _first_val_case()
    assert case.game_path.is_file()
    workspace = tmp_path / slug_for(case)
    stage_workspace(case, workspace)
    env = dict(os.environ)
    env["ALFWORLD_PYTHON"] = str(ALF_PYTHON)
    reset = subprocess.run(
        [str(workspace / "act.sh")],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert reset.returncode == 0, reset.stderr
    assert "won=false" in reset.stdout
    status = json.loads((workspace / "status.json").read_text())
    assert score_won(status) == 0.0
    assert status["admissible_actions"]
    action = status["admissible_actions"][0]
    step = subprocess.run(
        [str(workspace / "act.sh"), action],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert step.returncode == 0, step.stderr
    again = json.loads((workspace / "status.json").read_text())
    assert again["step"] == 1
    history = [
        json.loads(line)
        for line in (workspace / "history.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert history == [{"action": action}]
    mode = (workspace / "act.sh").stat().st_mode
    assert mode & stat.S_IXUSR
