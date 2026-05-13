import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    monkeypatch.delenv("FUGGINNAS_PASSWORD", raising=False)
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("FUGGINNAS_PASSWORD", "secret123")
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# --- No password set ---

def test_api_passes_without_password(client):
    resp = client.post('/api/backend', json={'backend': 'snapraid'})
    assert resp.status_code == 200


def test_index_passes_without_password(client):
    resp = client.get('/')
    assert resp.status_code == 200


# --- Password set ---

def test_api_blocked_without_auth_header(auth_client):
    resp = auth_client.post('/api/backend', json={'backend': 'snapraid'})
    assert resp.status_code == 401


def test_api_blocked_with_wrong_token(auth_client):
    resp = auth_client.post('/api/backend', json={'backend': 'snapraid'},
                            headers={'Authorization': 'Bearer wrong'})
    assert resp.status_code == 401


def test_api_passes_with_correct_token(auth_client):
    resp = auth_client.post('/api/backend', json={'backend': 'snapraid'},
                            headers={'Authorization': 'Bearer secret123'})
    assert resp.status_code == 200


def test_index_not_protected_when_password_set(auth_client):
    resp = auth_client.get('/')
    assert resp.status_code == 200


# --- Localhost enforcement ---

def test_localhost_request_passes(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_non_localhost_request_forbidden(client):
    resp = client.get('/', environ_base={'REMOTE_ADDR': '10.0.0.5'})
    assert resp.status_code == 403
