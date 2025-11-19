from tools.grader_tool import grade_question

def test_exact():
    r = grade_question({"expected":"3/4","answer":"3/4"})
    assert r["correct"] is True

def test_inexact():
    r = grade_question({"expected":"3/4","answer":"0.75"})
    assert r["score"] >= 0.8
