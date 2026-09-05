"""Fetch gated OfficeQA bulletin files via the Hugging Face CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from wikiskill.officeqa.dataset import (
    CORPUS_RELDIR,
    DEFAULT_CORPUS_DIR,
    DEFAULT_CSV_PATH,
    DEFAULT_SPLIT_DIR,
    missing_source_files,
)

HF_REPO = "databricks/officeqa"
DEFAULT_REVISION = "8ecbf18d3833daf4750a903d14963e4c4c1d4cd8"
BATCH_SIZE = 20


class OfficeQAFetchError(RuntimeError):
    """The Hugging Face CLI could not fetch a bulletin batch."""


def _hf_bin() -> str:
    path = shutil.which("hf")
    if path:
        return path
    fallback = Path.home() / ".local" / "bin" / "hf"
    if fallback.is_file():
        return str(fallback)
    raise OfficeQAFetchError("hf CLI not found on PATH (install huggingface_hub)")


def fetch_missing(
    *,
    csv_path: Path = DEFAULT_CSV_PATH,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    split: str | None = None,
    limit: int | None = None,
    revision: str = DEFAULT_REVISION,
) -> tuple[str, ...]:
    """Download every still-missing basename.  Returns files fetched."""
    missing = missing_source_files(
        csv_path=csv_path,
        corpus_dir=corpus_dir,
        split=split,
        split_dir=split_dir,
        limit=limit,
    )
    if not missing:
        return ()
    corpus_dir.mkdir(parents=True, exist_ok=True)
    hf = _hf_bin()
    fetched: list[str] = []
    for start in range(0, len(missing), BATCH_SIZE):
        batch = missing[start : start + BATCH_SIZE]
        filenames = [str(CORPUS_RELDIR / name) for name in batch]
        cmd = [
            hf,
            "download",
            HF_REPO,
            "--repo-type",
            "dataset",
            "--revision",
            revision,
            "--local-dir",
            str(corpus_dir),
        ]
        for rel in filenames:
            cmd.extend(["--include", rel])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise OfficeQAFetchError(
                f"hf download failed for {batch[:3]}... "
                f"(exit {proc.returncode}): {proc.stderr[-1500:]}"
            )
        fetched.extend(batch)
    still = missing_source_files(
        csv_path=csv_path,
        corpus_dir=corpus_dir,
        split=split,
        split_dir=split_dir,
        limit=limit,
    )
    if still:
        raise OfficeQAFetchError(f"still missing after fetch: {list(still)[:12]}")
    return tuple(fetched)
