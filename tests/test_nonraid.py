import json
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, tmp_path / "state.json"


VALID_CONFIG = {
    "parity_mode": "single",
    "filesystem": "xfs",
    "luks": False,
    "turbo_write": False,
    "check_schedule": "quarterly",
    "check_correct": False,
    "check_speed_limit": 200,
}


# ── /api/nonraid/status ───────────────────────────────────────────────────────

def test_get_nonraid_status_returns_200(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "nmdctl_status", lambda: {"state": "STARTED"})
    c, _ = client
    resp = c.get("/api/nonraid/status")
    assert resp.status_code == 200


def test_get_nonraid_status_includes_state(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "nmdctl_status", lambda: {"state": "STOPPED"})
    c, _ = client
    resp = c.get("/api/nonraid/status")
    assert resp.get_json()["state"] == "STOPPED"


# ── /api/nonraid/install GET ──────────────────────────────────────────────────

def test_get_nonraid_install_when_installed(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "is_nonraid_installed", lambda: True)
    c, _ = client
    resp = c.get("/api/nonraid/install")
    assert resp.status_code == 200
    assert resp.get_json()["installed"] is True


def test_get_nonraid_install_when_not_installed(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "is_nonraid_installed", lambda: False)
    c, _ = client
    resp = c.get("/api/nonraid/install")
    assert resp.get_json()["installed"] is False


# ── /api/nonraid/config POST ──────────────────────────────────────────────────

def test_post_nonraid_config_returns_200(client):
    c, _ = client
    resp = c.post("/api/nonraid/config", json=VALID_CONFIG)
    assert resp.status_code == 200


def test_post_nonraid_config_persists_parity_mode(client):
    c, state_file = client
    c.post("/api/nonraid/config", json=VALID_CONFIG)
    state = json.loads(state_file.read_text())
    assert state["nonraid_parity_mode"] == "single"


def test_post_nonraid_config_persists_filesystem(client):
    c, state_file = client
    c.post("/api/nonraid/config", json=VALID_CONFIG)
    state = json.loads(state_file.read_text())
    assert state["nonraid_filesystem"] == "xfs"


def test_post_nonraid_config_persists_luks(client):
    c, state_file = client
    c.post("/api/nonraid/config", json={**VALID_CONFIG, "luks": True})
    state = json.loads(state_file.read_text())
    assert state["nonraid_luks"] is True


def test_post_nonraid_config_persists_turbo_write(client):
    c, state_file = client
    c.post("/api/nonraid/config", json={**VALID_CONFIG, "turbo_write": True})
    state = json.loads(state_file.read_text())
    assert state["nonraid_turbo_write"] is True


def test_post_nonraid_config_dual_parity(client):
    c, state_file = client
    resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "parity_mode": "dual"})
    assert resp.status_code == 200
    assert json.loads(state_file.read_text())["nonraid_parity_mode"] == "dual"


def test_post_nonraid_config_invalid_parity_mode(client):
    c, _ = client
    resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "parity_mode": "triple"})
    assert resp.status_code == 400


def test_post_nonraid_config_invalid_filesystem(client):
    c, _ = client
    resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "filesystem": "ntfs"})
    assert resp.status_code == 400


def test_post_nonraid_config_all_filesystems(client):
    c, _ = client
    for fs in ("xfs", "btrfs", "ext4", "zfs"):
        resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "filesystem": fs})
        assert resp.status_code == 200


def test_post_nonraid_config_persists_check_correct(client):
    c, state_file = client
    c.post("/api/nonraid/config", json={**VALID_CONFIG, "check_correct": True})
    assert json.loads(state_file.read_text())["nonraid_check_correct"] is True


def test_post_nonraid_config_persists_check_speed_limit(client):
    c, state_file = client
    c.post("/api/nonraid/config", json={**VALID_CONFIG, "check_speed_limit": 100})
    assert json.loads(state_file.read_text())["nonraid_check_speed_limit"] == 100


def test_post_nonraid_config_invalid_speed_limit_too_low(client):
    c, _ = client
    resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "check_speed_limit": 5})
    assert resp.status_code == 400


def test_post_nonraid_config_invalid_speed_limit_too_high(client):
    c, _ = client
    resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "check_speed_limit": 9999})
    assert resp.status_code == 400


