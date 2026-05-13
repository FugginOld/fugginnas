import subprocess
from system.state import read_state


def _df_usage(mount: str) -> dict:
    """Return used_pct and available_bytes for a mount point."""
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


def get_status() -> dict:
    state = read_state()
    pool_mount = state.get("pool_mount", "/mnt/pool")
    cache_mount = state.get("cache_mount", "/mnt/cache")

    pool_usage = _df_usage(pool_mount)
    cache_usage = _df_usage(cache_mount)

    return {
        "backend": state.get("backend"),
        "pool": {
            "mount": pool_mount,
            "used_pct": pool_usage["used_pct"],
            "available_bytes": pool_usage["available_bytes"],
        },
        "cache_fill_pct": cache_usage["used_pct"],
        "shares": state.get("shares", []),
    }
