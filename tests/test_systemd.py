from system.systemd import (
    mover_units,
    snapraid_scrub_units,
    snapraid_sync_units,
    write_units,
)


def test_sync_timer_contains_calendar():
    units = snapraid_sync_units("02:00")
    timer = units["snapraid-sync.timer"]
    assert "OnCalendar=*-*-* 02:00:00" in timer


def test_sync_timer_custom_time():
    units = snapraid_sync_units("04:30")
    assert "OnCalendar=*-*-* 04:30:00" in units["snapraid-sync.timer"]


def test_sync_service_calls_snapraid_sync():
    units = snapraid_sync_units("02:00")
    assert "snapraid sync" in units["snapraid-sync.service"]


def test_sync_service_logs_to_file():
    units = snapraid_sync_units("02:00")
    assert "snapraid-sync.log" in units["snapraid-sync.service"]


def test_scrub_timer_weekly():
    units = snapraid_scrub_units("weekly")
    assert "Mon *-*-*" in units["snapraid-scrub.timer"]


def test_scrub_timer_monthly():
    units = snapraid_scrub_units("monthly")
    assert "*-*-01" in units["snapraid-scrub.timer"]


def test_scrub_service_calls_snapraid_scrub():
    units = snapraid_scrub_units("weekly")
    assert "snapraid" in units["snapraid-scrub.service"]
    assert "scrub" in units["snapraid-scrub.service"]


def test_mover_timer_contains_calendar():
    units = mover_units("03:00")
    assert "OnCalendar=*-*-* 03:00:00" in units["FugginNAS-mover.timer"]


def test_mover_service_calls_mover_script():
    units = mover_units("03:00")
    assert "FugginNAS-mover.sh" in units["FugginNAS-mover.service"]


def test_write_units_creates_files(tmp_path):
    units = {"test.timer": "[Timer]\nOnCalendar=daily\n"}
    written = write_units(units, unit_dir=str(tmp_path))
    assert len(written) == 1
    assert (tmp_path / "test.timer").exists()
    assert "OnCalendar=daily" in (tmp_path / "test.timer").read_text()


def test_write_units_returns_paths(tmp_path):
    units = {"a.timer": "a", "a.service": "b"}
    written = write_units(units, unit_dir=str(tmp_path))
    assert len(written) == 2
