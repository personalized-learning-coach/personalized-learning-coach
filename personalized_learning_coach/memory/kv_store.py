import json
from pathlib import Path
from threading import Lock

STORE_FILE = Path(__file__).parent / "store.json"
_lock = Lock()

def _load():
    if not STORE_FILE.exists():
        return {}
    return json.loads(STORE_FILE.read_text(encoding="utf-8"))

def _save(data):
    with _lock:
        STORE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def put(namespace: str, key: str, value):
    data = _load()
    data.setdefault(namespace, {})
    data[namespace][key] = value
    _save(data)

def get(namespace: str, key: str, default=None):
    data = _load()
    return data.get(namespace, {}).get(key, default)
