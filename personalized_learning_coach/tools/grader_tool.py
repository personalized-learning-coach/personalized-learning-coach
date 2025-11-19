# tools/grader_tool.py
"""
Improved grader MCP-style tool.

Input: { "question_id": str (optional), "expected": str, "answer": str, "mode": str (optional: 'exact'|'fuzzy'|'mixed') }
Output: { "score": float, "feedback": str, "correct": bool }

Behavior:
- Try to parse expected and answer as numeric values (supports decimals and fractions like "3/4").
  If both parse, compare numerically with a tolerance.
- Otherwise fall back to fuzzy string similarity.
"""
from typing import Dict
import difflib
import json
from fractions import Fraction

NUMERIC_TOL = 1e-9  # very strict equality threshold for numeric answers

def normalize_str(s: str) -> str:
    if s is None:
        return ""
    return " ".join(s.strip().lower().split())

def try_parse_numeric(s: str):
    """
    Try to interpret s as a numeric value.
    Supports:
      - decimal floats: "0.75", "2.0"
      - fraction: "3/4"
      - integer: "2"
    Returns a float on success, or None on failure.
    """
    if s is None:
        return None
    s = s.strip()
    if s == "":
        return None
    # Direct float
    try:
        # protect against things like "3 / 4" with spaces: remove spaces around slash first
        if "/" in s:
            # try fraction parsing below first
            raise ValueError()
        return float(s)
    except Exception:
        pass
    # Try fraction parsing
    try:
        # allow expressions like "3/4" or " 3/4 "
        frac = Fraction(s)
        return float(frac)
    except Exception:
        pass
    # Try converting common ratio forms like "3 / 4" by removing spaces
    try:
        compact = s.replace(" ", "")
        if "/" in compact:
            frac = Fraction(compact)
            return float(frac)
    except Exception:
        pass
    return None

def fuzzy_ratio_score(expected: str, answer: str) -> float:
    return difflib.SequenceMatcher(None, normalize_str(expected), normalize_str(answer)).ratio()

def numeric_score(expected_val: float, answer_val: float) -> float:
    if abs(expected_val - answer_val) <= NUMERIC_TOL:
        return 1.0
    # Otherwise, compute a closeness score — 1 / (1 + relative_error)
    # Use relative error to produce a score in (0,1]
    if expected_val == 0:
        rel = abs(answer_val)
    else:
        rel = abs((expected_val - answer_val) / expected_val)
    # convert rel to score; cap to 0
    score = 1.0 / (1.0 + rel)
    return max(0.0, min(1.0, score))

def grade_question(payload: Dict) -> Dict:
    expected = payload.get("expected", "")
    answer = payload.get("answer", "")
    mode = payload.get("mode", "mixed")  # 'exact', 'fuzzy', 'mixed'

    # Try numeric parsing
    expected_num = try_parse_numeric(expected)
    answer_num = try_parse_numeric(answer)

    if mode == "exact":
        # exact textual match (case-insensitive normalized)
        score = 1.0 if normalize_str(expected) == normalize_str(answer) else 0.0
    elif mode == "fuzzy":
        score = fuzzy_ratio_score(expected, answer)
    else:  # mixed
        # prefer numeric equality when both parse
        if (expected_num is not None) and (answer_num is not None):
            score = numeric_score(expected_num, answer_num)
        else:
            # textual exact match first, then fuzzy
            score = 1.0 if normalize_str(expected) == normalize_str(answer) else fuzzy_ratio_score(expected, answer)

    # Decide correctness threshold
    if mode == "exact":
        correct = score >= 0.99
    elif mode == "fuzzy":
        correct = score >= 0.85
    else:  # mixed
        # if numeric and equals -> correct
        if (expected_num is not None) and (answer_num is not None):
            correct = score >= 0.99
        else:
            correct = score >= 0.85

    feedback = "Correct" if correct else f"Expected: {expected}; Got: {answer}; score={score:.3f}"
    return {"score": float(score), "feedback": feedback, "correct": bool(correct)}

# quick demo when executed directly
if __name__ == "__main__":
    examples = [
        {"expected":"3/4","answer":"0.75"},
        {"expected":"3/4","answer":"3/4"},
        {"expected":"Paris","answer":"paris"},
        {"expected":"The Pythagorean theorem","answer":"pythagorean theorem"}
    ]
    for ex in examples:
        print(json.dumps(ex))
        print(json.dumps(grade_question(ex), indent=2))