from pathlib import Path
from unittest.mock import patch
import pytest

from system.apply_utils import backup_fstab, apply_all


def test_backup_fstab_copies_when_source_exists(tmp_path):
    fstab = tmp_path / "fstab"
    fstab.write_text("# original fstab")
    backup_fstab(str(fstab))
    bak = Path(str(fstab) + ".fugginnas.bak")
    assert bak.exists()
    assert bak.read_text() == "# original fstab"


def test_backup_fstab_noop_when_source_missing(tmp_path):
    backup_fstab(str(tmp_path / "nonexistent"))  # must not raise


def test_apply_all_calls_backup_fstab(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_path))
    from system.state import write_state
    write_state({
        "pool_mount": "/mnt/pool",
        "cache_mount": "/mnt/cache",
        "data_mounts": ["/mnt/disk1"],
        "write_policy": "mfs",
    })
    with patch("system.apply_utils.backup_fstab") as mock_backup, \
         patch("system.apply_utils._append_or_update_fstab"), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.write_text"):
        apply_all()
    mock_backup.assert_called_once_with("/etc/fstab")
