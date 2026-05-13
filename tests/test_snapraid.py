import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, tmp_path / "state.json"


VALID_SNAPRAID_CONFIG = {
    "parity_mode": "single",
    "parity_disks": ["/mnt/parity1"],
    "data_mounts": ["/mnt/disk1", "/mnt/disk2"],
    "sync_time": "02:00",
    "scrub_schedule": "weekly",
}


def test_post_snapraid_returns_200(client):
    c, _ = client
    resp = c.post("/api/snapraid", json=VALID_SNAPRAID_CONFIG)
    assert resp.status_code == 200


def test_post_snapraid_persists_config(client):
    import json
    c, state_file = client
    c.post("/api/snapraid", json=VALID_SNAPRAID_CONFIG)
    state = json.loads(state_file.read_text())
    assert state["snapraid_parity_mode"] == "single"
    assert state["snapraid_parity_disks"] == ["/mnt/parity1"]
    assert state["snapraid_sync_time"] == "02:00"
    assert state["snapraid_scrub_schedule"] == "weekly"


def test_post_snapraid_dual_parity_requires_two_disks(client):
    c, _ = client
    resp = c.post("/api/snapraid", json={
        **VALID_SNAPRAID_CONFIG,
        "parity_mode": "dual",
        "parity_disks": ["/mnt/parity1"],  # only one — should fail
    })
    assert resp.status_code == 400


def test_post_snapraid_dual_parity_two_disks_passes(client):
    c, _ = client
    resp = c.post("/api/snapraid", json={
        **VALID_SNAPRAID_CONFIG,
        "parity_mode": "dual",
        "parity_disks": ["/mnt/parity1", "/mnt/parity2"],
    })
    assert resp.status_code == 200


def test_post_snapraid_invalid_scrub_schedule_returns_400(client):
    c, _ = client
    resp = c.post("/api/snapraid", json={**VALID_SNAPRAID_CONFIG, "scrub_schedule": "hourly"})
    assert resp.status_code == 400


def test_post_snapraid_missing_parity_disks_returns_400(client):
    c, _ = client
    payload = {**VALID_SNAPRAID_CONFIG, "parity_disks": []}
    resp = c.post("/api/snapraid", json=payload)
    assert resp.status_code == 400


# --- snapraid.conf generator ---

def test_generate_conf_single_parity():
    from system.snapraid_conf import generate_conf
    conf = generate_conf(
        parity_disks=["/mnt/parity1"],
        data_mounts=["/mnt/disk1", "/mnt/disk2"],
        parity_mode="single",
    )
    assert "parity /mnt/parity1/snapraid.parity" in conf
    assert "2-parity" not in conf.split("#")[0]  # not an active line
    assert "data d1 /mnt/disk1" in conf
    assert "data d2 /mnt/disk2" in conf


def test_generate_conf_dual_parity():
    from system.snapraid_conf import generate_conf
    conf = generate_conf(
        parity_disks=["/mnt/parity1", "/mnt/parity2"],
        data_mounts=["/mnt/disk1"],
        parity_mode="dual",
    )
    assert "parity /mnt/parity1/snapraid.parity" in conf
    assert "2-parity /mnt/parity2/snapraid.parity" in conf


def test_generate_conf_content_files_on_each_data_disk():
    from system.snapraid_conf import generate_conf
    conf = generate_conf(
        parity_disks=["/mnt/parity1"],
        data_mounts=["/mnt/disk1", "/mnt/disk2"],
        parity_mode="single",
    )
    assert "content /mnt/disk1/snapraid.content" in conf
    assert "content /mnt/disk2/snapraid.content" in conf
