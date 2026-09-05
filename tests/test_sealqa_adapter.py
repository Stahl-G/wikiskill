"""SealQA adapter: fragment-stripped URLs and <answer> scoring."""

from __future__ import annotations

from pathlib import Path

import pytest

from wikiskill.benchmarks.sealqa import (
    has_answer_tag,
    load_cases,
    score_answer,
    strip_url_fragment,
)
from wikiskill.sealqa.rollout import _stage_workspace

DATA = Path(__import__("os").environ.get("WIKISKILL_TEST_DATA", "/nonexistent-wikiskill-test-data")) / "sealqa" / "seal-0.parquet"


def test_strip_url_fragment_drops_text_fragment() -> None:
    url = "https://en.wikipedia.org/wiki/X#:~:text=Serban%20Ghenea"
    assert strip_url_fragment(url) == "https://en.wikipedia.org/wiki/X"


def test_score_answer_reads_answer_tag() -> None:
    assert score_answer("Serban Ghenea", "trace\n<answer>Serban Ghenea</answer>") == 1.0
    assert score_answer("Serban Ghenea", "<answer>the Serban Ghenea</answer>") == 1.0
    assert score_answer("Serban Ghenea", "Serban Ghenea") == 0.0
    assert has_answer_tag("<answer>x</answer>")
    assert not has_answer_tag("x")


@pytest.mark.skipif(not DATA.is_file(), reason="seal-0.parquet missing")
def test_load_cases_strips_url_fragments() -> None:
    cases = load_cases(DATA)
    assert len(cases) == 111
    assert cases[0].uid == "seal0-0"
    assert cases[0].urls
    assert all("#" not in url for case in cases for url in case.urls)


@pytest.mark.skipif(not DATA.is_file(), reason="seal-0.parquet missing")
def test_stage_workspace_writes_search_script(tmp_path: Path) -> None:
    case = load_cases(DATA)[0]
    workspace = tmp_path / case.uid
    _stage_workspace(case, workspace)
    urls = (workspace / "urls.txt").read_text(encoding="utf-8")
    assert case.urls[0] in urls
    assert "#" not in urls
    script = workspace / "web_search.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111
