# personalized_learning_coach/memory/kv_store.py
"""Simple Key-Value Store for persistence."""
import json
import tempfile
from pathlib import Path
from threading import Lock
from datetime import datetime
from typing import Any, Dict, Optional

BASE = Path(__file__).parent
STORE_FILE = BASE / "store.json"
_lock = Lock()

def _now_iso():
    return datetime.utcnow().isoformat() + "Z"

def _ensure_dir():
    try:
        BASE.mkdir(parents=True, exist_ok=True)
    except Exception: # pylint: disable=broad-exception-caught
        pass

def _load() -> Dict[str, Any]:
    with _lock:
        if not STORE_FILE.exists():
            return {}
        try:
            txt = STORE_FILE.read_text(encoding="utf-8")
            return json.loads(txt) if txt.strip() else {}
        except Exception: # pylint: disable=broad-exception-caught
            return {}

def _atomic_write(path: Path, data: str):
    _ensure_dir()
    dirp = path.parent
    with tempfile.NamedTemporaryFile("w", dir=str(dirp), delete=False, encoding="utf-8") as tf:
        tf.write(data)
        tmp = tf.name
    Path(tmp).replace(path)

def _save(d: Dict[str, Any]):
    with _lock:
        payload = json.dumps(d, indent=2, ensure_ascii=False)
        _atomic_write(STORE_FILE, payload)

def put(namespace: str, key: str, value: Any) -> None:
    """Store a value in the KV store."""
    data = _load()
    data.setdefault(namespace, {})
    data[namespace][key] = value
    _save(data)

def get(namespace: str, key: Optional[str] = None, default: Any = None) -> Any:
    """Retrieve a value from the KV store."""
    data = _load()
    ns = data.get(namespace)
    if ns is None:
        return default
    if key is None or key == "":
        return ns
    return ns.get(key, default)

def query_prefix(namespace: str, prefix: str):
    """Query keys starting with a prefix."""
    data = _load()
    ns = data.get(namespace, {})
    return {k:v for k,v in ns.items() if k.startswith(prefix)}

def append_event(session_namespace: str, event: Dict[str, Any]) -> None:
    """Append an event to a session."""
    data = _load()
    session = data.get(session_namespace)
    if not session:
        session = {
            "session_id": session_namespace,
            "created_at": _now_iso(),
            "events": [],
            "state": {}
        }
    session.setdefault("events", [])
    session.setdefault("state", {})
    ev = dict(event)
    ev.setdefault("event_id", f"evt-{int(datetime.utcnow().timestamp()*1000)}")
    ev.setdefault("timestamp", _now_iso())
    session["events"].append(ev)
    session["state"]["last_event_ts"] = ev["timestamp"]
    data[session_namespace] = session
    _save(data)

def compact_session(session_namespace: str, keep_last: int = 5):
    """Compact session history."""
    data = _load()
    session = data.get(session_namespace, {})
    if not session:
        return {}
    events = session.get("events", [])
    kept = events[-keep_last:] if keep_last > 0 else []
    user_texts = []
    for e in kept:
        role = e.get("role","")
        content = e.get("content",{})
        text = ""
        if isinstance(content, dict):
            text = content.get("text","") or content.get("message","")
        else:
            text = str(content or "")
        if role == "user" and text:
            user_texts.append(text.strip())
    short_summary = " | ".join(user_texts[-3:])
    session["events"] = kept
    session.setdefault("state", {})
    session["state"]["short_summary"] = short_summary
    session["state"]["compacted_at"] = _now_iso()
    data[session_namespace] = session
    _save(data)
    return session

def _reset_store():
    _save({})