from personalized_learning_coach.memory.kv_store import _reset_store, append_event, compact_session, get

def main():
    ns = "session:test_user"
    _reset_store()
    append_event(ns, {"role":"user","type":"utterance","content":{"text":"I want to get better at fractions"}})
    append_event(ns, {"role":"agent","type":"action","content":{"text":"Generate diagnostic"}})
    append_event(ns, {"role":"user","type":"utterance","content":{"text":"I need more practice with 3/4"}})
    append_event(ns, {"role":"agent","type":"tool_result","content":{"text":"Graded 2/3 correct"}})
    print("Session before compact:")
    print(get(ns, ""))
    compacted = compact_session(ns, keep_last=2)
    print("Session after compact:")
    print(compacted)

if __name__ == "__main__":
    main()