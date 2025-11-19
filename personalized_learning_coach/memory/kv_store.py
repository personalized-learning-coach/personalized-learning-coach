"""
personalized_learning_coach.memory.kv_store

File-backed key-value store with simple session event append & compaction helpers.

- store.json layout: { "<namespace>": { "<key>": <value> } }
- sessions are stored under namespace "session:<user_id>"
- append_event(session_namespace, event) appends to events list
- compact_session(session_namespace, keep_last=5) summarizes and keeps last N events

This file is intentionally simple and synchronous (for prototyping).
"""
import json
from pathlib import Path
from threading import Lock
from datetime import datetime
from typing import Any, Dict, List

BASE = Path(__file__).parent
STORE_FILE = BASE / "store.json"
_lock = Lock()


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _load() -> Dict[str, Any]:
    if not STORE_FILE.exists():
        return {}
    try:
        return json.loads(STORE_FILE.read_text(encoding="utf-8"))
    except Exception:
        # if file corrupted, start fresh (safe for demo)
        return {}


def _save(data: Dict[str, Any]) -> None:
    with _lock:
        STORE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def put(namespace: str, key: str, value: Any) -> None:
    data = _load()
    data.setdefault(namespace, {})
    data[namespace][key] = value
    _save(data)


def get(namespace: str, key: str = None, default=None):
    """
    Get a value from the store.

    - If key is None or key == "", return the entire namespace dict (e.g., the whole session).
    - Otherwise, return the value stored under namespace[key] or default.
    """
    data = _load()
    ns = data.get(namespace, {})
    if key is None or key == "":
        return ns or default
    return ns.get(key, default)


def query_prefix(namespace: str, prefix: str) -> Dict[str, Any]:
    data = _load()
    ns = data.get(namespace, {})
    return {k: v for k, v in ns.items() if k.startswith(prefix)}


# ---- Session helpers ----
def append_event(session_namespace: str, event: Dict[str, Any]) -> None:
    """
    Append an event to a session stored under `session_namespace` (e.g. "session:user123").
    The session is stored as a dict with keys: session_id, events (list), state (dict), created_at.
    """
    data = _load()
    session = data.get(session_namespace, {})
    # initialize if missing
    if not session:
        session = {
            "session_id": session_namespace,
            "created_at": _now_iso(),
            "events": [],
            "state": {},
        }
    # event enrichment
    event = dict(event)  # shallow copy
    event.setdefault("event_id", f"evt-{int(datetime.utcnow().timestamp()*1000)}")
    event.setdefault("timestamp", _now_iso())
    session.setdefault("events", []).append(event)
    # optionally update last_seen or other quick state aspects
    session["state"]["last_event_ts"] = event["timestamp"]
    data[session_namespace] = session
    _save(data)


def compact_session(session_namespace: str, keep_last: int = 5) -> Dict[str, Any]:
    """
    Compact a session by:
    - keeping only the last `keep_last` events in full
    - producing a short_summary (concatenate truncated recent user messages)
    - storing the summary in session.state['short_summary']
    Returns the updated session object.
    """
    data = _load()
    session = data.get(session_namespace, {})
    if not session:
        return {}

    events: List[Dict[str, Any]] = session.get("events", [])
    if not events:
        return session

    # Keep only last N events
    kept = events[-keep_last:] if keep_last > 0 else []
    # Build a short summary: collect user-role text fields from kept events
    user_texts: List[str] = []
    for e in kept:
        role = e.get("role", "")
        content = e.get("content", {})
        text = ""
        if isinstance(content, dict):
            text = content.get("text", "")
        else:
            text = str(content)
        if role == "user" and text:
            user_texts.append(text.strip())

    # Simple summarization: join last user utterances separated by " | "
    short_summary = " | ".join(user_texts[-3:])  # at most last 3 user utterances

    # update session structure
    session["events"] = kept
    session.setdefault("state", {})
    session["state"]["short_summary"] = short_summary
    session["state"]["compacted_at"] = _now_iso()
    data[session_namespace] = session
    _save(data)
    return session


# Small helper to reset a namespace (useful for tests)
def _reset_store():
    _save({})


if __name__ == "__main__":
    # quick manual demo
    _reset_store()
    ns = "session:demo"
    append_event(ns, {"role": "user", "type": "utterance", "content": {"text": "I want to learn fractions"}})
    append_event(ns, {"role": "agent", "type": "action", "content": {"text": "Starting assessment"}})
    append_event(ns, {"role": "user", "type": "utterance", "content": {"text": "I struggle with simplifying fractions"}})
    print("Before compact:", get(ns, ""))
    s = compact_session(ns, keep_last=2)
    print("After compact:", json.dumps(s, indent=2))