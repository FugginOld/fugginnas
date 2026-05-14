import json
import subprocess


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def nmdctl_status() -> dict:
    result = _run(["nmdctl", "status", "-o", "json"])
    if result.returncode != 0:
        return {"error": result.stderr.strip(), "state": "UNKNOWN"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid json from nmdctl", "raw": result.stdout}


def nmdctl_start() -> tuple[bool, str]:
    result = _run(["nmdctl", "start"])
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def nmdctl_stop() -> tuple[bool, str]:
    result = _run(["nmdctl", "stop"])
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def nmdctl_mount(prefix: str = "/mnt/disk") -> tuple[bool, str]:
    result = _run(["nmdctl", "mount", prefix])
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def nmdctl_unmount() -> tuple[bool, str]:
    result = _run(["nmdctl", "unmount"])
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def nmdctl_check(mode: str = "NOCORRECT") -> subprocess.Popen:
    """Return a Popen process for streaming nmdctl check output via SSE."""
    return subprocess.Popen(
        ["nmdctl", "check", mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def parse_nmdstat() -> dict:
    """Parse /proc/nmdstat for check progress."""
    try:
        with open("/proc/nmdstat") as f:
            lines = f.read().splitlines()
    except OSError:
        return {}
    data = {}
    for line in lines:
        if "=" in line:
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip()
    return data


def is_nonraid_installed() -> bool:
    result = _run(["dkms", "status"])
    return "nonraid" in result.stdout.lower()
