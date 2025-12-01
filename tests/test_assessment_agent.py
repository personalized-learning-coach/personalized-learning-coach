"""Tests for AssessmentAgent.

This test is robust to agents that implement either a synchronous `run()` or an
`async def run()` coroutine. It also avoids assuming the shape of the returned
objects beyond the small contract used by the test (phase, questions/results,
avg_score and session events).
"""

import asyncio
from personalized_learning_coach.agents.assessment_agent import AssessmentAgent
from personalized_learning_coach.memory.kv_store import _reset_store, get


def _run_maybe_async(fn, *args, **kwargs):
    """Call `fn` and await it if it returns a coroutine.

    Returns the resolved value either way.
    """
    res = fn(*args, **kwargs)
    if asyncio.iscoroutine(res):
        return asyncio.run(res)
    return res


def test_assessment_basic():
    _reset_store()
    uid = "testuser"

    agent = AssessmentAgent(uid)

    # Step 1: ask questions
    q = _run_maybe_async(agent.run, None)
    assert isinstance(q, dict), "Expected a dict from agent.run(None)"
    assert q.get("phase") == "questions"

    questions = q.get("questions") or []
    assert len(questions) > 0, "Expected at least one question to be generated"

    # Step 2: answer using the expected answers where available
    # Fallback questions use "answer", LLM questions might use "answer" or "expected" depending on prompt
    # The prompt says "answer (A/B/C/D)", so we should use "answer"
    answers = {qobj.get("qid"): qobj.get("answer", "") for qobj in questions}
    r = _run_maybe_async(agent.run, {"answers": answers})

    assert isinstance(r, dict), "Expected a dict result from agent.run(answers)"
    assert r.get("phase") == "results"
    assert "avg_score" in r, "Results should include avg_score"

    # Check session stored in KV store
    sess = get(f"session:{uid}", None)
    assert sess is not None, "Expected a session object stored in KV store"
    assert "events" in sess, "Session should contain an 'events' key"