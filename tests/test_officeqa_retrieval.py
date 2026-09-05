"""Retrieval-mode OfficeQA must not leak staged file lists."""

from __future__ import annotations

from pathlib import Path

import pytest

from wikiskill.officeqa.dataset import OfficeQACase
from wikiskill.officeqa.loop import _infra_blob
from wikiskill.officeqa.retrieval import (
    EVIDENCE_MODE,
    build_retrieval_prompt,
    stage_retrieval_workspace,
)


def _case() -> OfficeQACase:
    return OfficeQACase(
        uid="UID0001",
        split="val",
        difficulty="easy",
        question="What is the 1939 January receipt total?",
        answer="1",
        source_files=("treasury_bulletin_1939_01.txt",),
        source_docs=("doc-a",),
        corpus_paths=(Path("/tmp/treasury_bulletin_1939_01.txt"),),
        missing_files=(),
    )


def test_retrieval_prompt_omits_source_files_and_docs() -> None:
    prompt = build_retrieval_prompt(_case(), "")
    assert "treasury_bulletin_1939_01.txt" not in prompt
    assert "docs/" not in prompt
    assert "<FINAL_ANSWER>" in prompt
    assert "corpus/" in prompt


def test_retrieval_prompt_rejects_skill_that_names_gold_file() -> None:
    with pytest.raises(Exception, match="must not name source files"):
        build_retrieval_prompt(
            _case(), "Read treasury_bulletin_1939_01.txt first.\n"
        )


def test_stage_retrieval_workspace_symlinks_corpus(tmp_path: Path) -> None:
    corpus = tmp_path / "transformed"
    corpus.mkdir()
    (corpus / "a.txt").write_text("x\n", encoding="utf-8")
    workspace = tmp_path / "UID0001"
    stage_retrieval_workspace(workspace, corpus)
    link = workspace / "corpus"
    assert link.is_symlink()
    assert (link / "a.txt").is_file()
    assert not (workspace / "docs").exists()


def test_infra_blob_sees_usage_limit_in_predicted() -> None:
    blob = _infra_blob(
        {
            "error": "",
            "predicted": (
                '{"type":"error","message":"You\'ve hit your usage limit. '
                'try again at Sep 11th, 2026 9:58 PM."}'
            ),
            "workspace": "/no/such/workspace",
        }
    )
    assert "usage limit" in blob.lower()
    assert EVIDENCE_MODE == "retrieval"
