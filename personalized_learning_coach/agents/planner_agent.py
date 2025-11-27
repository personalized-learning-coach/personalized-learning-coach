import json
import os
from typing import Dict, Any
from personalized_learning_coach.memory.kv_store import put
from personalized_learning_coach.utils.llm_client import LLMClient

class PlannerAgent:
    """
    Curriculum Planner Agent.
    Creates multi-week personalized plans based on assessment data.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = LLMClient()

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
        print(f"PlannerAgent: Generating plan for {self.user_id} based on assessment.")
        
        system_prompt = self._load_prompt()
        user_context = f"Assessment Data: {json.dumps(assessment_data)}"
        full_prompt = f"{system_prompt}\n\n{user_context}"
        
        response_text = self.llm.generate_content(full_prompt)
        
        try:
            plan = json.loads(response_text)
        except json.JSONDecodeError:
            print("Error decoding LLM response. Returning empty plan.")
            plan = {"error": "Failed to generate plan"}

        # Store in long-term memory
        # We'll store it under a 'plans' key for the user
        put(f"user:{self.user_id}", "current_plan", plan)
        
        return plan
