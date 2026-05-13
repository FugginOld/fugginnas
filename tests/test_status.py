import json
import pytest
from unittest.mock import patch, MagicMock


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
