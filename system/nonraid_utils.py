import json
import subprocess


class NonraidValidationError(ValueError):
    def __init__(self, error: str, *, valid: list[str] | None = None) -> None:
        super().__init__(error)
        self.error = error
        self.valid = valid


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


def build_nonraid_install_commands() -> list[list[str]]:
    return [
        ["apt-get", "install", "-y", "gpg"],
        [
            "bash", "-c",
            'wget -qO- "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x0B1768BC3340D235F3A5CB25186129DABB062BFD"'
            " | gpg --dearmor -o /usr/share/keyrings/nonraid-ppa.gpg",
        ],
        [
            "bash", "-c",
            'echo "deb [signed-by=/usr/share/keyrings/nonraid-ppa.gpg]'
            ' https://ppa.launchpadcontent.net/qvr/nonraid/ubuntu noble main"'
            " | tee /etc/apt/sources.list.d/nonraid-ppa.list",
        ],
        ["apt-get", "update"],
        ["apt-get", "install", "-y", "linux-headers-amd64", "nonraid-dkms", "nonraid-tools"],
    ]


def build_nonraid_create_operation() -> dict[str, str | list[str]]:
    return {
        "cmd": ["nmdctl", "create"],
        "done_msg": "Array created successfully",
        "error_msg": "ERROR (exit {returncode})",
    }


def resolve_nonraid_check_mode(payload_mode: str | None, state: dict) -> str:
    if payload_mode is not None:
        mode = payload_mode.upper()
        if mode not in {"CORRECT", "NOCORRECT"}:
            raise NonraidValidationError("mode must be CORRECT or NOCORRECT")
        return mode
    return "CORRECT" if state.get("nonraid_check_correct") else "NOCORRECT"


def build_nonraid_check_operation(mode: str) -> dict[str, str | list[str]]:
    return {
        "cmd": ["nmdctl", "check", mode],
        "done_msg": "Check complete (exit {returncode})",
        "error_msg": "Check complete (exit {returncode})",
    }


def build_nonraid_config_updates(data: dict) -> dict:
    valid_parity = {"single", "dual"}
    valid_fs = {"xfs", "btrfs", "ext4", "zfs"}

    parity_mode = data.get("parity_mode", "single")
    filesystem = data.get("filesystem", "xfs")
    luks = data.get("luks", False)
    turbo_write = data.get("turbo_write", False)
    check_schedule = data.get("check_schedule", "quarterly")
    check_correct = data.get("check_correct", False)
    check_speed_limit = data.get("check_speed_limit", 200)

    if parity_mode not in valid_parity:
        raise NonraidValidationError("invalid parity_mode")
    if filesystem not in valid_fs:
        raise NonraidValidationError("invalid filesystem", valid=sorted(valid_fs))
    if not isinstance(check_speed_limit, int) or not (10 <= check_speed_limit <= 1000):
        raise NonraidValidationError("check_speed_limit must be 10–1000 MB/s")

    return {
        "nonraid_parity_mode": parity_mode,
        "nonraid_filesystem": filesystem,
        "nonraid_luks": luks,
        "nonraid_turbo_write": turbo_write,
        "nonraid_check_schedule": check_schedule,
        "nonraid_check_correct": check_correct,
        "nonraid_check_speed_limit": check_speed_limit,
    }


def build_nonraid_roles_updates(parity_mode: str, parity_disks: list, data_disks: list) -> dict:
    expected = 2 if parity_mode == "dual" else 1
    if len(parity_disks) != expected:
        raise NonraidValidationError(f"parity_mode '{parity_mode}' requires exactly {expected} parity disk(s)")
    if not data_disks:
        raise NonraidValidationError("at least one data disk is required")
    if set(parity_disks) & set(data_disks):
        raise NonraidValidationError("a disk cannot be assigned both parity and data roles")
    return {
        "nonraid_parity_disks": parity_disks,
        "nonraid_data_disks": data_disks,
    }
