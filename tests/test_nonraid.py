import json
import pytest
from unittest.mock import patch


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
    assert resp.get_json() == {"error": "invalid parity_mode"}


def test_post_nonraid_config_invalid_filesystem(client):
    c, _ = client
    resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "filesystem": "ntfs"})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "invalid filesystem", "valid": ["btrfs", "ext4", "xfs", "zfs"]}


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
    assert resp.get_json() == {"error": "check_speed_limit must be 10–1000 MB/s"}


def test_post_nonraid_config_invalid_speed_limit_too_high(client):
    c, _ = client
    resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "check_speed_limit": 9999})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "check_speed_limit must be 10–1000 MB/s"}


def test_post_nonraid_config_speed_limit_boundary(client):
    c, _ = client
    for limit in (10, 200, 1000):
        resp = c.post("/api/nonraid/config", json={**VALID_CONFIG, "check_speed_limit": limit})
        assert resp.status_code == 200


def test_post_nonraid_config_uses_write_known_state(client, monkeypatch):
    c, _ = client
    calls = []

    def fake_write_known_state(payload):
        calls.append(payload)

    monkeypatch.setattr("routes.nonraid.write_known_state", fake_write_known_state)
    resp = c.post("/api/nonraid/config", json=VALID_CONFIG)

    assert resp.status_code == 200
    assert calls == [{
        "nonraid_parity_mode": "single",
        "nonraid_filesystem": "xfs",
        "nonraid_luks": False,
        "nonraid_turbo_write": False,
        "nonraid_check_schedule": "quarterly",
        "nonraid_check_correct": False,
        "nonraid_check_speed_limit": 200,
    }]


def test_post_nonraid_config_uses_config_update_builder(client):
    c, _ = client
    updates = {"nonraid_parity_mode": "single"}
    with patch("routes.nonraid.build_nonraid_config_updates", return_value=updates) as mock_builder, \
         patch("routes.nonraid.write_known_state") as mock_write:
        resp = c.post("/api/nonraid/config", json=VALID_CONFIG)

    assert resp.status_code == 200
    mock_builder.assert_called_once_with(VALID_CONFIG)
    mock_write.assert_called_once_with(updates)


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
    assert resp.get_json() == {"error": "mode must be CORRECT or NOCORRECT"}


def test_post_nonraid_install_uses_install_command_builder(client):
    c, _ = client
    expected_events = ["data: Running: echo one\n\n", "data: ok\n\n", "data: NonRAID install complete\n\n"]
    with patch("routes.nonraid.build_nonraid_install_stream", return_value=iter(expected_events)) as mock_builder:
        resp = c.post("/api/nonraid/install")
        body = resp.data.decode()

    assert resp.status_code == 200
    assert body == "".join(expected_events)
    mock_builder.assert_called_once_with()


def test_post_nonraid_install_uses_sse_helper_and_preserves_order(client):
    c, _ = client
    expected_events = [
        "data: Running: apt-get install -y gpg\n\n",
        "data: output for apt-get\n\n",
        "data: NonRAID install complete\n\n",
    ]
    with patch("routes.nonraid.build_nonraid_install_stream", return_value=iter(expected_events)) as mock_stream:
        resp = c.post("/api/nonraid/install")
        body = resp.data.decode()

    assert body == "".join(expected_events)
    mock_stream.assert_called_once_with()


def test_post_nonraid_install_preserves_error_sentinel_and_stops(client):
    c, _ = client
    expected_events = [
        "data: Running: apt-get update\n\n",
        "data: ERROR (exit 4)\n\n",
    ]
    with patch("routes.nonraid.build_nonraid_install_stream", return_value=iter(expected_events)):
        resp = c.post("/api/nonraid/install")
        body = resp.data.decode()

    assert "data: ERROR (exit 4)\n\n" in body
    assert "data: NonRAID install complete\n\n" not in body


def test_post_nonraid_install_delegates_stream_to_operation_builder(client):
    c, _ = client
    expected_events = ["data: Running: x\n\n", "data: NonRAID install complete\n\n"]
    with patch("routes.nonraid.build_nonraid_install_stream", return_value=iter(expected_events)) as mock_build:
        resp = c.post("/api/nonraid/install")
        body = resp.data.decode()

    assert resp.status_code == 200
    assert body == "".join(expected_events)
    mock_build.assert_called_once_with()


def test_post_nonraid_create_uses_operation_builder(client):
    c, _ = client
    operation = {
        "cmd": ["echo", "create"],
        "done_msg": "Array created successfully",
        "error_msg": "ERROR (exit {returncode})",
    }

    with patch("routes.nonraid.build_nonraid_create_operation", return_value=operation) as mock_builder, \
         patch("routes.nonraid.sse_subprocess", return_value=["data: Array created successfully\n\n"]) as mock_sse:
        resp = c.post("/api/nonraid/create")
        body = resp.data.decode()

    assert resp.status_code == 200
    assert body == "data: Array created successfully\n\n"
    mock_builder.assert_called_once_with()
    mock_sse.assert_called_once_with(
        ["echo", "create"],
        "Array created successfully",
        "ERROR (exit {returncode})",
    )


