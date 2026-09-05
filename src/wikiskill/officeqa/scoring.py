"""Score OfficeQA rollouts with the vendored Databricks reward function."""

from __future__ import annotations

import re

from wikiskill.officeqa.reward import (
    extract_final_answer_from_xml,
    score_answer,
)

_FINAL_ANSWER_TAG_RE = re.compile(
    r"<FINAL_ANSWER>.*?</FINAL_ANSWER>",
    re.DOTALL | re.IGNORECASE,
)


def has_final_answer_tag(text: str) -> bool:
    return bool(_FINAL_ANSWER_TAG_RE.search(text or ""))


def score_stdout(
    ground_truth: str, stdout: str, *, tolerance: float = 0.0
) -> tuple[float, str, bool]:
    """Return ``(score, predicted, tagged)``.

    ``score`` is the official ``score_answer`` result (0.0 or 1.0) with
    ``tolerance=0.0``.  ``predicted`` is the extracted ``<FINAL_ANSWER>``
    span when the tag is present, else ``""`` — an untagged transcript
    is not treated as a candidate answer.
    """
    tagged = has_final_answer_tag(stdout)
    predicted, _ = extract_final_answer_from_xml(stdout)
    if not tagged:
        predicted = ""
    score = float(score_answer(ground_truth, stdout, tolerance=tolerance))
    return score, predicted, tagged
