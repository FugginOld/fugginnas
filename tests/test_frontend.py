import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FUGGINNAS_STATE", str(tmp_path / "state.json"))
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# --- GET / ---

def test_get_root_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_get_root_contains_app_div(client):
    resp = client.get("/")
    assert b'<div id="app">' in resp.data


def test_get_root_links_app_js(client):
    resp = client.get("/")
    assert b"app.js" in resp.data


def test_get_root_links_style_css(client):
    resp = client.get("/")
    assert b"style.css" in resp.data


# --- Static files ---

def test_get_static_app_js_returns_200(client):
    resp = client.get("/static/app.js")
    assert resp.status_code == 200


def test_get_static_style_css_returns_200(client):
    resp = client.get("/static/style.css")
    assert resp.status_code == 200


# --- app.js content ---

def test_app_js_has_hash_router(client):
    resp = client.get("/static/app.js")
    assert b"hashchange" in resp.data


def test_app_js_has_backend_screen_options(client):
    resp = client.get("/static/app.js")
    assert b"snapraid" in resp.data
    assert b"nonraid" in resp.data
    assert b"mergerfs" in resp.data


def test_app_js_posts_to_api_backend(client):
    resp = client.get("/static/app.js")
    assert b"/api/backend" in resp.data


def test_app_js_has_drives_screen(client):
    resp = client.get("/static/app.js")
    assert b"/api/drives" in resp.data


def test_app_js_drive_table_has_role_selector(client):
    resp = client.get("/static/app.js")
    assert b"cache" in resp.data
    assert b"parity" in resp.data
    assert b"data-drive" in resp.data


# --- Pool screen ---

def test_app_js_pool_screen_has_step_4(client):
    resp = client.get("/static/app.js")
    assert b"Step 4" in resp.data


def test_app_js_pool_has_write_policy_input(client):
    resp = client.get("/static/app.js")
    assert b"write-policy" in resp.data


def test_app_js_pool_navigates_to_snapraid(client):
    resp = client.get("/static/app.js")
    assert b"#snapraid" in resp.data


# --- SnapRAID screen ---

def test_app_js_snapraid_screen_has_step_5(client):
    resp = client.get("/static/app.js")
    assert b"Step 5" in resp.data


def test_app_js_snapraid_posts_to_api(client):
    resp = client.get("/static/app.js")
    assert b"/api/snapraid" in resp.data


def test_app_js_snapraid_has_scrub_schedule(client):
    resp = client.get("/static/app.js")
    assert b"scrub_schedule" in resp.data


def test_app_js_snapraid_navigates_to_mover(client):
    resp = client.get("/static/app.js")
    assert b"#mover" in resp.data


# --- Mover screen ---

def test_app_js_mover_screen_has_step_6(client):
    resp = client.get("/static/app.js")
    assert b"Step 6" in resp.data


def test_app_js_mover_posts_to_api(client):
    resp = client.get("/static/app.js")
    assert b"/api/mover" in resp.data


def test_app_js_mover_has_age_hours(client):
    resp = client.get("/static/app.js")
    assert b"age_hours" in resp.data


def test_app_js_mover_navigates_to_shares(client):
    resp = client.get("/static/app.js")
    assert b"#shares" in resp.data


# --- Shares screen ---

def test_app_js_shares_screen_has_step_7(client):
    resp = client.get("/static/app.js")
    assert b"Step 7" in resp.data


def test_app_js_shares_posts_to_api(client):
    resp = client.get("/static/app.js")
    assert b"/api/shares" in resp.data


def test_app_js_shares_has_protocol_selector(client):
    resp = client.get("/static/app.js")
    assert b"smb" in resp.data
    assert b"nfs" in resp.data


def test_app_js_shares_navigates_to_summary(client):
    resp = client.get("/static/app.js")
    assert b"#summary" in resp.data


# --- Summary screen ---

def test_app_js_summary_screen_has_step_8(client):
    resp = client.get("/static/app.js")
    assert b"Step 8" in resp.data


def test_app_js_summary_fetches_api(client):
    resp = client.get("/static/app.js")
    assert b"/api/summary" in resp.data


def test_app_js_summary_navigates_to_status(client):
    resp = client.get("/static/app.js")
    assert b"#status" in resp.data


# --- Status screen ---

def test_app_js_status_screen_has_dashboard(client):
    resp = client.get("/static/app.js")
    assert b"Dashboard" in resp.data


def test_app_js_status_fetches_api(client):
    resp = client.get("/static/app.js")
    assert b"/api/status" in resp.data


# --- NonRAID screen ---

def test_app_js_has_nonraid_screen(client):
    resp = client.get("/static/app.js")
    assert b"#nonraid" in resp.data


def test_app_js_nonraid_posts_to_api(client):
    resp = client.get("/static/app.js")
    assert b"/api/nonraid" in resp.data


# --- Welcome screen ---

def test_app_js_has_welcome_route(client):
    resp = client.get("/static/app.js")
    assert b"'welcome'" in resp.data


def test_app_js_welcome_has_start_button(client):
    resp = client.get("/static/app.js")
    assert b"Start Setup" in resp.data


# --- MergerFS navigation path ---

def test_app_js_pool_checks_state_backend(client):
    resp = client.get("/static/app.js")
    assert b"_state.backend" in resp.data
