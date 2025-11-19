from personalized_learning_coach.agents.assessment_agent import AssessmentAgent
from personalized_learning_coach.memory.kv_store import _reset_store, get


def test_assessment_basic():
    _reset_store()
    uid = "testuser"

    agent = AssessmentAgent(uid)

    # Step 1: ask questions
    q = agent.run(None)
    assert q["phase"] == "questions"
    assert len(q["questions"]) > 0

    # Step 2: answer
    answers = {x["qid"]: x["expected"] for x in q["questions"]}
    r = agent.run(answers)

    assert r["phase"] == "results"
    assert "avg_score" in r

    sess = get(f"session:{uid}", "")
    assert sess is not None
    assert "events" in sess