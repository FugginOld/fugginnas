import json
import subprocess
from typing import Any


_LSBLK_CMD = ["lsblk", "-J", "-b", "-o", "NAME,SIZE,MODEL,TYPE,MOUNTPOINT,FSTYPE,TRAN"]


def list_drives() -> list[dict[str, Any]]:
    result = subprocess.run(_LSBLK_CMD, capture_output=True, text=True, check=True)
    return _parse_lsblk(result.stdout)


def _parse_lsblk(output: str) -> list[dict[str, Any]]:
    data = json.loads(output)
    return [
        {
            "name": dev["name"],
            "size": int(dev.get("size") or 0),
            "model": (dev.get("model") or "").strip() or None,
            "type": dev["type"],
            "mountpoint": dev.get("mountpoint"),
            "fstype": dev.get("fstype"),
            "tran": dev.get("tran"),
        }
        for dev in data.get("blockdevices", [])
        if dev.get("type") == "disk"
    ]
