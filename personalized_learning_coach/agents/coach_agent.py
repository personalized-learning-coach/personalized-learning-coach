# personalized_learning_coach/agents/coach_agent.py
import json
from typing import Dict, Any
from personalized_learning_coach.utils.llm_client import LLMClient
from observability.logger import get_logger

logger = get_logger("CoachAgent")


class CoachAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = LLMClient()
        self.logger = logger

    def run(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        # Build prompt encouraging the student
        prompt = f"Provide a brief motivational message and a 2-step study routine for this context: {json.dumps(progress_data)}"
        try:
            resp = self.llm.generate_content(prompt, system_instruction="Motivation coach: return JSON with message and routine")
            try:
                parsed = json.loads(resp)
                if isinstance(parsed, dict) and "message" in parsed:
                    return parsed
            except Exception:
                # fallback to using text as message
                return {"message": resp, "routine": ["Study 15 minutes", "Do 5 example problems"]}
        except Exception:
            return {"message": "Keep going — small steps add up!", "routine": ["Study 10 minutes", "Review examples"]}