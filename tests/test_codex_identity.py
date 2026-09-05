"""Codex model-identity assertion: gpt-reserve voids the rollout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wikiskill.codex_identity import (
    ModelIdentityError,
    assert_requested_model,
    extract_reported_model,
    extract_thread_id,
    model_from_session_file,
)


def test_banner_model_line() -> None:
    reported = extract_reported_model(stdout="workdir: x\nmodel: gpt-5.6-sol\nprovider: custom\n")
    assert reported == "gpt-5.6-sol"
    assert_requested_model("gpt-5.6-sol", reported)


def test_gpt_reserve_in_events_is_reserve() -> None:
    reported = extract_reported_model(events_text='{"type":"error","message":"gpt-reserve routed"}')
    assert reported == "gpt-reserve"
    with pytest.raises(ModelIdentityError, match="gpt-reserve"):
        assert_requested_model("gpt-5.6-luna", reported)


def test_mismatch_pauses_arm() -> None:
    with pytest.raises(ModelIdentityError, match="pause this arm"):
        assert_requested_model("gpt-5.5", "gpt-5.6-luna")


def test_missing_echo_fails_closed() -> None:
    with pytest.raises(ModelIdentityError, match="missing Codex model echo"):
        assert_requested_model("gpt-5.6-sol", "")


def test_thread_id_and_session_turn_context(tmp_path: Path) -> None:
    events = json.dumps({"type": "thread.started", "thread_id": "01abc"}) + "\n"
    assert extract_thread_id(events) == "01abc"
    session = tmp_path / "rollout-01abc.jsonl"
    session.write_text(
        json.dumps({"type": "session_meta", "payload": {"id": "01abc"}})
        + "\n"
        + json.dumps(
            {
                "type": "turn_context",
                "payload": {"model": "gpt-5.5", "cwd": "/tmp"},
            }
        )
        + "\n"
    )
    assert model_from_session_file(session) == "gpt-5.5"
    reported = extract_reported_model(session_path=session)
    assert reported == "gpt-5.5"
    assert_requested_model("gpt-5.5", reported)
