import shutil
from pathlib import Path

from system.mergerfs import build_mount_string
from system.mover import generate_mover_script
from system.nfs import generate_export_line
from system.samba import generate_smb_block
from system.snapraid_conf import generate_conf
from system.state import read_state
from system.systemd import (
    mover_units,
    snapraid_scrub_units,
    snapraid_sync_units,
)

_FSTAB_MARKER = "# FugginNAS mergerfs"


def backup_fstab(fstab_path: str) -> None:
    src = Path(fstab_path)
    if src.exists():
        shutil.copy2(src, str(src) + ".fugginnas.bak")


def _fstab_entry(state: dict) -> str:
    sources = [state["cache_mount"]] + state.get("data_mounts", [])
    line = build_mount_string(
        sources=sources,
        target=state["pool_mount"],
        write_policy=state.get("write_policy", "mfs"),
    )
    return f"{_FSTAB_MARKER}\n{line}\n"


def _append_or_update_fstab(fstab_path: str, entry: str) -> None:
    path = Path(fstab_path)
    existing = path.read_text() if path.exists() else ""
    if _FSTAB_MARKER in existing:
        lines = existing.splitlines(keepends=True)
        out = []
        skip_next = False
        for line in lines:
            if skip_next:
                skip_next = False
                continue
            if line.strip() == _FSTAB_MARKER.strip():
                out.append(entry)
                skip_next = True
            else:
                out.append(line)
        path.write_text("".join(out))
    else:
        with open(path, "a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(entry)


def build_file_manifest_for_state(state: dict) -> list[dict]:
    """Return list of {path, content} dicts for every file the apply step will write."""
    files = []

    if state.get("backend") == "snapraid":
        conf = generate_conf(
            parity_disks=state.get("snapraid_parity_disks", []),
            data_mounts=state.get("snapraid_data_mounts", []),
            parity_mode=state.get("snapraid_parity_mode", "single"),
        )
        files.append({"path": "/etc/snapraid.conf", "content": conf})

        sync_time = state.get("snapraid_sync_time", "02:00")
        for name, content in snapraid_sync_units(sync_time).items():
            files.append({"path": f"/etc/systemd/system/{name}", "content": content})

        scrub_schedule = state.get("snapraid_scrub_schedule", "weekly")
        if scrub_schedule != "off":
            for name, content in snapraid_scrub_units(scrub_schedule).items():
                files.append({"path": f"/etc/systemd/system/{name}", "content": content})

    if state.get("backend") == "nonraid":
        speed_mb = state.get("nonraid_check_speed_limit", 200)
        speed_kb = speed_mb * 1024
        sysctl_content = (
            "# FugginNAS NonRAID — parity check speed limit\n"
            f"dev.raid.speed_limit_max = {speed_kb}\n"
            f"dev.raid.speed_limit_min = {min(speed_kb, 1000)}\n"
        )
        files.append({"path": "/etc/sysctl.d/99-nonraid.conf", "content": sysctl_content})

    if state.get("pool_mount"):
        files.append({
            "path": "/etc/fstab",
            "content": _fstab_entry(state),
        })

    if state.get("cache_mount") and state.get("pool_mount"):
        script = generate_mover_script(
            cache_mount=state["cache_mount"],
            pool_mount=state["pool_mount"],
            age_hours=state.get("mover_age_hours", 24),
            min_free_pct=state.get("mover_min_free_pct", 20),
        )
        files.append({"path": "/usr/local/bin/FugginNAS-mover.sh", "content": script})

        mover_time = state.get("mover_schedule_time", "03:00")
        for name, content in mover_units(mover_time).items():
            files.append({"path": f"/etc/systemd/system/{name}", "content": content})

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


def build_file_manifest() -> list[dict]:
    """Compatibility wrapper that reads state from disk before building manifest."""
    return build_file_manifest_for_state(read_state())


def apply_all() -> list[str]:
    """Write every file from the manifest to disk. Returns list of written paths."""
    manifest = build_file_manifest()
    written = []
    for entry in manifest:
        path_str = entry["path"]
        content = entry["content"]
        if path_str == "/etc/fstab":
            backup_fstab("/etc/fstab")
            _append_or_update_fstab("/etc/fstab", content)
        else:
            path = Path(path_str)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        written.append(path_str)
    return written
