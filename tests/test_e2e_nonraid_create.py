"""
Browser E2E test — full NonRAID create flow.

Drives the SPA through:
  Welcome → Backend → Drives → Pool → NonRAID config →
  NonRAID roles → NonRAID prep (assertions + checkbox gate)
  → Mover (confirming navigation succeeds)

Run locally:
  pip install -r requirements.txt
  playwright install chromium
  pytest tests/test_e2e_nonraid_create.py -v

Not wired into CI — requires a Chromium install.
Skipped automatically when Playwright browsers are not available.
"""
import json
import os
import socket
import threading
import time

import pytest


def _chromium_available() -> bool:
    try:
        import os
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        path = p.chromium.executable_path
        p.stop()
        return os.path.exists(path)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium not installed — run: playwright install chromium",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


FAKE_DRIVES = {
    "drives": [
        {
            "name": "sdb",
            "size": 4_000_000_000_000,
            "model": "FakeParityDisk",
            "mountpoint": None,
            "fstype": None,
            "type": "disk",
        },
        {
            "name": "sdc",
            "size": 2_000_000_000_000,
            "model": "FakeDataDisk",
            "mountpoint": None,
            "fstype": None,
            "type": "disk",
        },
    ]
}


# ---------------------------------------------------------------------------
# Live Flask server fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    state_dir = tmp_path_factory.mktemp("e2e_state")
    state_file = state_dir / "state.json"

    os.environ["FUGGINNAS_STATE"] = str(state_file)

    from app import create_app

    flask_app = create_app()

    def _run():
        flask_app.run(host="127.0.0.1", port=_port, use_reloader=False, threaded=True)

    _port = _free_port()
    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # Wait up to 3 s for the server to accept connections
    import urllib.request
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{_port}/", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)

    yield f"http://127.0.0.1:{_port}"


# ---------------------------------------------------------------------------
# Route-mock helpers (GET-only intercept; POSTs fall through to Flask)
# ---------------------------------------------------------------------------

def _mock_get(route, body_dict):
    if route.request.method == "GET":
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(body_dict),
        )
    else:
        route.continue_()


# ---------------------------------------------------------------------------
# E2E test
# ---------------------------------------------------------------------------

def test_nonraid_create_flow(live_server, page):
    """Walk the full NonRAID wizard to the prep screen and verify gate logic."""

    # Mock system-dependent GET endpoints
    page.route("**/api/drives", lambda r: _mock_get(r, FAKE_DRIVES))
    page.route(
        "**/api/nonraid/install",
        lambda r: _mock_get(r, {"installed": True}),
    )
    page.route(
        "**/api/theme",
        lambda r: _mock_get(r, {"theme": "default"}),
    )

    # ── 1. Welcome ────────────────────────────────────────────────────────────
    page.goto(live_server)
    page.wait_for_selector("#btn-start")
    page.click("#btn-start")

    # ── 2. Backend — select NonRAID ───────────────────────────────────────────
    page.wait_for_selector('input[name="backend"][value="nonraid"]')
    page.click('input[name="backend"][value="nonraid"]')
    page.click("#btn-next")

    # ── 3. Drives — assign sdb → parity, sdc → data ───────────────────────────
    page.wait_for_selector('select[data-drive="sdb"]')
    page.select_option('select[data-drive="sdb"]', "parity")
    page.select_option('select[data-drive="sdc"]', "data")
    page.click("#btn-next")

    # ── 4. Pool — accept defaults ─────────────────────────────────────────────
    page.wait_for_selector("#pool-mount")
    page.click("#btn-next")

    # ── 5. NonRAID config — defaults (xfs, single parity) ────────────────────
    page.wait_for_selector("#parity-mode")
    # Verify the install badge shows NonRAID as installed
    assert page.locator(".status-badge.ok").count() > 0, "Expected NonRAID installed badge"
    page.click("#btn-next")

    # ── 6. NonRAID roles — assign sdb → parity, sdc → data ───────────────────
    page.wait_for_selector("#role-sdb")
    page.select_option("#role-sdb", "parity")
    page.select_option("#role-sdc", "data")
    page.click("#btn-next")

    # ── 7. NonRAID prep screen ────────────────────────────────────────────────
    page.wait_for_selector("#prep-done")
    content = page.content()

    # Parity disk commands
    assert "sgdisk --zap-all /dev/sdb" in content, "Missing parity sgdisk zap"
    assert "sgdisk -n 1:0:0 -t 1:fd00 /dev/sdb" in content, "Missing parity sgdisk partition"

    # Data disk commands
    assert "sgdisk --zap-all /dev/sdc" in content, "Missing data sgdisk zap"
    assert "sgdisk -n 1:0:0 -t 1:8300 /dev/sdc" in content, "Missing data sgdisk partition"
    assert "mkfs.xfs -f /dev/sdc1" in content, "Missing mkfs command for data disk"

    # nmdctl create guidance
    assert "nmdctl create" in content, "Missing nmdctl create instruction"

    # ── 8. Checkbox gates Proceed button ─────────────────────────────────────
    proceed = page.locator("#btn-next")
    assert proceed.is_disabled(), "Proceed button should be disabled before checkbox"

    page.check("#prep-done")
    assert not proceed.is_disabled(), "Proceed button should be enabled after checkbox"

    # ── 9. Proceed → Mover screen ─────────────────────────────────────────────
    page.click("#btn-next")
    page.wait_for_selector("#schedule-time")  # mover screen landmark
    assert page.url.endswith("#mover"), f"Expected #mover URL, got: {page.url}"
