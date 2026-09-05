"""LiveMathematicianBench adapter (paper split 35/18/124, single-step, no tools).

Data: monthly ``qa_YYYYMM_final.json`` files, each a list of items whose
``mcq`` dict carries ``question``, ``choices`` (labelled), and
``correct_choice`` (``{"label": ..., "text": ...}``). Scoring is exact match
on the choice label inside ``<answer>`` tags, per the paper's Appendix E prompt.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

SYSTEM_PROMPT = """You are an expert mathematical reasoning agent solving multiple-choice questions.

{skill_section}

## Task Format

You will receive one mathematics multiple-choice question and its answer choices. Reason carefully about quantifiers, hypotheses, extremal wording, and exact equality conditions.

## Answer Format

Think step by step, then provide your final answer inside <answer>...</answer> tags. Inside the tags, output only the single choice label, such as A or C. Example: <answer> B </answer>"""


@dataclass(frozen=True)
class LiveMathCase:
    uid: str
    question: str
    choices: list[dict]
    correct_label: str

    def user_prompt(self) -> str:
        lines = [self.question, ""]
        for choice in self.choices:
            lines.append(f"{choice['label']}. {choice['text']}")
        return "\n".join(lines)


def load_month_files(paths: list[Path]) -> list[LiveMathCase]:
    """Build cases with the correct choice ON the rendered option list.

    In the raw data ``mcq['choices']`` holds ONLY the distractors (labels
    B/C/D/E); the correct option lives in ``mcq['correct_choice']`` with label
    A. Rendering only ``choices`` would omit the answer from the paper the
    model sees. We merge correct+distractors, shuffle deterministically per
    uid (so the answer is not always in a fixed position), and relabel A-E
    positionally with the gold label following the correct option.
    """
    cases: list[LiveMathCase] = []
    for path in paths:
        for item in json.loads(path.read_text()):
            mcq = item["mcq"]
            options = [dict(mcq["correct_choice"])] + [dict(c) for c in mcq["choices"]]
            rng = random.Random(f"livemath-{item['month']}-{item['no']}")
            rng.shuffle(options)
            correct_text = mcq["correct_choice"]["text"]
            rendered: list[dict] = []
            correct_label = None
            for index, option in enumerate(options):
                label = chr(ord("A") + index)
                rendered.append({"label": label, "text": option["text"]})
                if option["text"] == correct_text:
                    correct_label = label
            if correct_label is None:
                raise ValueError(
                    f"correct option missing after render for {item['month']}-{item['no']}"
                )
            cases.append(
                LiveMathCase(
                    uid=f"{item['month']}-{item['no']}",
                    question=mcq["question"],
                    choices=rendered,
                    correct_label=correct_label,
                )
            )
    return cases


def split_cases(
    cases: list[LiveMathCase], seed: int = 20260904
) -> dict[str, list[str]]:
    """Deterministic uid split 35/18/124 over the loaded pool, pinned by caller."""
    rng = random.Random(seed)
    pool = sorted(c.uid for c in cases)
    rng.shuffle(pool)
    return {"train": pool[:35], "val": pool[35:53], "test": pool[53:177]}


_ANSWER_RE = re.compile(r"<answer>\s*([A-E])\s*</answer>", re.IGNORECASE)


def has_answer_tag(model_output: str) -> bool:
    return _ANSWER_RE.search(model_output or "") is not None


def score_answer(ground_truth_label: str, model_output: str) -> float:
    match = _ANSWER_RE.search(model_output or "")
    if match is None:
        return 0.0
    return 1.0 if match.group(1).upper() == ground_truth_label.upper() else 0.0
