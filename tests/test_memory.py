# tests/test_memory.py
from personalized_learning_coach.memory.kv_store import _reset_store, append_event, get, compact_session

def test_append_and_compact():
    ns = "session:unittest"
    _reset_store()
    append_event(ns, {"role":"user","type":"utterance","content":{"text":"one"}})
    append_event(ns, {"role":"user","type":"utterance","content":{"text":"two"}})
    append_event(ns, {"role":"user","type":"utterance","content":{"text":"three"}})
    sess = get(ns, "")
    assert sess["events"] and len(sess["events"]) == 3
    compacted = compact_session(ns, keep_last=2)
    assert "short_summary" in compacted["state"]
    assert len(compacted["events"]) == 2