def test_post_nonraid_create_success_and_error_sentinels(client):
    c, _ = client

    with patch("routes.nonraid.sse_subprocess", return_value=["data: Array created successfully\n\n"]):
        ok_resp = c.post("/api/nonraid/create")
        ok_body = ok_resp.data.decode()
    with patch("routes.nonraid.sse_subprocess", return_value=["data: ERROR (exit 2)\n\n"]):
        err_resp = c.post("/api/nonraid/create")
        err_body = err_resp.data.decode()

    assert ok_body == "data: Array created successfully\n\n"
    assert err_body == "data: ERROR (exit 2)\n\n"


def test_post_nonraid_check_stream_order_and_completion(client):
    c, _ = client
    with patch(
        "routes.nonraid.sse_subprocess",
        return_value=["data: line one\n\n", "data: Check complete (exit 0)\n\n"],
    ):
        resp = c.post("/api/nonraid/check", json={"mode": "CORRECT"})
        body = resp.data.decode()

    assert body == "data: line one\n\ndata: Check complete (exit 0)\n\n"


def test_post_nonraid_check_uses_mode_and_operation_builders(client):
    c, _ = client
    operation = {
        "cmd": ["nmdctl", "check", "CORRECT"],
        "done_msg": "Check complete (exit {returncode})",
        "error_msg": "Check complete (exit {returncode})",
    }
    with patch("routes.nonraid.resolve_nonraid_check_mode", return_value="CORRECT") as mock_mode, \
         patch("routes.nonraid.build_nonraid_check_operation", return_value=operation) as mock_operation, \
         patch("routes.nonraid.nmdctl_check", return_value=object()) as mock_popen, \
         patch("routes.nonraid.sse_subprocess", return_value=["data: Check complete (exit 0)\n\n"]) as mock_sse:
        resp = c.post("/api/nonraid/check", json={"mode": "correct"})
        body = resp.data.decode()
        _, kwargs = mock_sse.call_args
        factory = kwargs["popen_factory"]
        factory(["ignored"])
        mock_popen.assert_called_once_with("CORRECT")

    assert resp.status_code == 200
    assert body == "data: Check complete (exit 0)\n\n"
    mock_mode.assert_called_once()
    mock_operation.assert_called_once_with("CORRECT")


def test_post_nonraid_check_without_mode_falls_back_to_stored_preference(client, monkeypatch):
    import routes.nonraid as nonraid_route
    c, _ = client

    monkeypatch.setattr(nonraid_route, "read_state", lambda: {"nonraid_check_correct": True})
    monkeypatch.setattr(nonraid_route, "nmdctl_check", lambda _mode: object())
    monkeypatch.setattr(
        nonraid_route,
        "sse_subprocess",
        lambda *_args, **_kwargs: iter(["data: Check complete (exit 0)\n\n"]),
    )

    resp = c.post("/api/nonraid/check", json={})
    assert resp.status_code == 200
    assert resp.data.decode() == "data: Check complete (exit 0)\n\n"


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
    assert resp.get_json() == {"error": "parity_mode 'single' requires exactly 1 parity disk(s)"}


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


def test_post_nonraid_roles_uses_write_known_state(client, monkeypatch):
    _set_parity_mode(client, "single")
    c, _ = client
    calls = []

    def fake_write_known_state(payload):
        calls.append(payload)

    monkeypatch.setattr("routes.nonraid.write_known_state", fake_write_known_state)
    resp = c.post("/api/nonraid/roles", json={
        "parity_disks": ["/dev/sdb"],
        "data_disks": ["/dev/sdc", "/dev/sdd"],
    })

    assert resp.status_code == 200
    assert calls == [{
        "nonraid_parity_disks": ["/dev/sdb"],
        "nonraid_data_disks": ["/dev/sdc", "/dev/sdd"],
    }]


def test_post_nonraid_roles_uses_roles_update_builder(client):
    c, _ = client
    updates = {"nonraid_parity_disks": ["/dev/sdb"], "nonraid_data_disks": ["/dev/sdc"]}
    with patch("routes.nonraid.read_state", return_value={"nonraid_parity_mode": "single"}), \
         patch("routes.nonraid.build_nonraid_roles_updates", return_value=updates) as mock_builder, \
         patch("routes.nonraid.write_known_state") as mock_write:
        resp = c.post("/api/nonraid/roles", json={
            "parity_disks": ["/dev/sdb"],
            "data_disks": ["/dev/sdc"],
        })

    assert resp.status_code == 200
    mock_builder.assert_called_once_with(
        "single",
        ["/dev/sdb"],
        ["/dev/sdc"],
    )
    mock_write.assert_called_once_with(updates)
