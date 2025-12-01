# tests/test_memory.py
"""Unit tests for the in-memory kv_store helpers used by the learning coach.

This test ensures append_event, get and compact_session behave as expected.
"""
import uuid

from personalized_learning_coach.memory.kv_store import (
    _reset_store,
    append_event,
    get,
    compact_session,
)


def test_append_and_compact():
    # Use a unique namespace per test run to avoid accidental collisions
    ns = f"session:unittest:{uuid.uuid4().hex}"

    # Ensure we start from a clean store
    _reset_store()

    # Append three events
    append_event(ns, {"role": "user", "type": "utterance", "content": {"text": "one"}})
    append_event(ns, {"role": "user", "type": "utterance", "content": {"text": "two"}})
    append_event(ns, {"role": "user", "type": "utterance", "content": {"text": "three"}})

    # Retrieve the session and verify events were recorded
    sess = get(ns, "")
    assert isinstance(sess, dict), "get() should return a dict"
    assert "events" in sess and len(sess["events"]) == 3, (
        f"Expected 3 events after append, got {len(sess.get('events', []))}"
    )

    # Compact the session keeping only the last 2 events
    compacted = compact_session(ns, keep_last=2)
    assert isinstance(compacted, dict), "compact_session() should return a dict"
    assert "state" in compacted and "short_summary" in compacted["state"], (
        "Compacted session state should include a 'short_summary'"
    )
    assert "events" in compacted and len(compacted["events"]) == 2, (
        f"Expected 2 events after compact, got {len(compacted.get('events', []))}"
    )