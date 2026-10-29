"""Tiny JSON file storage for Friday's memory, tasks and bills.

Everything lives in data/friday.json on your own machine. Nothing is sent
anywhere except the parts Claude needs to answer you.
"""

import json
import threading
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "friday.json"
_lock = threading.Lock()

EMPTY = {"memories": [], "tasks": [], "bills": []}


def _load() -> dict:
    if not DATA_FILE.exists():
        return json.loads(json.dumps(EMPTY))
    with DATA_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    for key, value in EMPTY.items():
        data.setdefault(key, list(value))
    return data


def _save(data: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(DATA_FILE)  # atomic: a crash never leaves a half-written file


def read() -> dict:
    with _lock:
        return _load()


def update(fn):
    """Run fn(data) under the lock, save, and return what fn returned."""
    with _lock:
        data = _load()
        result = fn(data)
        _save(data)
        return result


def new_id() -> str:
    return uuid.uuid4().hex[:6]
