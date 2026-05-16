import json
import pytest
from unittest.mock import patch, MagicMock


NONRAID_STATE = {
    "backend": "nonraid",
    "pool_mount": "/mnt/pool",
    "cache_mount": "/mnt/cache",
    "nonraid_parity_disks": ["/dev/sdb"],
    "nonraid_data_disks": ["/dev/sdc", "/dev/sdd"],
    "nonraid_parity_mode": "single",
    "shares": [],
}

FULL_STATE = {
    "backend": "snapraid",
    "pool_mount": "/mnt/pool",
    "cache_mount": "/mnt/cache",
    "data_mounts": ["/mnt/disk1", "/mnt/disk2"],
    "write_policy": "mfs",
    "snapraid_parity_mode": "single",
    "snapraid_sync_time": "02:00",
    "mover_schedule_time": "03:00",
    "shares": [],
}

DF_OUTPUT = (
    "Filesystem     1B-blocks       Used  Available Use% Mounted on\n"
    "/mnt/pool      2000000000  500000000 1500000000  25% /mnt/pool\n"
    "/mnt/cache      500000000  400000000  100000000  80% /mnt/cache\n"
)


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


@pytest.fixture
def nonraid_client(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(NONRAID_STATE))
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_file))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _mock_run(stdout="", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


def test_get_status_returns_200(client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
    assert resp.status_code == 200


def test_get_status_has_pool_section(client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
    data = resp.get_json()
    assert "pool" in data


def test_get_status_pool_has_mount_and_usage(client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
    pool = resp.get_json()["pool"]
    assert pool["mount"] == "/mnt/pool"
    assert "used_pct" in pool


def test_get_status_uses_pool_panel_builder(client):
    fake_pool = {"mount": "/mnt/custom", "mounted": True, "used_pct": 10, "available_bytes": 123}
    with patch("system.status.build_pool_status", return_value=fake_pool) as mock_pool, \
         patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
        data = resp.get_json()

    assert resp.status_code == 200
    assert data["pool"] == fake_pool
    args, _ = mock_pool.call_args
    assert args[0] == FULL_STATE


def test_get_status_has_cache_fill_pct(client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
    data = resp.get_json()
    assert "cache_fill_pct" in data


def test_get_status_has_backend_field(client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
    data = resp.get_json()
    assert data["backend"] == "snapraid"


def test_get_status_has_theme_field(client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
    data = resp.get_json()
    assert data["theme"] == "default"


def test_get_status_backend_non_string_returns_none(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"backend": 123, "pool_mount": "/mnt/pool", "cache_mount": "/mnt/cache"}))
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_file))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as c, patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = c.get("/api/status")
    assert resp.get_json()["backend"] is None


# ── NonRAID status panel ──────────────────────────────────────────────────────

def test_nonraid_status_has_nonraid_key(nonraid_client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)), \
         patch("system.status.nmdctl_status", return_value={"state": "STARTED"}):
        resp = nonraid_client.get("/api/status")
    assert "nonraid" in resp.get_json()


def test_nonraid_status_state_from_nmdctl(nonraid_client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)), \
         patch("system.status.nmdctl_status", return_value={"state": "STOPPED"}):
        resp = nonraid_client.get("/api/status")
    assert resp.get_json()["nonraid"]["state"] == "STOPPED"


def test_nonraid_status_includes_parity_disks(nonraid_client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)), \
         patch("system.status.nmdctl_status", return_value={"state": "STARTED"}):
        resp = nonraid_client.get("/api/status")
    assert resp.get_json()["nonraid"]["parity_disks"] == ["/dev/sdb"]


def test_nonraid_status_includes_data_disks(nonraid_client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)), \
         patch("system.status.nmdctl_status", return_value={"state": "STARTED"}):
        resp = nonraid_client.get("/api/status")
    assert resp.get_json()["nonraid"]["data_disks"] == ["/dev/sdc", "/dev/sdd"]