def test_post_nonraid_config_speed_limit_boundary(client):
    c, _ = client
    for limit in (10, 200, 1000):
        resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "check_speed_limit": limit})
        assert resp.status_code == 200


# ── /api/nonraid/start / stop / mount / unmount ───────────────────────────────

def test_post_nonraid_start_ok(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "nmdctl_start", lambda: (True, "started"))
    c, _ = client
    assert c.post("/api/nonraid/start").status_code == 200


def test_post_nonraid_start_fail(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "nmdctl_start", lambda: (False, "error"))
    c, _ = client
    assert c.post("/api/nonraid/start").status_code == 500


def test_post_nonraid_stop_ok(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "nmdctl_stop", lambda: (True, "stopped"))
    c, _ = client
    assert c.post("/api/nonraid/stop").status_code == 200


def test_post_nonraid_mount_ok(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "nmdctl_mount", lambda prefix="/mnt/disk": (True, "ok"))
    c, _ = client
    assert c.post("/api/nonraid/mount").status_code == 200


def test_post_nonraid_unmount_ok(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "nmdctl_unmount", lambda: (True, "ok"))
    c, _ = client
    assert c.post("/api/nonraid/unmount").status_code == 200


# ── /api/nonraid/check ────────────────────────────────────────────────────────

def test_post_nonraid_check_invalid_mode(client):
    c, _ = client
    resp = c.post("/api/nonraid/check", json={"mode": "BADMODE"})
    assert resp.status_code == 400


# ── /api/nonraid/check/status ─────────────────────────────────────────────────

def test_get_nonraid_check_status_returns_200(client, monkeypatch):
    import routes.nonraid as nonraid_route
    monkeypatch.setattr(nonraid_route, "parse_nmdstat", lambda: {"mdResync": "0"})
    c, _ = client
    resp = c.get("/api/nonraid/check/status")
    assert resp.status_code == 200


# ── /api/nonraid/roles POST ───────────────────────────────────────────────────

def _set_parity_mode(client, mode):
    c, _ = client
    c.post("/api/nonraid/config", json={**VALID_CONFIG, "parity_mode": mode})


def test_post_nonraid_roles_returns_200(client):
    _set_parity_mode(client, "single")
    c, _ = client
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb"],
        "data_disks": ["/dev/sdc"],
    })
    assert resp.status_code == 200


def test_post_nonraid_roles_persists_parity_disks(client):
    _set_parity_mode(client, "single")
    c, state_file = client
    c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb"],
        "data_disks": ["/dev/sdc"],
    })
    state = json.loads(state_file.read_text())
    assert state["nonraid_parity_disks"] == ["/dev/sdb"]


def test_post_nonraid_roles_persists_data_disks(client):
    _set_parity_mode(client, "single")
    c, state_file = client
    c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb"],
        "data_disks": ["/dev/sdc", "/dev/sdd"],
    })
    state = json.loads(state_file.read_text())
    assert state["nonraid_data_disks"] == ["/dev/sdc", "/dev/sdd"]


def test_post_nonraid_roles_dual_parity_ok(client):
    _set_parity_mode(client, "dual")
    c, _ = client
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb", "/dev/sdc"],
        "data_disks": ["/dev/sdd"],
    })
    assert resp.status_code == 200


def test_post_nonraid_roles_wrong_parity_count_single(client):
    _set_parity_mode(client, "single")
    c, _ = client
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb", "/dev/sdc"],
        "data_disks": ["/dev/sdd"],
    })
    assert resp.status_code == 400


def test_post_nonraid_roles_zero_parity_single(client):
    _set_parity_mode(client, "single")
    c, _ = client
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": [],
        "data_disks": ["/dev/sdc"],
    })
    assert resp.status_code == 400


def test_post_nonraid_roles_wrong_parity_count_dual(client):
    _set_parity_mode(client, "dual")
    c, _ = client
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb"],
        "data_disks": ["/dev/sdc"],
    })
    assert resp.status_code == 400


def test_post_nonraid_roles_no_data_disks(client):
    _set_parity_mode(client, "single")
    c, _ = client
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb"],
        "data_disks": [],
    })
    assert resp.status_code == 400


def test_post_nonraid_roles_overlap_rejected(client):
    _set_parity_mode(client, "single")
    c, _ = client
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb"],
        "data_disks": ["/dev/sdb"],
    })
    assert resp.status_code == 400
