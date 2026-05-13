import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_post_nonraid_valid(client):
    resp = client.post('/api/nonraid', json={'devices': ['/dev/sdb', '/dev/sdc'], 'level': 1})
    assert resp.status_code == 200


def test_post_nonraid_valid_all_levels(client):
    for level in [0, 1, 5, 6, 10]:
        resp = client.post('/api/nonraid', json={'devices': ['/dev/sdb', '/dev/sdc'], 'level': level})
        assert resp.status_code == 200


def test_post_nonraid_with_custom_name(client):
    resp = client.post('/api/nonraid', json={'devices': ['/dev/sdb', '/dev/sdc'], 'level': 1, 'name': 'md1'})
    assert resp.status_code == 200


def test_post_nonraid_missing_devices(client):
    resp = client.post('/api/nonraid', json={'level': 1})
    assert resp.status_code == 400


def test_post_nonraid_empty_devices(client):
    resp = client.post('/api/nonraid', json={'devices': [], 'level': 1})
    assert resp.status_code == 400


def test_post_nonraid_missing_level(client):
    resp = client.post('/api/nonraid', json={'devices': ['/dev/sdb', '/dev/sdc']})
    assert resp.status_code == 400


def test_post_nonraid_invalid_level(client):
    resp = client.post('/api/nonraid', json={'devices': ['/dev/sdb', '/dev/sdc'], 'level': 3})
    assert resp.status_code == 400


def test_post_nonraid_saves_state(client, tmp_path, monkeypatch):
    import json
    state_path = tmp_path / "s2.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_path))
    from importlib import import_module, reload
    import system.state as ss
    reload(ss)
    client.post('/api/nonraid', json={'devices': ['/dev/sdb', '/dev/sdc'], 'level': 5})
    state = json.loads(state_path.read_text())
    assert state['nonraid']['level'] == 5
    assert '/dev/sdb' in state['nonraid']['devices']
