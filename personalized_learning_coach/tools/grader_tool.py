# personalized_learning_coach/tools/grader_tool.py
from typing import Any, Dict
import difflib
import re
from fractions import Fraction

class GraderTool:
    name = "grader_tool"
    description = "Grades a single student answer against an expected answer. Returns score, correctness and feedback."
    input_schema = {"type":"object","properties":{"expected":{"type":"string"},"answer":{"type":"string"}}, "required":["expected","answer"]}

    def _clean(self, s):
        return "" if s is None else re.sub(r"\s+", " ", str(s)).strip().lower()

    def _parse_number(self, s):
        if not s:
            return None
        t = s.strip().lower().replace(",", "")
        if t.endswith("%"):
            try:
                return float(t.rstrip("%"))/100.0
            except Exception:
                return None
        try:
            if "/" in t:
                return Fraction(t)
            return Fraction(str(float(t)))
        except Exception:
            return None

    def grade(self, expected: str, answer: str, mode: str = "mixed") -> Dict[str, Any]:
        exp = self._clean(expected)
        ans = self._clean(answer)
        if exp and exp == ans:
            return {"score":1.0,"correct":True,"feedback":"Exact match."}
        if mode in ("mixed","numeric"):
            try:
                e = self._parse_number(exp)
                a = self._parse_number(ans)
                if e is not None and a is not None:
                    if e == a:
                        return {"score":1.0,"correct":True,"feedback":"Numeric/fraction equivalent."}
            except Exception:
                pass
            if mode=="numeric":
                return {"score":0.0,"correct":False,"feedback":"Numeric mismatch."}
        # fuzzy
        ratio = difflib.SequenceMatcher(None, exp, ans).ratio()
        if ratio >= 0.85:
            return {"score":1.0,"correct":True,"feedback":f"Close match (similarity={ratio:.2f})."}
        if ratio >= 0.6:
            return {"score":0.5,"correct":False,"feedback":f"Partial match (similarity={ratio:.2f})."}
        return {"score":0.0,"correct":False,"feedback":"Incorrect."}


def grade_question(*args, **kwargs):
    if len(args)==1 and isinstance(args[0], dict):
        payload = args[0]
        expected = payload.get("expected")
        answer = payload.get("answer")
        mode = payload.get("mode","mixed")
    else:
        expected = kwargs.get("expected")
        answer = kwargs.get("answer")
        if expected is None and len(args)>=1:
            expected = args[0]
        if answer is None and len(args)>=2:
            answer = args[1]
        mode = kwargs.get("mode","mixed") if kwargs.get("mode") is not None else (args[2] if len(args)>=3 else "mixed")
    return GraderTool().grade(expected=expected, answer=answer, mode=mode)