def test_get_status_uses_nonraid_panel_builder(nonraid_client):
    fake_nonraid = {"state": "STARTED", "parity_disks": ["/dev/sdb"], "data_disks": ["/dev/sdc"]}
    with patch("system.status.build_nonraid_status", return_value=fake_nonraid) as mock_builder, \
         patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = nonraid_client.get("/api/status")
        data = resp.get_json()

    assert resp.status_code == 200
    assert data["nonraid"] == fake_nonraid
    args, _ = mock_builder.call_args
    assert args[0] == NONRAID_STATE


def test_build_nonraid_status_wires_nmd_and_state_disks():
    state = {
        "nonraid_parity_disks": ["/dev/sdb"],
        "nonraid_data_disks": ["/dev/sdc", "/dev/sdd"],
    }
    with patch("system.status.nmdctl_status", return_value={"state": "STOPPED"}) as mock_nmd:
        out = __import__("system.status", fromlist=["build_nonraid_status"]).build_nonraid_status(state)

    assert out == {
        "state": "STOPPED",
        "parity_disks": ["/dev/sdb"],
        "data_disks": ["/dev/sdc", "/dev/sdd"],
    }
    mock_nmd.assert_called_once_with()


def test_snapraid_backend_has_no_nonraid_key(client):
    with patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
    assert "nonraid" not in resp.get_json()


def test_get_status_uses_snapraid_panel_builder(client):
    fake_snapraid = {"sync": {"last_run": "x"}, "scrub": {"last_run": "y"}, "dirty_files": 7}
    with patch("system.status.build_snapraid_status", return_value=fake_snapraid) as mock_builder, \
         patch("system.status.subprocess.run", return_value=_mock_run(DF_OUTPUT)):
        resp = client.get("/api/status")
        data = resp.get_json()

    assert resp.status_code == 200
    assert data["snapraid"] == fake_snapraid
    args, _ = mock_builder.call_args
    assert args[0] == FULL_STATE


def test_build_snapraid_status_wires_logs_and_dirty_count():
    state = {"backend": "snapraid"}
    sync = {"last_run": "sync"}
    scrub = {"last_run": "scrub"}
    with patch("system.status._parse_snapraid_log", side_effect=[sync, scrub]) as mock_parse, \
         patch("system.status._snapraid_dirty_count", return_value=3) as mock_dirty:
        out = __import__("system.status", fromlist=["build_snapraid_status"]).build_snapraid_status(state)

    assert out == {"sync": sync, "scrub": scrub, "dirty_files": 3}
    assert mock_parse.call_count == 2
    mock_dirty.assert_called_once_with()


# ── Live share status ─────────────────────────────────────────────────────────

SHARES_STATE = {
    "backend": "snapraid",
    "pool_mount": "/mnt/pool",
    "cache_mount": "/mnt/cache",
    "shares": [
        {"name": "media", "path": "/mnt/pool/media", "protocol": "smb"},
        {"name": "backup", "path": "/mnt/pool/backup", "protocol": "nfs"},
        {"name": "docs",   "path": "/mnt/pool/docs",   "protocol": "both"},
    ],
}


@pytest.fixture
def shares_client(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(SHARES_STATE))
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_file))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _patch_shares(smbd=True, nfsd=True, path_exists=True, smb_ok=True, nfs_ok=True):
    """Return a subprocess.run side_effect that dispatches by command."""
    def _run(cmd, **kwargs):
        m = MagicMock()
        if "systemctl" in cmd:
            svc = cmd[-1]
            m.returncode = 0 if (smbd if svc == "smbd" else nfsd) else 1
        elif "smbclient" in cmd:
            m.returncode = 0 if smb_ok else 1
            m.stdout = ""
        elif "showmount" in cmd:
            m.returncode = 0 if nfs_ok else 1
            m.stdout = "/mnt/pool/backup 192.168.0.0/16\n/mnt/pool/docs 192.168.0.0/16\n" if nfs_ok else ""
        else:
            m.returncode = 0
            m.stdout = DF_OUTPUT
        return m
    return _run


