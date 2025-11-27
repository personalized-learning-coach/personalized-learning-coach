import json
import os
from typing import Dict, Any
from personalized_learning_coach.memory.kv_store import get
from personalized_learning_coach.utils.llm_client import LLMClient

class TutorAgent:
    """
    Tutor Agent (Gemini-powered).
    Teaches lessons, provides examples, and generates practice problems.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = LLMClient()

    def _load_prompt(self) -> str:
        prompt_path = "prompts/tutor_prompt.md"
        if not os.path.exists(prompt_path):
             return "You are a helpful tutor."
        with open(prompt_path, "r") as f:
            return f.read()

    def _get_student_context(self) -> str:
        # Fetch skill profile from long-term memory
        # Assuming structure: user:{user_id} -> skill_profiles
        user_data = get(f"user:{self.user_id}", "skill_profiles")
        if not user_data:
            return "Student context: Unknown skill levels."
        return f"Student Skill Profile: {json.dumps(user_data)}"

    def run(self, lesson_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conducts a lesson for a specific item.
        """
        print(f"TutorAgent: Teaching lesson item {lesson_item.get('topic', 'unknown')}")
        
        system_instruction = self._load_prompt()
        student_context = self._get_student_context()
        
        user_message = f"""
        Lesson Request: {json.dumps(lesson_item)}
        Context: {student_context}
        """
        
        response_text = self.llm.generate_content(user_message, system_instruction=system_instruction)
        
        try:
            lesson_content = json.loads(response_text)
        except json.JSONDecodeError:
             print("Error decoding LLM response. Returning empty lesson.")
             lesson_content = {"error": "Failed to generate lesson"}
             
        return lesson_content
