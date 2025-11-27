from typing import Optional

class LLMClient:
    """
    Simple wrapper for LLM calls.
    Currently a mock implementation.
    """
    def __init__(self, model_name: str = "gemini-pro"):
        self.model_name = model_name

    def generate_content(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generates content based on the prompt.
        Returns a mock JSON string for now.
        """
        print(f"[LLMClient] Generating content for prompt length: {len(prompt)}")
        if system_instruction:
            print(f"[LLMClient] System instruction length: {len(system_instruction)}")

        # Simple heuristic to return different mocks based on prompt content
        if "curriculum planner" in (system_instruction or "").lower() or "weekly plan" in prompt.lower():
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
        elif "tutor agent" in (system_instruction or "").lower() or "lesson content" in prompt.lower():
             return """
            {
                "lesson_content": "To simplify a fraction, divide the top and bottom by the greatest common factor.",
                "worked_example": "Simplify 4/8. Divide both by 4. Result: 1/2.",
                "practice_problems": [
                    {"q": "Simplify 3/9", "difficulty": 1},
                    {"q": "Simplify 12/16", "difficulty": 2},
                    {"q": "Simplify 15/25", "difficulty": 3}
                ],
                "expected_answers": {
                    "Simplify 3/9": "1/3",
                    "Simplify 12/16": "3/4",
                    "Simplify 15/25": "3/5"
                },
                "formative_question": "Why do we divide by the greatest common factor?"
            }
            """
        elif "motivation coach" in (system_instruction or "").lower() or "motivation" in prompt.lower():
            return """
            {
                "message": "Great job improving on your fractions! Consistency is key. You're doing better than 80% of your past self!",
                "routine": [
                    "Review one fraction problem before breakfast",
                    "Do a 5-minute speed drill at 4 PM",
                    "Celebrate with a small treat after completing the drill"
                ]
            }
            """
        
        return "{}"
