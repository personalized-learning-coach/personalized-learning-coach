import json
import logging
import re
from typing import Dict, Any, Optional

from personalized_learning_coach.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM-as-a-Judge evaluator.

    Improvements:
    - Python 3.9 compatible type hints.
    - Robust JSON extraction from LLM output (handles fenced code blocks and bare JSON anywhere in text).
    - Defensive validation of returned JSON (ensures `score` is an int in 1..5 and `rationale` exists).
    - Clear logging on errors and fallback return structure so callers always receive a predictable dict.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()
        self.system_prompt = (
            """
You are an impartial AI Judge. Your job is to evaluate the quality of an AI Agent's response.

You will be given:
1. The User Input
2. The Agent's Response
3. The Expected Criteria (what a good response should contain)

Evaluate the response on these axes:
- effectiveness: Did it solve the user's problem?
- correctness: Is the information accurate?
- alignment: Did it meet the expected criteria?

Return ONLY a JSON object (no surrounding text). The JSON must include at least:
- "score": an integer 1-5 (5 being perfect)
- "rationale": a short explanation of the score
Optionally you may add a "details" field with more structured information.
            """
        )

    def _extract_json(self, text: Optional[str]) -> Optional[str]:
        """Try to extract a JSON object from arbitrary LLM output.

        Strategies:
        - Look for fenced ```json ... ``` blocks
        - Look for fenced ``` ... ``` blocks
        - Look for the first top-level {...} JSON object via a balanced-brace scan
        """
        if not text:
            return None

        # 1) fenced json block
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if m:
            return m.group(1).strip()

        # 2) any fenced block
        m = re.search(r"```\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if m:
            return m.group(1).strip()

        # 3) first standalone JSON object (attempt balanced brace scan)
        brace_start = text.find('{')
        if brace_start == -1:
            return None

        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[brace_start : i + 1]
                    return candidate.strip()
        return None

    def _validate_and_normalize(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure returned structure contains `score` (1-5) and `rationale`.
        Normalize types and provide defaults when reasonable.
        """
        out: Dict[str, Any] = {}

        # Score
        score = parsed.get("score")
        try:
            score_int = int(score)
        except Exception:
            score_int = None

        if score_int is None or not (1 <= score_int <= 5):
            logger.warning("LLM returned invalid or missing score: %r", score)
            # Graceful default to 3 (neutral)
            try:
                fallback = int(parsed.get("score", 3)) if isinstance(parsed.get("score", None), int) else 3
            except Exception:
                fallback = 3
            score_int = max(1, min(5, fallback))

        out["score"] = score_int

        # Rationale
        rationale = parsed.get("rationale") or parsed.get("explanation") or parsed.get("reason")
        if not rationale or not isinstance(rationale, str):
            rationale = "No rationale provided by evaluator."

        out["rationale"] = rationale.strip()

        # Pass through additional fields into details
        if "details" in parsed and isinstance(parsed["details"], (dict, list, str, int, float)):
            out["details"] = parsed["details"]
        else:
            details = {k: v for k, v in parsed.items() if k not in ("score", "rationale")}
            if details:
                out["details"] = details

        return out

    def evaluate(self, user_input: str, agent_response: str, expected_criteria: str) -> Dict[str, Any]:
        """
        Evaluates a single interaction.

        Returns a dict with at least keys: score (int 1..5) and rationale (str).
        """
        prompt = (
            f"User Input: {user_input}\n\n"
            f"Agent Response: {agent_response}\n\n"
            f"Expected Criteria: {expected_criteria}\n\n"
            "Evaluate now and return ONLY the JSON object as described in the system instruction."
        )

        response_text = ""
        try:
            raw = self.llm.generate_content(prompt, system_instruction=self.system_prompt)

            # Normalize raw to string for parsing heuristics (LLM client may return dict)
            if isinstance(raw, dict):
                # Pretty-print to stable JSON text
                response_text = json.dumps(raw, ensure_ascii=False)
            elif isinstance(raw, str):
                response_text = raw
            else:
                # Fallback coercion
                response_text = str(raw)

            logger.debug("LLM judge raw output: %s", response_text)

            json_text = self._extract_json(response_text)
            if not json_text:
                # If we couldn't locate a JSON chunk, try to parse the whole response as JSON
                try:
                    parsed_whole = json.loads(response_text)
                    if isinstance(parsed_whole, dict):
                        normalized = self._validate_and_normalize(parsed_whole)
                        return normalized
                    # else fallthrough to raising below
                except Exception:
                    raise ValueError("Could not locate JSON object in LLM output")

            parsed = json.loads(json_text)
            normalized = self._validate_and_normalize(parsed)
            return normalized

        except json.JSONDecodeError:
            logger.exception("JSON parsing failed for LLM judge output")
            return {
                "score": 3,
                "rationale": f"LLM returned invalid JSON. Raw output: {response_text[:500]}",
            }
        except Exception as e:
            logger.exception("LLMJudge evaluation failed: %s", exc_info=e)
            return {
                "score": 3,
                "rationale": f"Evaluation failed: {str(e)}",
            }