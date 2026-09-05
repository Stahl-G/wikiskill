from pathlib import Path

import pytest

from wikiskill.k4_lock import acquire_k4_lock


def test_k4_lock_blocks_second_holder(tmp_path: Path) -> None:
    acquire_k4_lock(tmp_path)
    with pytest.raises(SystemExit, match="already running"):
        acquire_k4_lock(tmp_path)
