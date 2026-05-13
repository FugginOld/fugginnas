import os
import shutil
from pathlib import Path

from system.mergerfs import build_mount_string
from system.mover import generate_mover_script
from system.nfs import generate_export_line
from system.samba import generate_smb_block
from system.snapraid_conf import generate_conf
from system.state import read_state


def backup_fstab(fstab_path: str) -> None:
    src = Path(fstab_path)
    if src.exists():
        shutil.copy2(src, str(src) + '.fugginnas.bak')


def build_file_manifest() -> list[dict]:
    """Return list of {path, content} dicts for every file the apply step will write."""
    state = read_state()
    files = []

    # /etc/snapraid.conf
    if state.get("backend") == "snapraid":
        conf = generate_conf(
            parity_disks=state.get("snapraid_parity_disks", []),
            data_mounts=state.get("snapraid_data_mounts", []),
            parity_mode=state.get("snapraid_parity_mode", "single"),
        )
        files.append({"path": "/etc/snapraid.conf", "content": conf})

    # /etc/fstab additions (mergerfs mount)
    if state.get("pool_mount"):
        sources = [state["cache_mount"]] + state.get("data_mounts", [])
        fstab_line = build_mount_string(
            sources=sources,
            target=state["pool_mount"],
            write_policy=state.get("write_policy", "mfs"),
        )
        files.append({"path": "/etc/fstab", "content": fstab_line})

    # /usr/local/bin/FugginNAS-mover.sh
    if state.get("cache_mount") and state.get("pool_mount"):
        script = generate_mover_script(
            cache_mount=state["cache_mount"],
            pool_mount=state["pool_mount"],
            age_hours=state.get("mover_age_hours", 24),
            min_free_pct=state.get("mover_min_free_pct", 20),
        )
        files.append({"path": "/usr/local/bin/FugginNAS-mover.sh", "content": script})

    # /etc/samba/smb.conf and /etc/exports
    smb_blocks, nfs_lines = [], []
    for share in state.get("shares", []):
        if share["protocol"] in ("smb", "both"):
            smb_blocks.append(generate_smb_block(
                name=share["name"], path=share["path"],
                guest_ok=share.get("smb_guest_ok", True),
                username=share.get("smb_username", ""),
                password=share.get("smb_password", ""),
            ))
        if share["protocol"] in ("nfs", "both"):
            nfs_lines.append(generate_export_line(
                path=share["path"],
                allowed_hosts=share.get("nfs_allowed_hosts", "192.168.0.0/16"),
                readonly=share.get("nfs_readonly", False),
            ))
    if smb_blocks:
        files.append({"path": "/etc/samba/smb.conf", "content": "\n".join(smb_blocks)})
    if nfs_lines:
        files.append({"path": "/etc/exports", "content": "\n".join(nfs_lines)})

    return files


def apply_all() -> list[str]:
    """Write every file from the manifest to disk. Returns list of written paths."""
    manifest = build_file_manifest()
    written = []
    for entry in manifest:
        if entry["path"] == "/etc/fstab":
            backup_fstab("/etc/fstab")
        path = Path(entry["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry["content"])
        written.append(entry["path"])
    return written
