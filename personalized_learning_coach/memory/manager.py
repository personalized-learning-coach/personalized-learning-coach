"""Memory manager for the personalized learning coach.

Improvements made:
- Better typing and Optional usage
- Robust handling when kv_store operations fail
- Defensive checks for session API (get_events, session_id)
- Safer text extraction from events
- Logging for observability
- Cap stored memories to avoid unbounded growth
- Clearer docstrings and small helper methods
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from personalized_learning_coach.memory import kv_store
from personalized_learning_coach.memory.session import Session

logger = logging.getLogger(__name__)

# Maximum number of memories to keep per user to avoid unbounded growth.
MAX_MEMORIES = 1000


class MemoryManager:
    """Manages the 'filing cabinet' for long-term knowledge.

    Responsibilities:
    - store and retrieve simple memory items for a user
    - extract simple, rule-based insights from a Session object

    Note: This implementation is intentionally lightweight and synchronous.
    In production you might replace kv_store with a vector DB and run
    extraction via an LLM.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.namespace = f"memory:{user_id}"

    def _now_iso(self) -> str:
        # UTC timestamp with Z suffix for clarity
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _load_memories(self) -> List[Dict[str, Any]]:
        try:
            return kv_store.get(self.namespace, "items", default=[]) or []
        except Exception:
            logger.exception("Failed to load memories for %s", self.namespace)
            return []

    def _save_memories(self, memories: List[Dict[str, Any]]) -> None:
        # keep only the most recent MAX_MEMORIES (operate on a copy)
        try:
            to_store = memories[-MAX_MEMORIES:] if len(memories) > MAX_MEMORIES else list(memories)
            kv_store.put(self.namespace, "items", to_store)
        except Exception:
            logger.exception("Failed to save memories for %s", self.namespace)

    def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Adds a single memory item.

        Args:
            content: short text describing the memory.
            metadata: optional dictionary with extra fields (e.g. source_session)
        """
        if not content or not str(content).strip():
            # don't persist empty memories
            logger.debug("Skipping add_memory with empty content (user=%s)", self.user_id)
            return

        if metadata is None:
            metadata = {}

        memory_item: Dict[str, Any] = {
            "content": str(content).strip(),
            "metadata": metadata,
            "created_at": self._now_iso(),
        }

        memories = self._load_memories()
        memories.append(memory_item)
        self._save_memories(memories)

    def get_memories(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve memories, optionally filtered by a simple substring query.

        This is intentionally simple — in future replace with vector similarity.
        """
        memories = self._load_memories()
        if not query:
            return memories

        q = query.strip().lower()
        if not q:
            return memories

        filtered: List[Dict[str, Any]] = []
        for m in memories:
            content = (m.get("content") or "").lower()
            if q in content:
                filtered.append(m)
        return filtered

    def extract_from_session(self, session: Session) -> List[str]:
        """Extracts simple insights from a Session and stores them as memories.

        This is a lightweight, rule-based extractor. It looks for keywords that
        indicate struggle, mastery, or preferences and stores short 'insight'
        sentences linked back to the session id when available.

        Returns a list of extracted memory strings.
        """
        if session is None:
            logger.warning("extract_from_session called with None session")
            return []

        # Best-effort fetch of events; be defensive about the API
        try:
            if hasattr(session, "get_events") and callable(session.get_events):
                events = session.get_events() or []
            elif hasattr(session, "events"):
                events = getattr(session, "events") or []
            else:
                logger.debug("Session has no events property or get_events method")
                events = []
        except Exception:
            logger.exception("Error retrieving events from session")
            events = []

        new_memories: List[str] = []

        for event in events:
            if not isinstance(event, dict):
                # Skip malformed events
                continue

            role = event.get("role")
            content = event.get("content", "")

            # content may be a dict with a 'text' field or a plain string
            text = ""
            if isinstance(content, dict):
                # Prefer common text keys, fall back to full content repr
                text = content.get("text") or content.get("message") or content.get("utterance") or ""
            else:
                text = str(content or "")

            text = text.strip()
            if not text:
                continue

            text_lower = text.lower()

            # Simple heuristics for user utterances
            if role == "user":
                if any(k in text_lower for k in ("struggle", "struggling", "hard", "difficult", "cant", "can't", "frustrat")):
                    insight = f"User reported difficulty: {text}"
                    new_memories.append(insight)
                if any(k in text_lower for k in ("love", "like", "enjoy", "prefer")):
                    insight = f"User preference: {text}"
                    new_memories.append(insight)

            # Agent/tool outputs may contain graded results or metrics
            if role in ("agent", "system"):
                if "score" in text_lower or "mastery" in text_lower or "accuracy" in text_lower:
                    insight = f"Performance record: {text}"
                    new_memories.append(insight)

                if event.get("type") == "tool_result" and text:
                    insight = f"Tool result: {text}"
                    new_memories.append(insight)

        # Persist extracted memories, attach source_session when possible
        session_id = getattr(session, "session_id", None) or getattr(session, "id", None)
        for mem in new_memories:
            meta: Dict[str, Any] = {}
            if session_id:
                meta["source_session"] = session_id
            self.add_memory(mem, metadata=meta)

        return new_memories


__all__ = ["MemoryManager"]