from personalized_learning_coach.tools.grader_tool import grade_question

def test_exact():
    r = grade_question({"expected": "3/4", "answer": "3/4", "mode": "exact"})
    assert r["correct"] is True

def test_inexact_numeric():
    r = grade_question({"expected": "3/4", "answer": "0.75", "mode": "mixed"})
    # numerical equivalence should be scored highly
    assert r.get("score", 0) >= 0.8

def test_fuzzy_text():
    r = grade_question({"expected": "The Pythagorean theorem", "answer": "pythagorean theorem", "mode": "fuzzy"})
    # either fully correct or high fuzzy score
    assert r.get("correct", False) is True or r.get("score", 0) >= 0.8
