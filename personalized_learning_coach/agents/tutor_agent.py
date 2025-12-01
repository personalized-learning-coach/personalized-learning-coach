# personalized_learning_coach/agents/tutor_agent.py
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from personalized_learning_coach.utils.llm_client import LLMClient
from observability.logger import get_logger
from observability.tracer import trace_agent

logger = get_logger("TutorAgent")


class TutorAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = LLMClient()
        self.logger = logger

    def _build_prompt(self, lesson_request: Dict[str, Any]) -> str:
        topic = lesson_request.get("topic", "General Topic")
        return (
            f"Act as an expert tutor. Create a comprehensive and detailed lesson for '{topic}'.\n"
            "The lesson MUST be detailed enough for a beginner to understand and solve the practice problems without external resources.\n"
            "Include syntax rules, key concepts, common pitfalls, and usage examples in the overview.\n\n"
            "Return the lesson in the following MARKDOWN format:\n\n"
            "## Overview\n"
            "[Detailed overview text...]\n\n"
            "## Worked Example\n"
            "[Explanation text...]\n"
            "```[language]\n"
            "[Code snippet]\n"
            "```\n\n"
            "## Practice Problems\n"
            "1. [Question text] (Difficulty: [Level])\n"
            "2. ...\n"
        )

    def run(self, lesson_item: Dict[str, Any]) -> Dict[str, Any]:
        topic = lesson_item.get("topic", "General Topic") if isinstance(lesson_item, dict) else "General Topic"
        self.logger.info("TutorAgent run", extra={"topic": topic})
        prompt = self._build_prompt({"topic": topic})
        
        lesson_content = {
            "overview": "",
            "worked_example": "",
            "practice_problems": []
        }

        try:
            resp_text = self.llm.generate_content(prompt, system_instruction=f"Tutor for {topic}")
            
            # Parse Markdown Sections
            current_section = None
            lines = resp_text.splitlines()
            
            overview_lines = []
            example_lines = []
            problems_lines = []

            for line in lines:
                stripped = line.strip()
                lower_line = stripped.lower()
                
                # Flexible Header Detection
                if lower_line.startswith("#") and "overview" in lower_line:
                    current_section = "overview"
                    continue
                elif lower_line.startswith("#") and "worked example" in lower_line:
                    current_section = "example"
                    continue
                elif lower_line.startswith("#") and "practice problems" in lower_line:
                    current_section = "problems"
                    continue
                
                if current_section == "overview":
                    overview_lines.append(line)
                elif current_section == "example":
                    example_lines.append(line)
                elif current_section == "problems":
                    if stripped and (stripped[0].isdigit() or stripped.startswith("-")):
                        problems_lines.append(stripped)

            lesson_content["overview"] = "\n".join(overview_lines).strip()
            lesson_content["worked_example"] = "\n".join(example_lines).strip()
            lesson_content["practice_problems"] = problems_lines
            
            # Fallback: If overview is empty, use the whole text (parsing failed)
            if not lesson_content["overview"] and not lesson_content["worked_example"]:
                 # Check if it's an error message
                 if "Gemini generate raised error" in resp_text:
                     lesson_content["overview"] = "I'm currently experiencing high traffic (Rate Limit Exceeded). Please wait a moment and try again."
                 else:
                     lesson_content["overview"] = resp_text

        except Exception as e:
            logger.exception("Tutor LLM failed")
            lesson_content = {"overview": "Short lesson summary: enable Gemini for richer content. (Mock LLM) "}

        return {"lesson_content": lesson_content, "generated_at": datetime.now(timezone.utc).isoformat(), "topic": topic}

        return {"lesson_content": lesson_content, "generated_at": datetime.now(timezone.utc).isoformat(), "topic": topic}