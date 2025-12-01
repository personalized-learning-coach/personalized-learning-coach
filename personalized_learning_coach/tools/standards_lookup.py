# personalized_learning_coach/tools/standards_lookup.py
from typing import List, Dict, Any

class StandardsLookupTool:
    name = "standards_lookup_tool"
    description = "Lookup curriculum standards by keyword. Returns a list of matches."
    input_schema = {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}

    def __init__(self):
        self._index = [
            {"id":"CCSS.5.NF.A.1","text":"Add and subtract fractions with unlike denominators"},
            {"id":"CCSS.4.NF.A.1","text":"Understand a fraction 1/b as the quantity formed by 1 part when a whole is partitioned into b equal parts"},
            {"id":"MATH.FRACTIONS.1","text":"Simplify fractions"},
        ]

    def lookup(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q:
            return []
        matches = []
        for it in self._index:
            if q == it["id"].lower() or q in it["text"].lower():
                matches.append(it)
        if not matches:
            tokens = q.split()
            first = tokens[0] if tokens else q
            for it in self._index:
                if first in it["text"].lower():
                    matches.append(it)
        return matches