from unittest.mock import patch, MagicMock, mock_open
import subprocess
import json

from system.nonraid_utils import (
    build_nonraid_install_stream,
    nmdctl_status,
    nmdctl_start,
    nmdctl_stop,
    nmdctl_mount,
    nmdctl_unmount,
    parse_nmdstat,
    is_nonraid_installed,
)


def _make_proc(returncode=0, stdout="", stderr=""):
    p = MagicMock(spec=subprocess.CompletedProcess)
    p.returncode = returncode
    p.stdout = stdout
    p.stderr = stderr
    return p


# ── nmdctl_status ─────────────────────────────────────────────────────────────

def test_nmdctl_status_returns_dict_on_success():
    payload = {"state": "STARTED", "disks": []}
    with patch("system.nonraid_utils._run", return_value=_make_proc(0, json.dumps(payload))):
        result = nmdctl_status()
    assert result["state"] == "STARTED"


def test_nmdctl_status_returns_unknown_on_failure():
    with patch("system.nonraid_utils._run", return_value=_make_proc(1, stderr="no device")):
        result = nmdctl_status()
    assert result["state"] == "UNKNOWN"
    assert "error" in result


def test_nmdctl_status_handles_invalid_json():
    with patch("system.nonraid_utils._run", return_value=_make_proc(0, stdout="not-json")):
        result = nmdctl_status()
    assert "error" in result


# ── nmdctl_start ──────────────────────────────────────────────────────────────

def test_nmdctl_start_returns_true_on_success():
    with patch("system.nonraid_utils._run", return_value=_make_proc(0, stdout="started")):
        ok, msg = nmdctl_start()
    assert ok is True
    assert "started" in msg


def test_nmdctl_start_returns_false_on_failure():
    with patch("system.nonraid_utils._run", return_value=_make_proc(1, stderr="driver error")):
        ok, msg = nmdctl_start()
    assert ok is False
    assert "driver error" in msg


# ── nmdctl_stop ───────────────────────────────────────────────────────────────

def test_nmdctl_stop_returns_true_on_success():
    with patch("system.nonraid_utils._run", return_value=_make_proc(0, stdout="stopped")):
        ok, msg = nmdctl_stop()
    assert ok is True


def test_nmdctl_stop_returns_false_on_failure():
    with patch("system.nonraid_utils._run", return_value=_make_proc(1, stderr="busy")):
        ok, msg = nmdctl_stop()
    assert ok is False


# ── nmdctl_mount ──────────────────────────────────────────────────────────────

def test_nmdctl_mount_returns_true_on_success():
    with patch("system.nonraid_utils._run", return_value=_make_proc(0, stdout="mounted")):
        ok, msg = nmdctl_mount()
    assert ok is True


def test_nmdctl_mount_passes_prefix():
    captured = []
    def fake_run(cmd):
        captured.append(cmd)
        return _make_proc(0)
    with patch("system.nonraid_utils._run", side_effect=fake_run):
        nmdctl_mount(prefix="/mnt/data")
    assert "/mnt/data" in captured[0]


def test_nmdctl_mount_default_prefix():
    captured = []
    def fake_run(cmd):
        captured.append(cmd)
        return _make_proc(0)
    with patch("system.nonraid_utils._run", side_effect=fake_run):
        nmdctl_mount()
    assert "/mnt/disk" in captured[0]


# ── nmdctl_unmount ────────────────────────────────────────────────────────────

def test_nmdctl_unmount_returns_true_on_success():
    with patch("system.nonraid_utils._run", return_value=_make_proc(0, stdout="unmounted")):
        ok, msg = nmdctl_unmount()
    assert ok is True


def test_nmdctl_unmount_returns_false_on_failure():
    with patch("system.nonraid_utils._run", return_value=_make_proc(1, stderr="device busy")):
        ok, msg = nmdctl_unmount()
    assert ok is False


# ── parse_nmdstat ─────────────────────────────────────────────────────────────

def test_parse_nmdstat_returns_dict():
    content = "mdResync=0\nmdState=idle\n"
    with patch("builtins.open", mock_open(read_data=content)):
        result = parse_nmdstat()
    assert isinstance(result, dict)


def test_parse_nmdstat_returns_empty_on_missing_file():
    with patch("builtins.open", side_effect=OSError("no such file")):
        result = parse_nmdstat()
    assert result == {}


def test_parse_nmdstat_key_value_parsing():
    content = "mdResync=1234\nmdState=resync\n"
    with patch("builtins.open", mock_open(read_data=content)):
        result = parse_nmdstat()
    assert result.get("mdResync") == "1234"
    assert result.get("mdState") == "resync"


# ── is_nonraid_installed ──────────────────────────────────────────────────────

def test_is_nonraid_installed_true_when_dkms_shows_nonraid():
    with patch("system.nonraid_utils._run",
               return_value=_make_proc(0, stdout="nonraid/1.0, 5.15.0, installed")):
        assert is_nonraid_installed() is True


def test_is_nonraid_installed_false_when_not_present():
    with patch("system.nonraid_utils._run",
               return_value=_make_proc(0, stdout="zfs/2.1.0, 5.15.0, installed")):
        assert is_nonraid_installed() is False


def test_is_nonraid_installed_false_when_dkms_fails():
    with patch("system.nonraid_utils._run",
               return_value=_make_proc(1, stdout="")):
        assert is_nonraid_installed() is False


def test_build_nonraid_install_stream_preserves_order_and_completion():
    cmds = [["echo", "one"], ["echo", "two"]]

    def fake_sse(cmd, done_msg, error_msg):
        _ = done_msg
        _ = error_msg
        yield f"data: output for {' '.join(cmd)}\n\n"

    events = list(build_nonraid_install_stream(commands=cmds, sse_runner=fake_sse))

    assert events == [
        "data: Running: echo one\n\n",
        "data: output for echo one\n\n",
        "data: Running: echo two\n\n",
        "data: output for echo two\n\n",
        "data: NonRAID install complete\n\n",
    ]