def test_shares_status_has_services_key(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares()):
        data = shares_client.get("/api/status").get_json()
    assert "services" in data


def test_get_status_uses_shares_panel_builder(shares_client):
    fake_services = {"smbd": True, "nfs_server": False}
    fake_shares = [{"name": "media", "path_exists": True, "smb_reachable": True}]
    with patch("system.status.build_shares_status", return_value={"services": fake_services, "shares": fake_shares}) as mock_builder, \
         patch("system.status.subprocess.run", side_effect=_patch_shares()):
        resp = shares_client.get("/api/status")
        data = resp.get_json()

    assert resp.status_code == 200
    assert data["services"] == fake_services
    assert data["shares"] == fake_shares
    mock_builder.assert_called_once()


def test_shares_status_smbd_running(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares(smbd=True)):
        data = shares_client.get("/api/status").get_json()
    assert data["services"]["smbd"] is True


def test_shares_status_smbd_stopped(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares(smbd=False)):
        data = shares_client.get("/api/status").get_json()
    assert data["services"]["smbd"] is False


def test_shares_status_nfsd_running(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares(nfsd=True)):
        data = shares_client.get("/api/status").get_json()
    assert data["services"]["nfs_server"] is True


def test_shares_per_share_has_path_exists(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares()), \
         patch("system.status.Path.exists", return_value=True):
        data = shares_client.get("/api/status").get_json()
    assert all("path_exists" in s for s in data["shares"])


def test_shares_path_exists_true_when_present(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares()), \
         patch("system.status.Path.exists", return_value=True):
        shares = shares_client.get("/api/status").get_json()["shares"]
    assert all(s["path_exists"] is True for s in shares)


def test_shares_path_exists_false_when_missing(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares()), \
         patch("system.status.Path.exists", return_value=False):
        shares = shares_client.get("/api/status").get_json()["shares"]
    assert all(s["path_exists"] is False for s in shares)


def test_shares_smb_reachable_true(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares(smb_ok=True)), \
         patch("system.status.Path.exists", return_value=True):
        shares = shares_client.get("/api/status").get_json()["shares"]
    smb_shares = [s for s in shares if s.get("smb_reachable") is not None]
    assert all(s["smb_reachable"] is True for s in smb_shares)


def test_shares_smb_reachable_false_when_unreachable(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares(smb_ok=False)), \
         patch("system.status.Path.exists", return_value=True):
        shares = shares_client.get("/api/status").get_json()["shares"]
    smb_shares = [s for s in shares if s.get("smb_reachable") is not None]
    assert all(s["smb_reachable"] is False for s in smb_shares)


def test_shares_nfs_reachable_true(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares(nfs_ok=True)), \
         patch("system.status.Path.exists", return_value=True):
        shares = shares_client.get("/api/status").get_json()["shares"]
    nfs_shares = [s for s in shares if s.get("nfs_reachable") is not None]
    assert all(s["nfs_reachable"] is True for s in nfs_shares)


def test_shares_nfs_reachable_false_when_not_exported(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares(nfs_ok=False)), \
         patch("system.status.Path.exists", return_value=True):
        shares = shares_client.get("/api/status").get_json()["shares"]
    nfs_shares = [s for s in shares if s.get("nfs_reachable") is not None]
    assert all(s["nfs_reachable"] is False for s in nfs_shares)


def test_shares_smb_only_has_no_nfs_reachable(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares()), \
         patch("system.status.Path.exists", return_value=True):
        shares = shares_client.get("/api/status").get_json()["shares"]
    media = next(s for s in shares if s["name"] == "media")
    assert "nfs_reachable" not in media


def test_shares_nfs_only_has_no_smb_reachable(shares_client):
    with patch("system.status.subprocess.run", side_effect=_patch_shares()), \
         patch("system.status.Path.exists", return_value=True):
        shares = shares_client.get("/api/status").get_json()["shares"]
    backup = next(s for s in shares if s["name"] == "backup")
    assert "smb_reachable" not in backup
