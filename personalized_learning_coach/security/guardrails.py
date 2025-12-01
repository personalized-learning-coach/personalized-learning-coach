# personalized_learning_coach/security/guardrails.py
import re
from typing import Tuple, List, Optional

class SecurityGuard:
    def __init__(self, block_pii: bool = True, extra_toxic_keywords: Optional[List[str]] = None):
        self.block_pii = block_pii
        email = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone = r"\b\+?\d{1,3}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b"
        ssn = r"\b\d{3}-\d{2}-\d{4}\b"
        self._pii_patterns = [re.compile(p, re.IGNORECASE) for p in (email, phone, ssn)]
        base_toxic = ["hate", "kill", "stupid", "idiot", "destroy"]
        if extra_toxic_keywords:
            base_toxic += extra_toxic_keywords
        self._toxic_patterns = [re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE) for w in base_toxic]

    def check_input(self, text: str) -> Tuple[bool, Optional[str]]:
        if not text:
            return True, None
        for patt in self._toxic_patterns:
            if patt.search(text):
                return False, "I cannot respond to that input as it violates safety guidelines (toxicity)."
        for patt in self._pii_patterns:
            if patt.search(text):
                if self.block_pii:
                    return False, "Please don't share personal information (email, phone, SSN)."
                else:
                    return True, "Warning: your message contains personal information; avoid sharing it."
        return True, None

    def check_output(self, text: str) -> Tuple[bool, Optional[str]]:
        if not text:
            return True, None
        for patt in self._pii_patterns:
            if patt.search(text):
                return False, "[System] Output blocked: detected personal information."
        return True, None

    def mask_pii(self, text: str) -> str:
        out = text
        for patt in self._pii_patterns:
            out = patt.sub("[REDACTED]", out)
        return out