import json
import pytest
from unittest.mock import patch, MagicMock  # noqa: F401 — MagicMock used in apply tests


FULL_STATE = {
    "backend": "snapraid",
    "pool_mount": "/mnt/pool",
    "cache_mount": "/mnt/cache",
    "data_mounts": ["/mnt/disk1", "/mnt/disk2"],
    "write_policy": "mfs",
    "snapraid_parity_mode": "single",
    "snapraid_parity_disks": ["/mnt/parity1"],
    "snapraid_data_mounts": ["/mnt/disk1", "/mnt/disk2"],
    "snapraid_sync_time": "02:00",
    "snapraid_scrub_schedule": "weekly",
    "mover_schedule_time": "03:00",
    "mover_age_hours": 24,
    "mover_min_free_pct": 20,
    "shares": [{"name": "pool", "path": "/mnt/pool", "protocol": "smb",
                "smb_guest_ok": True, "smb_username": "", "smb_password": "",
                "nfs_allowed_hosts": "192.168.0.0/16", "nfs_readonly": False}],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(FULL_STATE))
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_file))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# --- GET /api/summary ---

def test_get_summary_returns_200(client):
    resp = client.get("/api/summary")
    assert resp.status_code == 200


def test_get_summary_lists_expected_files(client):
    resp = client.get("/api/summary")
    data = resp.get_json()
    files = [f["path"] for f in data["files"]]
    assert "/etc/snapraid.conf" in files
    assert "/usr/local/bin/FugginNAS-mover.sh" in files
    assert "/etc/fstab" in files


def test_get_summary_includes_content_preview(client):
    resp = client.get("/api/summary")
    data = resp.get_json()
    snapraid_entry = next(f for f in data["files"] if f["path"] == "/etc/snapraid.conf")
    assert "content" in snapraid_entry
    assert len(snapraid_entry["content"]) > 0


def test_get_summary_uses_explicit_state_with_pure_manifest_builder(client):
    expected_files = [{"path": "/tmp/example", "content": "ok"}]
    with patch("routes.summary.read_state", return_value={"backend": "snapraid"}) as mock_read_state, \
         patch("routes.summary.build_file_manifest_for_state", return_value=expected_files) as mock_pure_builder:
        resp = client.get("/api/summary")

    assert resp.status_code == 200
    assert resp.get_json()["files"] == expected_files
    mock_read_state.assert_called_once()
    mock_pure_builder.assert_called_once_with({"backend": "snapraid"})


# --- POST /api/apply ---


def test_post_apply_uses_explicit_state_with_pure_manifest_builder(client):
    fake_state = {"backend": "snapraid"}
    fake_manifest = [{"path": "/etc/fstab", "content": "entry"}]
    with patch("routes.apply.read_state", return_value=fake_state) as mock_read_state, \
         patch("routes.apply.build_file_manifest_for_state", return_value=fake_manifest) as mock_pure_builder, \
         patch("routes.apply.apply_all_for_state", return_value=[]), \
         patch("routes.apply.backup_fstab"), \
         patch("routes.apply.sse_subprocess", return_value=[]):
        resp = client.post("/api/apply")
        _ = resp.data

    assert resp.status_code == 200
    mock_read_state.assert_called_once()
    mock_pure_builder.assert_called_once_with(fake_state)

def test_post_apply_returns_event_stream(client):
    with patch("routes.apply.apply_all_for_state") as mock_apply, \
         patch("routes.apply.backup_fstab"), \
         patch("routes.apply.build_file_manifest_for_state", return_value=[]), \
         patch("routes.apply.sse_subprocess", return_value=["data: systemctl enable FugginNAS-mover.timer: OK\n\n"]), \
         patch("subprocess.run") as mock_sub:
        mock_apply.return_value = []
        mock_sub.return_value = MagicMock(returncode=0, stderr="")
        resp = client.post("/api/apply")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type


