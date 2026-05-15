import json
import os
from pathlib import Path

DEFAULT_THEME = "default"
KNOWN_STATE_KEYS = {
    "backend",
    "pool_mount",
    "cache_mount",
    "data_mounts",
    "write_policy",
    "snapraid_parity_mode",
    "snapraid_parity_disks",
    "snapraid_data_mounts",
    "snapraid_sync_time",
    "snapraid_scrub_schedule",
    "mover_schedule_time",
    "mover_age_hours",
    "mover_min_free_pct",
    "shares",
    "theme",
    "nonraid_parity_mode",
    "nonraid_filesystem",
    "nonraid_luks",
    "nonraid_turbo_write",
    "nonraid_check_schedule",
    "nonraid_check_correct",
    "nonraid_check_speed_limit",
    "nonraid_parity_disks",
    "nonraid_data_disks",
}


def _state_path() -> Path:
    return Path(os.environ.get("FUGGINNAS_STATE", "state/state.json"))


def read_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _write_state_internal(updates: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state = read_state()
    state.update(updates)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(path)


def write_state(updates: dict) -> None:
    _write_state_internal(updates)


def write_known_state(updates: dict) -> None:
    unknown = sorted(k for k in updates.keys() if k not in KNOWN_STATE_KEYS)
    if unknown:
        raise ValueError(f"unknown state key(s): {', '.join(unknown)}")
    _write_state_internal(updates)


def get_theme(state: dict) -> str:
    value = state.get("theme")
    return value if isinstance(value, str) and value else DEFAULT_THEME


def get_backend(state: dict) -> str | None:
    value = state.get("backend")
    return value if isinstance(value, str) and value else None
