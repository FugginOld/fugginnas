import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, tmp_path / "state.json"


VALID_POOL_CONFIG = {
    "pool_mount": "/mnt/pool",
    "cache_mount": "/mnt/cache",
    "data_mounts": ["/mnt/disk1", "/mnt/disk2"],
    "write_policy": "mfs",
}


def test_post_pool_returns_200(client):
    c, _ = client
    resp = c.post("/api/pool", json=VALID_POOL_CONFIG)
    assert resp.status_code == 200


def test_post_pool_persists_config(client):
    import json
    c, state_file = client
    c.post("/api/pool", json=VALID_POOL_CONFIG)
    state = json.loads(state_file.read_text())
    assert state["pool_mount"] == "/mnt/pool"
    assert state["cache_mount"] == "/mnt/cache"
    assert state["data_mounts"] == ["/mnt/disk1", "/mnt/disk2"]
    assert state["write_policy"] == "mfs"


def test_post_pool_missing_pool_mount_returns_400(client):
    c, _ = client
    payload = {**VALID_POOL_CONFIG}
    del payload["pool_mount"]
    resp = c.post("/api/pool", json=payload)
    assert resp.status_code == 400


def test_post_pool_missing_cache_mount_returns_400(client):
    c, _ = client
    payload = {**VALID_POOL_CONFIG}
    del payload["cache_mount"]
    resp = c.post("/api/pool", json=payload)
    assert resp.status_code == 400


def test_post_pool_empty_data_mounts_returns_400(client):
    c, _ = client
    resp = c.post("/api/pool", json={**VALID_POOL_CONFIG, "data_mounts": []})
    assert resp.status_code == 400


def test_post_pool_invalid_write_policy_returns_400(client):
    c, _ = client
    resp = c.post("/api/pool", json={**VALID_POOL_CONFIG, "write_policy": "bogus"})
    assert resp.status_code == 400


def test_post_pool_default_write_policy_is_mfs(client):
    import json
    c, state_file = client
    payload = {k: v for k, v in VALID_POOL_CONFIG.items() if k != "write_policy"}
    resp = c.post("/api/pool", json=payload)
    assert resp.status_code == 200
    state = json.loads(state_file.read_text())
    assert state["write_policy"] == "mfs"


def test_post_pool_uses_write_known_state(client, monkeypatch):
    import routes.pool as pool_route

    c, _ = client
    calls = []

    def fake_write_known_state(payload):
        calls.append(payload)

    monkeypatch.setattr("routes.pool.write_known_state", fake_write_known_state)
    assert not hasattr(pool_route, "write_state")

    resp = c.post("/api/pool", json=VALID_POOL_CONFIG)
    assert resp.status_code == 200
    assert calls == [VALID_POOL_CONFIG]


# --- mergerfs mount string builder ---

def test_build_mergerfs_mount_string():
    from system.mergerfs import build_mount_string
    result = build_mount_string(
        sources=["/mnt/cache", "/mnt/disk1", "/mnt/disk2"],
        target="/mnt/pool",
        write_policy="mfs",
    )
    assert result.startswith("/mnt/cache:/mnt/disk1:/mnt/disk2")
    assert "/mnt/pool" in result
    assert "category.create=mfs" in result


def test_build_mergerfs_mount_string_existing_policy():
    from system.mergerfs import build_mount_string
    result = build_mount_string(
        sources=["/mnt/cache", "/mnt/disk1"],
        target="/mnt/pool",
        write_policy="existing",
    )
    assert "category.create=existing" in result
