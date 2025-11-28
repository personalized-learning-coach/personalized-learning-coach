import json
import os
from typing import Dict, Any
from personalized_learning_coach.memory.kv_store import put
from personalized_learning_coach.utils.llm_client import LLMClient
from observability.logger import get_logger

class PlannerAgent:
    """
    Curriculum Planner Agent.
    Creates multi-week personalized plans based on assessment data.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = LLMClient()
        self.logger = get_logger("PlannerAgent")

    def _load_prompt(self) -> str:
        # Assuming prompts are in the root 'prompts' directory relative to execution or package
        # Adjust path as needed. For now, assuming running from root.
        prompt_path = "prompts/planner_prompt.md"
        if not os.path.exists(prompt_path):
             # Fallback or error
             return "You are a curriculum planner."
        with open(prompt_path, "r") as f:
            return f.read()

    def run(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a weekly plan based on assessment results.
        """
        self.logger.info("Starting run", extra={"event": "agent_start", "data": {"user_id": self.user_id}})
        print(f"PlannerAgent: Generating plan for {self.user_id} based on assessment.")
        
        system_prompt = self._load_prompt()
        user_context = f"Assessment Data: {json.dumps(assessment_data)}"
        full_prompt = f"{system_prompt}\n\n{user_context}"
        
        response_text = self.llm.generate_content(full_prompt)
        
        try:
            plan = json.loads(response_text)
        except json.JSONDecodeError:
            print("Error decoding LLM response. Returning empty plan.")
            self.logger.error("Failed to decode LLM response", extra={"event": "llm_error"})
            plan = {"error": "Failed to generate plan"}

        # Store in long-term memory
        # We'll store it under a 'plans' key for the user
        put(f"user:{self.user_id}", "current_plan", plan)
        
        self.logger.info("Finished run", extra={"event": "agent_end", "data": {"plan_keys": list(plan.keys())}})
        return plan
