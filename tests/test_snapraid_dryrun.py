import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def configured_client(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_path))
    from system.state import write_state
    write_state({
        "snapraid_parity_disks": ["/dev/sdb"],
        "snapraid_data_mounts": ["/mnt/disk1"],
        "snapraid_parity_mode": "single",
    })
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_dryrun_no_snapraid_config(client):
    resp = client.get('/api/snapraid/dry-run')
    assert resp.status_code == 400
    assert b"not configured" in resp.data


def test_dryrun_success(configured_client):
    mock_result = MagicMock(returncode=0, stdout="All done", stderr="")
    with patch("routes.snapraid.subprocess.run", return_value=mock_result):
        resp = configured_client.get('/api/snapraid/dry-run')
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_dryrun_failure(configured_client):
    mock_result = MagicMock(returncode=1, stdout="", stderr="disk not found")
    with patch("routes.snapraid.subprocess.run", return_value=mock_result):
        resp = configured_client.get('/api/snapraid/dry-run')
    assert resp.status_code == 500
    assert resp.get_json()["ok"] is False
