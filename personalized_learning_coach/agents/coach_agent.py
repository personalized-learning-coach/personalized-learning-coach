import json
import os
from typing import Dict, Any
from personalized_learning_coach.memory.kv_store import get
from personalized_learning_coach.utils.llm_client import LLMClient
from observability.logger import get_logger

class CoachAgent:
    """
    Motivation Coach Agent.
    Provides motivational messages and study routines.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = LLMClient()
        self.logger = get_logger("CoachAgent")

    def _load_prompt(self) -> str:
        prompt_path = "prompts/coach_prompt.md"
        if not os.path.exists(prompt_path):
             return "You are a motivational coach."
        with open(prompt_path, "r") as f:
            return f.read()

    def _get_progress_context(self) -> str:
        profiles = get(f"user:{self.user_id}", "skill_profiles") or []
        if not profiles:
            return "No recent activity recorded."
        
        # Simple summary of top skills
        summary = [f"{p['skill_id']}: {p.get('mastery_score', 0.0):.2f}" for p in profiles]
        return f"Recent Skill Mastery: {', '.join(summary)}"

    def run(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates motivation and tips based on progress.
        """
        self.logger.info("Generating motivation", extra={"event": "agent_start"})
        print(f"CoachAgent: Generating motivation for {self.user_id}")
        
        system_instruction = self._load_prompt()
        progress_context = self._get_progress_context()
        
        user_message = f"""
        Recent Progress Update: {json.dumps(progress_data)}
        Overall Context: {progress_context}
        """
        
        response_text = self.llm.generate_content(user_message, system_instruction=system_instruction)
        
        try:
            coach_response = json.loads(response_text)
        except json.JSONDecodeError:
            print("Error decoding LLM response. Returning generic motivation.")
            self.logger.error("Failed to decode LLM response", extra={"event": "llm_error"})
            coach_response = {
                "message": "Keep going! You are doing great.",
                "routine": ["Study for 10 mins", "Review notes"]
            }
            
        self.logger.info("Finished motivation", extra={"event": "agent_end"})
        return coach_response
