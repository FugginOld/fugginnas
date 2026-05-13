import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, tmp_path / "state.json"


SMB_SHARE = {
    "name": "pool",
    "path": "/mnt/pool",
    "protocol": "smb",
    "smb_guest_ok": True,
}

NFS_SHARE = {
    "name": "pool",
    "path": "/mnt/pool",
    "protocol": "nfs",
    "nfs_allowed_hosts": "192.168.0.0/16",
    "nfs_readonly": False,
}

BOTH_SHARE = {
    "name": "pool",
    "path": "/mnt/pool",
    "protocol": "both",
    "smb_guest_ok": False,
    "smb_username": "nas",
    "smb_password": "secret",
    "nfs_allowed_hosts": "192.168.1.0/24",
    "nfs_readonly": False,
}


def test_post_shares_smb_returns_200(client):
    c, _ = client
    resp = c.post("/api/shares", json=SMB_SHARE)
    assert resp.status_code == 200


def test_post_shares_nfs_returns_200(client):
    c, _ = client
    resp = c.post("/api/shares", json=NFS_SHARE)
    assert resp.status_code == 200


def test_post_shares_both_returns_200(client):
    c, _ = client
    resp = c.post("/api/shares", json=BOTH_SHARE)
    assert resp.status_code == 200


def test_post_shares_persists(client):
    import json
    c, state_file = client
    c.post("/api/shares", json=SMB_SHARE)
    state = json.loads(state_file.read_text())
    shares = state["shares"]
    assert len(shares) == 1
    assert shares[0]["name"] == "pool"
    assert shares[0]["protocol"] == "smb"


def test_post_shares_accumulates_multiple(client):
    import json
    c, state_file = client
    c.post("/api/shares", json=SMB_SHARE)
    c.post("/api/shares", json={**NFS_SHARE, "name": "backup", "path": "/mnt/backup"})
    state = json.loads(state_file.read_text())
    assert len(state["shares"]) == 2


def test_post_shares_invalid_protocol_returns_400(client):
    c, _ = client
    resp = c.post("/api/shares", json={**SMB_SHARE, "protocol": "ftp"})
    assert resp.status_code == 400


def test_post_shares_missing_name_returns_400(client):
    c, _ = client
    payload = {**SMB_SHARE}
    del payload["name"]
    resp = c.post("/api/shares", json=payload)
    assert resp.status_code == 400


def test_post_shares_missing_path_returns_400(client):
    c, _ = client
    payload = {**SMB_SHARE}
    del payload["path"]
    resp = c.post("/api/shares", json=payload)
    assert resp.status_code == 400


# --- smb.conf + exports generators ---

def test_generate_smb_block_guest():
    from system.samba import generate_smb_block
    block = generate_smb_block(name="pool", path="/mnt/pool", guest_ok=True)
    assert "[pool]" in block
    assert "path = /mnt/pool" in block
    assert "guest ok = yes" in block


def test_generate_smb_block_auth():
    from system.samba import generate_smb_block
    block = generate_smb_block(name="pool", path="/mnt/pool", guest_ok=False,
                               username="nas", password="secret")
    assert "guest ok = no" in block
    assert "valid users = nas" in block


def test_generate_nfs_export():
    from system.nfs import generate_export_line
    line = generate_export_line(path="/mnt/pool", allowed_hosts="192.168.0.0/16", readonly=False)
    assert line.startswith("/mnt/pool")
    assert "192.168.0.0/16" in line
    assert "rw" in line


def test_generate_nfs_export_readonly():
    from system.nfs import generate_export_line
    line = generate_export_line(path="/mnt/pool", allowed_hosts="192.168.0.0/16", readonly=True)
    assert "ro" in line
