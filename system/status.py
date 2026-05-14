import re
import subprocess
from pathlib import Path

from system.state import read_state

_SYNC_LOG = "/var/log/snapraid-sync.log"
_SCRUB_LOG = "/var/log/snapraid-scrub.log"


def _df_usage(mount: str) -> dict:
    try:
        result = subprocess.run(
            ["df", "-B1", "--output=used,avail,pcent", mount],
            capture_output=True, text=True, check=False,
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            return {"used_pct": None, "available_bytes": None}
        parts = lines[1].split()
        used_pct = int(parts[2].rstrip("%"))
        available_bytes = int(parts[1])
        return {"used_pct": used_pct, "available_bytes": available_bytes}
    except Exception:
        return {"used_pct": None, "available_bytes": None}


def _is_mounted(path: str) -> bool:
    try:
        with open("/proc/mounts") as f:
            return any(line.split()[1] == path for line in f if len(line.split()) >= 2)
    except OSError:
        return False


def _parse_snapraid_log(log_path: str) -> dict:
    """Extract last run time, result, and error count from a snapraid log."""
    path = Path(log_path)
    if not path.exists():
        return {"last_run": None, "result": None, "errors": None}
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return {"last_run": None, "result": None, "errors": None}

    last_run = None
    result = None
    errors = None

    for line in reversed(text.splitlines()):
        if last_run is None:
            m = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line)
            if m:
                last_run = m.group(0)
        if result is None and ("completed" in line.lower() or "error" in line.lower()):
            result = line.strip()
        if errors is None:
            m = re.search(r"(\d+)\s+error", line, re.IGNORECASE)
            if m:
                errors = int(m.group(1))
        if last_run and result and errors is not None:
            break

    return {"last_run": last_run, "result": result, "errors": errors or 0}


def _snapraid_dirty_count() -> int | None:
    """Run snapraid diff --count-only and return number of changed files."""
    try:
        result = subprocess.run(
            ["snapraid", "diff"],
            capture_output=True, text=True, timeout=30,
        )
        m = re.search(r"(\d+)\s+(?:add|remove|update|move|copy|restore)", result.stdout)
        if m:
            total = sum(
                int(x) for x in re.findall(
                    r"(\d+)\s+(?:add|remove|update|move|copy|restore)", result.stdout
                )
            )
            return total
        return 0
    except Exception:
        return None


def get_status() -> dict:
    state = read_state()
    pool_mount = state.get("pool_mount", "/mnt/pool")
    cache_mount = state.get("cache_mount", "/mnt/cache")
    backend = state.get("backend")

    pool_usage = _df_usage(pool_mount)
    cache_usage = _df_usage(cache_mount)

    status: dict = {
        "backend": backend,
        "pool": {
            "mount": pool_mount,
            "mounted": _is_mounted(pool_mount),
            "used_pct": pool_usage["used_pct"],
            "available_bytes": pool_usage["available_bytes"],
        },
        "cache_fill_pct": cache_usage["used_pct"],
        "shares": state.get("shares", []),
    }

    if backend == "snapraid":
        status["snapraid"] = {
            "sync": _parse_snapraid_log(_SYNC_LOG),
            "scrub": _parse_snapraid_log(_SCRUB_LOG),
            "dirty_files": _snapraid_dirty_count(),
        }

    return status
