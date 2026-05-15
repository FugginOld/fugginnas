import json
import pytest

from system.state import KNOWN_STATE_KEYS, get_backend, get_theme, write_known_state, write_state


def test_get_theme_default_when_missing():
    assert get_theme({}) == "default"


def test_get_theme_returns_valid_string():
    assert get_theme({"theme": "nord"}) == "nord"


def test_get_theme_ignores_non_string_values():
    assert get_theme({"theme": 123}) == "default"


def test_get_backend_missing_returns_none():
    assert get_backend({}) is None


def test_get_backend_returns_string():
    assert get_backend({"backend": "snapraid"}) == "snapraid"


def test_get_backend_ignores_non_string_values():
    assert get_backend({"backend": 7}) is None


def test_write_state_merges_updates(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_file))
    write_state({"theme": "default"})
    write_state({"backend": "mergerfs"})
    state = json.loads(state_file.read_text())
    assert state["theme"] == "default"
    assert state["backend"] == "mergerfs"


def test_write_known_state_accepts_known_keys(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_file))
    write_known_state({"theme": "nord", "backend": "snapraid"})
    state = json.loads(state_file.read_text())
    assert state["theme"] == "nord"
    assert state["backend"] == "snapraid"


def test_write_known_state_rejects_unknown_keys(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("FUGGINNAS_STATE", str(state_file))
    with pytest.raises(ValueError):
        write_known_state({"bogus": True})


def test_known_state_keys_cover_migrated_route_writer_keys():
    migrated_route_keys = {
        "theme",
        "backend",
        "mover_schedule_time",
        "mover_age_hours",
        "mover_min_free_pct",
        "shares",
    }
    assert migrated_route_keys.issubset(KNOWN_STATE_KEYS)
