import json
import os
from pathlib import Path


def _state_path() -> Path:
    return Path(os.environ.get("FUGGINNAS_STATE", "state/state.json"))


def read_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def write_state(updates: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state = read_state()
    state.update(updates)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(path)
