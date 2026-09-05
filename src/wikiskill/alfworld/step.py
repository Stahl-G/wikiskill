"""Replay-from-history ALFWorld stepper used by workspace-local act.sh."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ALFWORLD_PYTHON_HINT = Path(sys.executable)


def _load_env(game_path: Path, max_steps: int = 50):
    import textworld
    import textworld.gym
    from alfworld.agents.environment.alfred_tw_env import AlfredDemangler, AlfredInfos

    request_infos = textworld.EnvInfos(
        won=True, admissible_commands=True, extras=["gamefile"]
    )
    env_id = textworld.gym.register_games(
        [str(game_path)],
        request_infos,
        max_episode_steps=max_steps,
        wrappers=[AlfredDemangler(shuffle=False), AlfredInfos],
    )
    return textworld.gym.make(env_id)


def _payload(obs: str, info: dict, *, reward: int = 0, done: bool = False, step: int = 0) -> dict:
    admissible = info.get("admissible_commands") or []
    won = bool(info.get("won"))
    return {
        "observation": obs,
        "admissible_actions": admissible,
        "won": won,
        "reward": reward,
        "done": bool(done) or won,
        "step": step,
    }


def _print_payload(payload: dict) -> None:
    won = "true" if payload["won"] else "false"
    done = "true" if payload["done"] else "false"
    actions = ", ".join(payload["admissible_actions"])
    text = (
        f"step={payload['step']} won={won} done={done}\n"
        f"{payload['observation'].rstrip()}\n\n"
        f"admissible: [{actions}]\n"
    )
    sys.stdout.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--action")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--max-steps", type=int, default=50)
    args = parser.parse_args()
    root = args.root
    game_path = Path((root / "game.path").read_text(encoding="utf-8").strip())
    history_path = root / "history.jsonl"
    status_path = root / "status.json"
    obs_path = root / "observation.txt"

    if args.reset or not history_path.is_file():
        history: list[str] = []
    else:
        history = [
            json.loads(line)["action"]
            for line in history_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if args.action and not args.reset:
        history = history + [args.action]

    env = _load_env(game_path, max_steps=args.max_steps)
    obs, info = env.reset()
    reward = 0
    done = False
    for index, command in enumerate(history, start=1):
        obs, reward, done, info = env.step(command)
        if done:
            history = history[:index]
            break
    payload = _payload(obs, info, reward=int(reward), done=done, step=len(history))
    history_path.write_text(
        "".join(json.dumps({"action": action}) + "\n" for action in history),
        encoding="utf-8",
    )
    status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    obs_path.write_text(payload["observation"], encoding="utf-8")
    _print_payload(payload)
    return 0


if __name__ == "__main__":
    # Allow `python step.py` from the alfworld venv.
    os.environ.setdefault("ALFWORLD_PYTHON", str(ALFWORLD_PYTHON_HINT))
    raise SystemExit(main())
