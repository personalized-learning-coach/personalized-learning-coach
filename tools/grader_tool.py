from typing import Dict
import difflib

def normalize_text(s: str) -> str:
    return s.strip().lower()

def grade_question(payload: Dict) -> Dict:
    expected = payload.get("expected", "")
    answer = payload.get("answer", "")
    score = 1.0 if normalize_text(expected) == normalize_text(answer) else difflib.SequenceMatcher(None, normalize_text(expected), normalize_text(answer)).ratio()
    correct = score >= 0.85
    return {"score": float(score), "correct": bool(correct)}
