import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, tmp_path / "state.json"


VALID_MOVER_CONFIG = {
    "schedule_time": "03:00",
    "age_hours": 24,
    "min_free_pct": 20,
}


def test_post_mover_returns_200(client):
    c, _ = client
    resp = c.post("/api/mover", json=VALID_MOVER_CONFIG)
    assert resp.status_code == 200


def test_post_mover_persists_config(client):
    import json
    c, state_file = client
    c.post("/api/mover", json=VALID_MOVER_CONFIG)
    state = json.loads(state_file.read_text())
    assert state["mover_schedule_time"] == "03:00"
    assert state["mover_age_hours"] == 24
    assert state["mover_min_free_pct"] == 20


def test_post_mover_defaults_applied(client):
    import json
    c, state_file = client
    resp = c.post("/api/mover", json={})
    assert resp.status_code == 200
    state = json.loads(state_file.read_text())
    assert state["mover_schedule_time"] == "03:00"
    assert state["mover_age_hours"] == 24
    assert state["mover_min_free_pct"] == 20


def test_post_mover_invalid_min_free_pct_returns_400(client):
    c, _ = client
    resp = c.post("/api/mover", json={**VALID_MOVER_CONFIG, "min_free_pct": 110})
    assert resp.status_code == 400


def test_post_mover_negative_age_hours_returns_400(client):
    c, _ = client
    resp = c.post("/api/mover", json={**VALID_MOVER_CONFIG, "age_hours": -1})
    assert resp.status_code == 400


# --- mover script generator ---

def test_generate_mover_script_contains_config():
    from system.mover import generate_mover_script
    script = generate_mover_script(
        cache_mount="/mnt/cache",
        pool_mount="/mnt/pool",
        age_hours=24,
        min_free_pct=20,
    )
    assert "CACHE=/mnt/cache" in script
    assert "POOL=/mnt/pool" in script
    assert "MIN_FREE_PCT=20" in script
    assert "AGE_HOURS=24" in script


def test_generate_mover_script_uses_rsync():
    from system.mover import generate_mover_script
    script = generate_mover_script("/mnt/cache", "/mnt/pool", 24, 20)
    assert "rsync" in script
    assert "--remove-source-files" in script
