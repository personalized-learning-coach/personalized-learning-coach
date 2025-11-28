from typing import Optional
from observability.logger import get_logger
from observability.tracer import Tracer

class LLMClient:
    """
    Simple wrapper for LLM calls.
    Currently a mock implementation.
    """
    def __init__(self, model_name: str = "gemini-pro"):
        self.model_name = model_name
        self.logger = get_logger("LLMClient")

    def generate_content(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generates content based on the prompt.
        Returns a mock JSON string for now.
        """
        with Tracer("llm_generate"):
            # Estimate tokens (char / 4)
            prompt_tokens = len(prompt) // 4
            
            self.logger.info("Generating content", extra={
                "event": "llm_request",
                "data": {
                    "model": self.model_name,
                    "prompt_length": len(prompt),
                    "system_instruction_length": len(system_instruction) if system_instruction else 0
                }
            })
            
            print(f"[LLMClient] Generating content for prompt length: {len(prompt)}")
            if system_instruction:
                print(f"[LLMClient] System instruction length: {len(system_instruction)}")
                
            # Mock logic based on prompt content
            response_text = "{}"
            if "curriculum planner" in (system_instruction or "").lower():
                response_text = """
                {
                    "week_1": {
                        "topic": "Fractions",
                        "goal": "Understand basic concepts",
                        "activities": ["Video: Intro to Fractions", "Practice: Identifying numerators"]
                    },
                    "week_2": {
                        "topic": "Multiplication",
                        "goal": "Master times tables 1-5",
                        "activities": ["Game: Multiplication Bingo", "Quiz: Times Tables"]
                    }
                }
                """
            elif "tutor" in (system_instruction or "").lower():
                response_text = """
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
                response_text = """
                {
                    "message": "Great job improving on your fractions! Consistency is key. You're doing better than 80% of your past self!",
                    "routine": [
                        "Review one fraction problem before breakfast",
                        "Do a 5-minute speed drill at 4 PM",
                        "Celebrate with a small treat after completing the drill"
                    ]
                }
                """
            
            completion_tokens = len(response_text) // 4
            
            # Log metrics
            self.logger.info("LLM Metrics", extra={
                "event": "metric",
                "data": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            })
            
            return response_text
