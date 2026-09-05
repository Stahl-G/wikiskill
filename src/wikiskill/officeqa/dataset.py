"""Load OfficeQA cases from the public ID split plus the gated CSV/corpus.

The public repo stores only SkillOpt item IDs (no answers).  Questions,
gold answers, and bulletin text live under ``data/officeqa/``
and must never be committed.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from wikiskill.settings import RESOURCES, DATA_ROOT
DEFAULT_SPLIT_DIR = RESOURCES / "officeqa" / "id_split"
DEFAULT_CSV_PATH = DATA_ROOT / "officeqa" / "officeqa_full.csv"
DEFAULT_CORPUS_DIR = DATA_ROOT / "officeqa" / "corpus"
CORPUS_RELDIR = Path("treasury_bulletins_parsed") / "transformed"
SPLITS: tuple[str, ...] = ("train", "val", "test")


class OfficeQADatasetError(ValueError):
    """Split/CSV/corpus join failed closed."""


@dataclass(frozen=True)
class OfficeQACase:
    uid: str
    split: str
    difficulty: str
    question: str
    answer: str
    source_files: tuple[str, ...]
    source_docs: tuple[str, ...]
    corpus_paths: tuple[Path, ...]
    missing_files: tuple[str, ...]


def parse_multiline_field(raw: str) -> tuple[str, ...]:
    """Split a CSV/JSON multiline field on CR/LF.  Empty lines drop out."""
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    return tuple(part.strip() for part in text.split("\n") if part.strip())


def _load_csv_rows(csv_path: Path) -> dict[str, dict[str, str]]:
    if not csv_path.is_file():
        raise OfficeQADatasetError(
            f"OfficeQA CSV is missing at {csv_path} "
            "(gated Hugging Face payload; not in the public repo)"
        )
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_uid: dict[str, dict[str, str]] = {}
    for row in rows:
        uid = (row.get("uid") or "").strip()
        if not uid:
            raise OfficeQADatasetError(f"{csv_path} has a row with no uid")
        if uid in by_uid:
            raise OfficeQADatasetError(f"{csv_path} repeats uid {uid!r}")
        by_uid[uid] = row
    return by_uid


def _load_split_items(split_dir: Path, split: str) -> list[dict]:
    if split not in SPLITS:
        raise OfficeQADatasetError(f"unknown split {split!r}; expected {SPLITS}")
    path = split_dir / f"{split}.json"
    if not path.is_file():
        raise OfficeQADatasetError(f"split file is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise OfficeQADatasetError(f"{path} must be a non-empty JSON array")
    return payload


def index_corpus(corpus_dir: Path) -> dict[str, Path]:
    """Map bulletin basename -> path.  Duplicate basenames fail closed."""
    index: dict[str, Path] = {}
    if not corpus_dir.is_dir():
        return index
    preferred = corpus_dir / CORPUS_RELDIR
    root = preferred if preferred.is_dir() else corpus_dir
    for path in sorted(root.rglob("*.txt")):
        if ".cache" in path.parts:
            continue
        name = path.name
        existing = index.get(name)
        if existing is not None and existing.resolve() != path.resolve():
            raise OfficeQADatasetError(
                f"corpus has two files named {name!r}: {existing} and {path}"
            )
        index[name] = path
    return index


def missing_source_files(
    *,
    csv_path: Path = DEFAULT_CSV_PATH,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    split: str | None = None,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    limit: int | None = None,
) -> tuple[str, ...]:
    """Basenames required by the CSV (or one split) that the corpus lacks."""
    by_uid = _load_csv_rows(csv_path)
    if split is None:
        needed: list[str] = []
        seen: set[str] = set()
        for row in by_uid.values():
            for name in parse_multiline_field(row.get("source_files") or ""):
                if name not in seen:
                    seen.add(name)
                    needed.append(name)
    else:
        needed = []
        seen = set()
        items = _load_split_items(split_dir, split)
        if limit is not None:
            items = items[:limit]
        for item in items:
            uid = item["uid"]
            if uid not in by_uid:
                raise OfficeQADatasetError(f"split {split} uid {uid!r} is not in {csv_path}")
            for name in parse_multiline_field(by_uid[uid].get("source_files") or ""):
                if name not in seen:
                    seen.add(name)
                    needed.append(name)
    have = set(index_corpus(corpus_dir))
    return tuple(name for name in needed if name not in have)


def load_cases(
    split: str,
    *,
    csv_path: Path = DEFAULT_CSV_PATH,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    require_files: bool = True,
    limit: int | None = None,
    uids: tuple[str, ...] | None = None,
) -> tuple[OfficeQACase, ...]:
    """Join public split IDs to the gated CSV and local bulletin files.

    Split JSON is membership only (uid + split). Question, answer, and
    source filenames come from the CSV: SkillOpt's public file lists
    drift from the official payload on a handful of items.
    """
    by_uid = _load_csv_rows(csv_path)
    items = _load_split_items(split_dir, split)
    if uids is not None:
        wanted = set(uids)
        items = [item for item in items if item["uid"] in wanted]
        found = {item["uid"] for item in items}
        missing_uids = [uid for uid in uids if uid not in found]
        if missing_uids:
            raise OfficeQADatasetError(
                f"uids not in split {split}: {missing_uids}"
            )
    if limit is not None:
        items = items[:limit]
    corpus = index_corpus(corpus_dir)
    cases: list[OfficeQACase] = []
    missing_any: list[str] = []
    for item in items:
        uid = (item.get("uid") or "").strip()
        if not uid:
            raise OfficeQADatasetError(f"split {split} item has no uid")
        row = by_uid.get(uid)
        if row is None:
            raise OfficeQADatasetError(
                f"split {split} uid {uid!r} is not in {csv_path}"
            )
        if any(case.uid == uid for case in cases):
            raise OfficeQADatasetError(f"split {split} repeats uid {uid!r}")
        source_files = parse_multiline_field(row.get("source_files") or "")
        if not source_files:
            raise OfficeQADatasetError(f"{uid} has no source_files")
        source_docs = parse_multiline_field(row.get("source_docs") or "")
        corpus_paths: list[Path] = []
        missing: list[str] = []
        for name in source_files:
            path = corpus.get(name)
            if path is None:
                missing.append(name)
            else:
                corpus_paths.append(path)
        if missing:
            missing_any.extend(f"{uid}:{name}" for name in missing)
        cases.append(
            OfficeQACase(
                uid=uid,
                split=split,
                difficulty=(row.get("difficulty") or item.get("category") or "").strip(),
                question=(row.get("question") or "").strip(),
                answer=(row.get("answer") or "").strip(),
                source_files=source_files,
                source_docs=source_docs,
                corpus_paths=tuple(corpus_paths),
                missing_files=tuple(missing),
            )
        )
        if not cases[-1].question:
            raise OfficeQADatasetError(f"{uid} has an empty question")
        if not cases[-1].answer:
            raise OfficeQADatasetError(f"{uid} has an empty answer")
    if require_files and missing_any:
        preview = ", ".join(missing_any[:12])
        more = "" if len(missing_any) <= 12 else f" (+{len(missing_any) - 12} more)"
        raise OfficeQADatasetError(
            f"{len(missing_any)} source file(s) missing under {corpus_dir}: "
            f"{preview}{more}"
        )
    return tuple(cases)
