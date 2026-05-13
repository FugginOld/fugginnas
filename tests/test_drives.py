import json
import pytest
from unittest.mock import MagicMock, patch

LSBLK_SAMPLE = {
    "blockdevices": [
        {
            "name": "sda",
            "size": "500107862016",
            "model": "Samsung SSD 860 EVO ",
            "type": "disk",
            "mountpoint": None,
            "fstype": None,
            "tran": "sata",
        },
        {
            "name": "sdb",
            "size": "2000398934016",
            "model": "WDC WD20EZRZ",
            "type": "disk",
            "mountpoint": "/mnt/data",
            "fstype": "ext4",
            "tran": "sata",
        },
        {
            "name": "loop0",
            "size": "55574528",
            "model": None,
            "type": "loop",
            "mountpoint": "/snap/core18",
            "fstype": "squashfs",
            "tran": None,
        },
        {
            "name": "sda1",
            "size": "499000000000",
            "model": None,
            "type": "part",
            "mountpoint": "/boot",
            "fstype": "vfat",
            "tran": None,
        },
    ]
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# --- Pure parsing tests (no subprocess needed) ---

def test_parse_lsblk_returns_only_disks():
    from system.drive_utils import _parse_lsblk
    drives = _parse_lsblk(json.dumps(LSBLK_SAMPLE))
    assert all(d["type"] == "disk" for d in drives)
    assert len(drives) == 2


def test_parse_lsblk_excludes_loops_and_partitions():
    from system.drive_utils import _parse_lsblk
    drives = _parse_lsblk(json.dumps(LSBLK_SAMPLE))
    names = [d["name"] for d in drives]
    assert "loop0" not in names
    assert "sda1" not in names


def test_parse_lsblk_size_is_int():
    from system.drive_utils import _parse_lsblk
    drives = _parse_lsblk(json.dumps(LSBLK_SAMPLE))
    sda = next(d for d in drives if d["name"] == "sda")
    assert sda["size"] == 500107862016
    assert isinstance(sda["size"], int)


def test_parse_lsblk_strips_model_whitespace():
    from system.drive_utils import _parse_lsblk
    drives = _parse_lsblk(json.dumps(LSBLK_SAMPLE))
    sda = next(d for d in drives if d["name"] == "sda")
    assert sda["model"] == "Samsung SSD 860 EVO"


def test_parse_lsblk_null_model_is_none():
    from system.drive_utils import _parse_lsblk
    # sdb has no trailing whitespace, model should pass through
    drives = _parse_lsblk(json.dumps(LSBLK_SAMPLE))
    loop_entry = {"blockdevices": [{"name": "sdc", "size": "1000", "model": None,
                                     "type": "disk", "mountpoint": None,
                                     "fstype": None, "tran": "usb"}]}
    drives = _parse_lsblk(json.dumps(loop_entry))
    assert drives[0]["model"] is None


# --- HTTP endpoint tests ---

def test_get_drives_returns_200(client):
    with patch("system.drive_utils.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=json.dumps(LSBLK_SAMPLE))
        resp = client.get("/api/drives")
    assert resp.status_code == 200


def test_get_drives_returns_drive_list(client):
    with patch("system.drive_utils.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=json.dumps(LSBLK_SAMPLE))
        resp = client.get("/api/drives")
    data = resp.get_json()
    assert "drives" in data
    assert len(data["drives"]) == 2
    names = [d["name"] for d in data["drives"]]
    assert "sda" in names
    assert "sdb" in names


def test_get_drives_excludes_non_disks(client):
    with patch("system.drive_utils.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=json.dumps(LSBLK_SAMPLE))
        resp = client.get("/api/drives")
    data = resp.get_json()
    names = [d["name"] for d in data["drives"]]
    assert "loop0" not in names
    assert "sda1" not in names


def test_get_drives_lsblk_failure_returns_500(client):
    import subprocess
    with patch("system.drive_utils.subprocess.run",
               side_effect=subprocess.CalledProcessError(1, "lsblk")):
        resp = client.get("/api/drives")
    assert resp.status_code == 500
