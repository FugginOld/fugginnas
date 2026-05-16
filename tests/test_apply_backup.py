from pathlib import Path
from unittest.mock import patch

from system.apply_utils import (
    apply_all,
    apply_all_for_state,
    backup_fstab,
    build_file_manifest,
    build_file_manifest_for_state,
)


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


def test_build_file_manifest_for_state_builds_without_read_state(monkeypatch):
    state = {
        "backend": "snapraid",
        "pool_mount": "/mnt/pool",
        "cache_mount": "/mnt/cache",
        "data_mounts": ["/mnt/disk1"],
        "write_policy": "mfs",
        "snapraid_parity_mode": "single",
        "snapraid_parity_disks": ["/mnt/parity1"],
        "snapraid_data_mounts": ["/mnt/disk1"],
    }
    monkeypatch.setattr("system.apply_utils.read_state", lambda: (_ for _ in ()).throw(RuntimeError("should not be called")))
    files = build_file_manifest_for_state(state)
    paths = [f["path"] for f in files]
    assert "/etc/fstab" in paths
    assert "/etc/snapraid.conf" in paths


def test_build_file_manifest_wrapper_matches_pure_function(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_path))
    from system.state import write_state

    state = {
        "backend": "mergerfs",
        "pool_mount": "/mnt/pool",
        "cache_mount": "/mnt/cache",
        "data_mounts": ["/mnt/disk1"],
        "write_policy": "mfs",
    }
    write_state(state)
    wrapper = build_file_manifest()
    pure = build_file_manifest_for_state(state)
    assert wrapper == pure


def test_apply_all_for_state_builds_manifest_from_explicit_state(monkeypatch):
    state = {"pool_mount": "/mnt/pool"}
    expected_manifest = [{"path": "/tmp/demo", "content": "x"}]
    monkeypatch.setattr("system.apply_utils.build_file_manifest_for_state", lambda s: expected_manifest if s is state else [])

    with patch("pathlib.Path.mkdir"), patch("pathlib.Path.write_text"):
        written = apply_all_for_state(state)

    assert written == ["/tmp/demo"]


def test_apply_all_wrapper_matches_apply_all_for_state(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_path))
    from system.state import write_state

    state = {"pool_mount": "/mnt/pool", "cache_mount": "/mnt/cache", "data_mounts": ["/mnt/disk1"]}
    write_state(state)

    with patch("system.apply_utils.backup_fstab"), \
         patch("system.apply_utils._append_or_update_fstab"), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.write_text"):
        wrapper = apply_all()
        pure = apply_all_for_state(state)

    assert wrapper == pure
