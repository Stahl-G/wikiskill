"""SealQA adapter (seal-0 = paper's 16/10/85, web_search + read_file tools).

Data: ``seal-0.parquet`` (111 rows) from ``vtllms/sealqa`` with question,
answer, and ``urls``. The ``search_results`` column is a conflict label
(``conflicting`` / ``unhelpful``), not snippet bodies. The paper's agent used
live Google (July 2026). This adapter serves a workspace-local
``./web_search.sh`` that prints this item's URL list with ``#fragment``
identifiers stripped so gold ``:~:text=`` spans never enter the prompt. That
is a documented deviation from live search. Live-search mode can be added
later behind the same tool interface.

Scoring: exact match on the normalized answer (case/whitespace-insensitive),
per the paper prompt's "exact value only" contract.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

SYSTEM_PROMPT = """You are a knowledgeable question-answering assistant with access to web_search and read_file tools.

{skill_section}

## Task

You will receive a factual question. To answer it:
1. You can check the available skills. They contain guidance that can improve your search queries and answer accuracy.
2. You can use ./web_search.sh to list the packaged source URLs for this item. This is not live Google.
3. You can run ./web_search.sh anytime during the process depending on your needs.
4. After gathering enough information, provide your final answer.

## Answer Format

You MUST wrap your final answer in <answer> tags: <answer> ... your final answer (exact value only, no explanation) ... </answer>"""


@dataclass(frozen=True)
class SealQACase:
    uid: str
    question: str
    answer: str
    effective_year: str
    urls: tuple[str, ...]

    def user_prompt(self) -> str:
        return self.question


def strip_url_fragment(url: str) -> str:
    return url.split("#", 1)[0].strip()


def _as_urls(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [value]
    else:
        items = list(value)
    out: list[str] = []
    for item in items:
        cleaned = strip_url_fragment(str(item))
        if cleaned:
            out.append(cleaned)
    return tuple(out)


def load_cases(parquet_path) -> list[SealQACase]:
    import pandas as pd

    df = pd.read_parquet(parquet_path)
    return [
        SealQACase(
            uid=f"seal0-{i}",
            question=str(row["question"]),
            answer=str(row["answer"]),
            effective_year=str(row.get("effective_year", "")),
            urls=_as_urls(row.get("urls")),
        )
        for i, row in df.iterrows()
    ]


def split_cases(
    cases: list[SealQACase], seed: int = 20260904
) -> dict[str, list[str]]:
    """Deterministic split 16/10/85 over seal-0, pinned by caller."""
    rng = random.Random(seed)
    pool = sorted(c.uid for c in cases)
    rng.shuffle(pool)
    return {"train": pool[:16], "val": pool[16:26], "test": pool[26:111]}


_ANSWER_RE = re.compile(r"<answer>\s*(.*?)\s*</answer>", re.DOTALL)


def _normalize(text: str) -> str:
    lowered = text.strip().lower()
    for article in ("the ", "a ", "an "):
        if lowered.startswith(article):
            lowered = lowered[len(article) :].strip()
            break
    return re.sub(r"\s+", " ", lowered)


def has_answer_tag(model_output: str) -> bool:
    return _ANSWER_RE.search(model_output or "") is not None


def score_answer(ground_truth: str, model_output: str) -> float:
    match = _ANSWER_RE.search(model_output or "")
    if match is None:
        return 0.0
    return 1.0 if _normalize(match.group(1)) == _normalize(ground_truth) else 0.0
