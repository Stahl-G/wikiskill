"""Packaged read-only resources and caller-owned data paths."""
import os
from pathlib import Path
from importlib.resources import files
RESOURCES = Path(str(files("wikiskill") / "resources"))
DATA_ROOT = Path(os.environ.get("WIKISKILL_DATA_DIR", "data")).resolve()
