from pathlib import Path


def _hhmm_to_calendar(hhmm: str) -> str:
    """Convert HH:MM string to systemd OnCalendar value (daily at that time)."""
    return f"*-*-* {hhmm}:00"


def _scrub_calendar(schedule: str) -> str:
    if schedule == "monthly":
        return "*-*-01 04:00:00"
    return "Mon *-*-* 04:00:00"  # weekly, Monday


def snapraid_sync_units(sync_time: str) -> dict[str, str]:
    calendar = _hhmm_to_calendar(sync_time)
    timer = f"""[Unit]
Description=SnapRAID daily sync

[Timer]
OnCalendar={calendar}
Persistent=true

[Install]
WantedBy=timers.target
"""
    service = """[Unit]
Description=SnapRAID sync
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/snapraid sync
StandardOutput=append:/var/log/snapraid-sync.log
StandardError=append:/var/log/snapraid-sync.log
"""
    return {
        "snapraid-sync.timer": timer,
        "snapraid-sync.service": service,
    }


def snapraid_scrub_units(schedule: str) -> dict[str, str]:
    calendar = _scrub_calendar(schedule)
    timer = f"""[Unit]
Description=SnapRAID scrub

[Timer]
OnCalendar={calendar}
Persistent=true

[Install]
WantedBy=timers.target
"""
    service = """[Unit]
Description=SnapRAID scrub
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/snapraid -p 5 -o oldest scrub
StandardOutput=append:/var/log/snapraid-scrub.log
StandardError=append:/var/log/snapraid-scrub.log
"""
    return {
        "snapraid-scrub.timer": timer,
        "snapraid-scrub.service": service,
    }


def mover_units(schedule_time: str) -> dict[str, str]:
    calendar = _hhmm_to_calendar(schedule_time)
    timer = f"""[Unit]
Description=FugginNAS cache mover

[Timer]
OnCalendar={calendar}
Persistent=true

[Install]
WantedBy=timers.target
"""
    service = """[Unit]
Description=FugginNAS cache mover
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/FugginNAS-mover.sh
StandardOutput=append:/var/log/FugginNAS-mover.log
StandardError=append:/var/log/FugginNAS-mover.log
"""
    return {
        "FugginNAS-mover.timer": timer,
        "FugginNAS-mover.service": service,
    }


def write_units(units: dict[str, str], unit_dir: str = "/etc/systemd/system") -> list[str]:
    """Write unit files to disk. Returns list of written paths."""
    written = []
    base = Path(unit_dir)
    base.mkdir(parents=True, exist_ok=True)
    for name, content in units.items():
        path = base / name
        path.write_text(content)
        written.append(str(path))
    return written
