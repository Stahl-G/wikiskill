"""ALFWorld adapter (paper split 39/18/134 over valid_seen/valid_unseen).

Environment: ``alfworld==0.4.2`` in ``a caller-provided ALFWORLD_PYTHON environment``
(Python 3.12; needs cmake + a ``python`` shim on PATH during install). Game
data lives under ``~/.cache/alfworld/json_2.1.1`` — 140 valid_seen and 134
valid_unseen games. Test = all 134 valid_unseen (matches the paper's count);
train/val = deterministic 39/18 sample of valid_seen.

The paper runs the inference agent ReAct-style, one action per turn. Under
``codex exec`` the adapted contract is one subprocess per episode: the agent
steps the simulator through a workspace-local ``act.sh`` tool (load episode
state, apply action, print next observation and admissible actions); success
is the environment's goal predicate. The episode driver itself is left to the
runner; this module pins the split, the prompt, and the scoring flag.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from pathlib import Path

SYSTEM_PROMPT = """You are an expert agent operating in the ALFRED Embodied Environment. Your task is to:

{task_description}

{skill_section}

Prior to this step, you have already taken {step_count} step(s). Below are the most recent {history_length} observations and the corresponding actions you took:

{action_history}

You are now at step {current_step} and your current observation is:

{current_observation}

Your admissible actions of the current situation are: [{admissible_actions}].

Now it's your turn to take an action. You should first reason step-by-step about the current situation. This reasoning process MUST be enclosed within <think> </think> tags. Once you've finished your reasoning, you should choose an admissible action for current step and present it within <action> </action> tags."""

DEFAULT_DATA_ROOT = Path.home() / ".cache" / "alfworld" / "json_2.1.1"


@dataclass(frozen=True)
class AlfWorldCase:
    uid: str
    game_path: Path
    split: str


def discover_games(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    for split in ("valid_seen", "valid_unseen"):
        games = sorted((data_root / split).rglob("*.tw-pddl"))
        if not games:
            raise FileNotFoundError(
                f"no games under {data_root / split}; run alfworld-download --extra"
            )
        out[split] = games
    return out


def split_cases(
    games: dict[str, list[Path]], seed: int = 20260904
) -> dict[str, list[str]]:
    """Test = all 134 valid_unseen; train/val = seeded 39/18 of valid_seen."""
    rng = random.Random(seed)
    seen = sorted(str(p) for p in games["valid_seen"])
    rng.shuffle(seen)
    return {
        "train": seen[:39],
        "val": seen[39:57],
        "test": sorted(str(p) for p in games["valid_unseen"]),
    }


_ACTION_RE = re.compile(r"<action>\s*(.*?)\s*</action>", re.DOTALL)


def extract_action(model_output: str) -> str | None:
    """One admissible action per turn, inside <action> tags."""
    match = _ACTION_RE.search(model_output or "")
    return match.group(1).strip() if match else None


def score_won(info_or_status: dict) -> float:
    """Environment goal predicate: won == True scores 1."""
    return 1.0 if info_or_status.get("won") else 0.0
