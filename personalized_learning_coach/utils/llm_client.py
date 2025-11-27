from typing import Optional

class LLMClient:
    """
    Simple wrapper for LLM calls.
    Currently a mock implementation.
    """
    def __init__(self, model_name: str = "gemini-pro"):
        self.model_name = model_name

    def generate_content(self, prompt: str) -> str:
        """
        Generates content based on the prompt.
        Returns a mock JSON string for now.
        """
        print(f"[LLMClient] Generating content for prompt length: {len(prompt)}")
        # Return a valid JSON string that matches the expected output of the Planner Agent
        return """
        {
            "week_id": "week_1",
            "objectives": ["Master fractions addition", "Review multiplication tables"],
            "lesson_items": [
                {
                    "topic": "Fractions Addition",
                    "time_minutes": 30,
                    "learning_goal": "Add fractions with unlike denominators",
                    "exercise_type": "practice_problems"
                },
                {
                    "topic": "Multiplication Review",
                    "time_minutes": 15,
                    "learning_goal": "Speed drill for 7x and 8x tables",
                    "exercise_type": "quiz"
                }
            ]
        }
        """
