"""OfficeQA scorer: official FINAL_ANSWER tag, paper <answer> tag scores 0."""

from __future__ import annotations

import json

from wikiskill.officeqa.scoring import (
    has_final_answer_tag,
    score_stdout,
)


def test_official_wrapper_scores_one() -> None:
    score, predicted, tagged = score_stdout(
        "2,602", "working\n<FINAL_ANSWER>2,602</FINAL_ANSWER>\n"
    )
    assert tagged is True
    assert predicted == "2,602"
    assert score == 1.0


def test_paper_answer_tag_scores_zero() -> None:
    score, predicted, tagged = score_stdout(
        "2,602", "working\n<answer>2,602</answer>\n"
    )
    assert tagged is False
    assert predicted == ""
    assert score == 0.0


def test_wrong_number_scores_zero() -> None:
    score, predicted, tagged = score_stdout(
        "2,602", "<FINAL_ANSWER>99</FINAL_ANSWER>"
    )
    assert tagged is True
    assert predicted == "99"
    assert score == 0.0


def test_untagged_single_line_can_match_official_scorer() -> None:
    """No wrapper: the vendored scorer falls back to the full text."""
    score, predicted, tagged = score_stdout(
        "2,602", "The total is 2,602 million."
    )
    assert tagged is False
    assert predicted == ""
    assert score == 1.0


def test_untagged_multiline_trace_scores_zero() -> None:
    score, _, tagged = score_stdout(
        "2,602",
        "I searched the bulletin.\nThe total is 2,602 million.\nDone.",
    )
    assert tagged is False
    assert score == 0.0


def test_has_final_answer_tag_is_case_insensitive() -> None:
    assert has_final_answer_tag("<final_answer>1</final_answer>") is True
    assert has_final_answer_tag("<ANSWER>1</ANSWER>") is False


def test_compact_event_log_drops_file_dumps() -> None:
    from wikiskill.officeqa.wiki_agents import compact_event_log

    huge = "CELL|" * 5000
    event = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "rg -n defense docs/",
                "aggregated_output": huge,
                "exit_code": 0,
            },
        }
    )
    compact = compact_event_log(event)
    assert "rg -n defense docs/" in compact
    assert huge not in compact
    assert len(compact) < 500
