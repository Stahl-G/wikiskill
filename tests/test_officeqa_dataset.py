"""OfficeQA dataset join, multiline source_files, and missing-file fail-closed."""

from __future__ import annotations

from pathlib import Path

import pytest

from wikiskill.officeqa.dataset import (
    DEFAULT_CSV_PATH,
    OfficeQADatasetError,
    load_cases,
    missing_source_files,
    parse_multiline_field,
)
from wikiskill.officeqa.rollout import build_prompt

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "officeqa"


def _paths() -> dict[str, Path]:
    return {
        "csv": FIXTURE_ROOT / "officeqa_mini.csv",
        "split_dir": FIXTURE_ROOT / "id_split",
        "corpus": FIXTURE_ROOT / "corpus",
    }


def test_parse_multiline_field_normalizes_crlf() -> None:
    assert parse_multiline_field("a.txt\r\nb.txt\r\n") == ("a.txt", "b.txt")
    assert parse_multiline_field("a.txt") == ("a.txt",)
    assert parse_multiline_field("") == ()


def test_train_join_resolves_corpus_files() -> None:
    paths = _paths()
    cases = load_cases(
        "train",
        csv_path=paths["csv"],
        split_dir=paths["split_dir"],
        corpus_dir=paths["corpus"],
    )
    assert [case.uid for case in cases] == ["UIDT1", "UIDT2"]
    assert cases[0].source_files == ("doc_a.txt",)
    assert "stale_split_name.txt" not in cases[0].source_files
    assert cases[1].source_files == ("doc_a.txt", "doc_b.txt")
    assert cases[0].missing_files == ()
    assert cases[1].answer == "Alice, Bob"
    assert all(path.is_file() for case in cases for path in case.corpus_paths)


def test_missing_source_files_lists_val_gap() -> None:
    paths = _paths()
    missing = missing_source_files(
        csv_path=paths["csv"],
        corpus_dir=paths["corpus"],
        split="val",
        split_dir=paths["split_dir"],
    )
    assert missing == ("missing_doc.txt",)


def test_load_cases_fails_closed_on_missing_file() -> None:
    paths = _paths()
    with pytest.raises(OfficeQADatasetError, match="missing_doc.txt"):
        load_cases(
            "val",
            csv_path=paths["csv"],
            split_dir=paths["split_dir"],
            corpus_dir=paths["corpus"],
            require_files=True,
        )


def test_load_cases_can_surface_missing_without_raising() -> None:
    paths = _paths()
    cases = load_cases(
        "val",
        csv_path=paths["csv"],
        split_dir=paths["split_dir"],
        corpus_dir=paths["corpus"],
        require_files=False,
    )
    assert cases[0].missing_files == ("missing_doc.txt",)
    assert cases[0].corpus_paths == ()


def test_prompt_does_not_include_gold_answer() -> None:
    paths = _paths()
    case = load_cases(
        "train",
        csv_path=paths["csv"],
        split_dir=paths["split_dir"],
        corpus_dir=paths["corpus"],
    )[1]
    prompt = build_prompt(case, "# skill\n\nPrefer the table footnotes.\n")
    assert case.answer not in prompt
    assert case.question in prompt
    assert "docs/doc_a.txt" in prompt
    assert "<FINAL_ANSWER>" in prompt
    assert "Active skill (injected verbatim)" in prompt
    assert "Prefer the table footnotes." in prompt


@pytest.mark.skipif(
    not DEFAULT_CSV_PATH.is_file(),
    reason="gated OfficeQA CSV is not materialized",
)
def test_public_id_split_joins_gated_csv() -> None:
    cases = load_cases("val", require_files=False)
    assert len(cases) == 24
    assert all(case.question and case.answer for case in cases)
    missing = missing_source_files(split="val")
    assert missing == ()
