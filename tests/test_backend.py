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


def test_post_backend_snapraid_returns_200(client):
    c, _ = client
    resp = c.post("/api/backend", json={"backend": "snapraid"})
    assert resp.status_code == 200


def test_post_backend_nonraid_returns_200(client):
    c, _ = client
    resp = c.post("/api/backend", json={"backend": "nonraid"})
    assert resp.status_code == 200


def test_post_backend_mergerfs_returns_200(client):
    c, _ = client
    resp = c.post("/api/backend", json={"backend": "mergerfs"})
    assert resp.status_code == 200


def test_post_backend_persists_to_state(client):
    c, state_file = client
    c.post("/api/backend", json={"backend": "snapraid"})
    state = json.loads(state_file.read_text())
    assert state["backend"] == "snapraid"


def test_post_backend_invalid_value_returns_400(client):
    c, _ = client
    resp = c.post("/api/backend", json={"backend": "invalid"})
    assert resp.status_code == 400


def test_post_backend_missing_field_returns_400(client):
    c, _ = client
    resp = c.post("/api/backend", json={})
    assert resp.status_code == 400


def test_post_backend_no_body_returns_400(client):
    c, _ = client
    resp = c.post("/api/backend", data="not-json", content_type="text/plain")
    assert resp.status_code == 400