def test_post_apply_calls_apply_all(client):
    with patch("routes.apply.apply_all_for_state") as mock_apply, \
         patch("routes.apply.backup_fstab"), \
         patch("routes.apply.build_file_manifest_for_state", return_value=[]), \
         patch("routes.apply.sse_subprocess", return_value=["data: systemctl enable FugginNAS-mover.timer: OK\n\n"]), \
         patch("subprocess.run") as mock_sub:
        mock_apply.return_value = []
        mock_sub.return_value = MagicMock(returncode=0, stderr="")
        resp = client.post("/api/apply")
        _ = resp.data  # consume SSE stream so generator executes
        mock_apply.assert_called_once()


def test_post_apply_passes_explicit_state_to_apply_all_for_state(client):
    fake_state = {"backend": "snapraid"}
    with patch("routes.apply.read_state", return_value=fake_state), \
         patch("routes.apply.build_file_manifest_for_state", return_value=[]), \
         patch("routes.apply.apply_all_for_state", return_value=[]) as mock_apply_for_state, \
         patch("routes.apply.backup_fstab"), \
         patch("routes.apply.sse_subprocess", return_value=[]):
        resp = client.post("/api/apply")
        _ = resp.data

    assert resp.status_code == 200
    mock_apply_for_state.assert_called_once_with(fake_state)


def test_post_apply_streams_file_paths(client):
    with patch("routes.apply.apply_all_for_state") as mock_apply, \
         patch("routes.apply.backup_fstab"), \
         patch("routes.apply.build_file_manifest_for_state", return_value=[]), \
         patch("routes.apply.sse_subprocess", return_value=["data: systemctl enable FugginNAS-mover.timer: OK\n\n"]), \
         patch("subprocess.run") as mock_sub:
        mock_apply.return_value = ["/etc/snapraid.conf", "/usr/local/bin/FugginNAS-mover.sh"]
        mock_sub.return_value = MagicMock(returncode=0, stderr="")
        resp = client.post("/api/apply")
        body = resp.data.decode()
    assert "/etc/snapraid.conf" in body
    assert "Apply complete" in body


def test_post_apply_uses_sse_helper_for_snapraid_timers(client):
    with patch("routes.apply.apply_all_for_state", return_value=[]), \
         patch("routes.apply.backup_fstab"), \
         patch("routes.apply.build_file_manifest_for_state", return_value=[]), \
         patch("routes.apply.sse_subprocess", return_value=[]) as mock_sse:
        resp = client.post("/api/apply")
        _ = resp.data

    calls = [c.args for c in mock_sse.call_args_list]
    assert (
        ["systemctl", "enable", "--now", "snapraid-sync.timer"],
        "systemctl enable snapraid-sync.timer: OK",
        "systemctl enable snapraid-sync.timer: WARN: {stderr}",
    ) in calls
    assert (
        ["systemctl", "enable", "--now", "snapraid-scrub.timer"],
        "systemctl enable snapraid-scrub.timer: OK",
        "systemctl enable snapraid-scrub.timer: WARN: {stderr}",
    ) in calls


def test_post_apply_preserves_snapraid_timer_error_sentinel_text(client):
    events = {
        "snapraid-sync.timer": ["data: systemctl enable snapraid-sync.timer: WARN: sync failed\n\n"],
        "snapraid-scrub.timer": ["data: systemctl enable snapraid-scrub.timer: WARN: scrub failed\n\n"],
        "FugginNAS-mover.timer": ["data: systemctl enable FugginNAS-mover.timer: OK\n\n"],
    }

    def _fake_sse(cmd, done_msg, error_msg):
        _ = done_msg
        _ = error_msg
        return events[cmd[-1]]

    with patch("routes.apply.apply_all_for_state", return_value=[]), \
         patch("routes.apply.backup_fstab"), \
         patch("routes.apply.build_file_manifest_for_state", return_value=[]), \
         patch("routes.apply.sse_subprocess", side_effect=_fake_sse):
        resp = client.post("/api/apply")
        body = resp.data.decode()

    assert "data: systemctl enable snapraid-sync.timer: WARN: sync failed\n\n" in body
    assert "data: systemctl enable snapraid-scrub.timer: WARN: scrub failed\n\n" in body
