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


# ── GET /api/theme ────────────────────────────────────────────────────────────

def test_get_theme_returns_200(client):
    c, _ = client
    assert c.get("/api/theme").status_code == 200


def test_get_theme_default_when_no_state(client):
    c, _ = client
    assert c.get("/api/theme").get_json()["theme"] == "default"


def test_get_theme_returns_persisted_value(client):
    c, state_file = client
    state_file.write_text(json.dumps({"theme": "nord"}))
    assert c.get("/api/theme").get_json()["theme"] == "nord"


# ── POST /api/theme ───────────────────────────────────────────────────────────

def test_post_theme_returns_200(client):
    c, _ = client
    assert c.post("/api/theme", json={"theme": "default"}).status_code == 200


def test_post_theme_persists_value(client):
    c, state_file = client
    c.post("/api/theme", json={"theme": "dracula"})
    assert json.loads(state_file.read_text())["theme"] == "dracula"


def test_post_theme_invalid_name_returns_400(client):
    c, _ = client
    assert c.post("/api/theme", json={"theme": "nonexistent"}).status_code == 400


def test_post_theme_missing_key_returns_400(client):
    c, _ = client
    assert c.post("/api/theme", json={}).status_code == 400


def test_post_theme_all_valid_names_accepted(client):
    c, _ = client
    valid = [
        "default", "nord", "dracula", "solarized-dark", "gruvbox",
        "monokai", "catppuccin", "tokyo-night", "one-dark",
        "material", "github-dark", "synthwave",
        "tron-blue", "tron-red",
    ]
    for name in valid:
        resp = c.post("/api/theme", json={"theme": name})
        assert resp.status_code == 200, f"{name} was rejected"
