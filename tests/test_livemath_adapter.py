"""LiveMath adapter: correct option must appear on the rendered choice list."""

from __future__ import annotations

from pathlib import Path

from wikiskill.benchmarks.livemath import (
    load_month_files,
    score_answer,
)

FIXTURE = Path(__file__).parent / "fixtures" / "livemath" / "qa_tiny.json"


def test_load_month_files_merges_correct_choice_onto_the_list() -> None:
    cases = load_month_files([FIXTURE])
    assert len(cases) == 1
    case = cases[0]
    assert case.uid == "202604-1"
    assert len(case.choices) == 5
    texts = [choice["text"] for choice in case.choices]
    assert "4" in texts
    gold = next(choice for choice in case.choices if choice["label"] == case.correct_label)
    assert gold["text"] == "4"
    prompt = case.user_prompt()
    assert "4" in prompt
    assert "What is 2+2?" in prompt


def test_score_answer_reads_answer_tag() -> None:
    assert score_answer("B", "reason\n<answer>B</answer>") == 1.0
    assert score_answer("B", "<answer> C </answer>") == 0.0
    assert score_answer("B", "the answer is B") == 0.0
