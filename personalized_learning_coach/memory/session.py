# personalized_learning_coach/memory/session.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from personalized_learning_coach.memory import kv_store

class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._ensure_exists()

    def _ensure_exists(self):
        data = kv_store.get(self.session_id)
        if not data:
            kv_store.put(self.session_id, "events", [])
            kv_store.put(self.session_id, "state", {})
            self.add_event("system", "Session started", event_type="system")

    def add_event(self, role: str, content: Any, event_type: str = "utterance"):
        event = {"role": role, "type": event_type, "content": content, "timestamp": datetime.utcnow().isoformat()+"Z"}
        append = getattr(kv_store, "append_event", None)
        try:
            if callable(append):
                append(self.session_id, event)
                return
        except Exception:
            pass
        sess = kv_store.get(self.session_id) or {"events": [], "state": {}}
        events = sess.get("events") or []
        events.append(event)
        kv_store.put(self.session_id, "events", events)

    def get_events(self) -> List[Dict[str, Any]]:
        data = kv_store.get(self.session_id) or {}
        return data.get("events") or []

    def get_last_event(self) -> Optional[Dict[str, Any]]:
        events = self.get_events()
        return events[-1] if events else None

    def get_state(self) -> Dict[str, Any]:
        data = kv_store.get(self.session_id) or {}
        return data.get("state") or {}

    def update_state(self, key: str, value: Any):
        state = self.get_state()
        state[key] = value
        kv_store.put(self.session_id, "state", state)

    def compact(self, keep_last: int = 10):
        fn = getattr(kv_store, "compact_session", None)
        if callable(fn):
            fn(self.session_id, keep_last=keep_last)
            return
        events = self.get_events()
        if len(events) <= keep_last:
            return
        kv_store.put(self.session_id, "events", events[-keep_last:])