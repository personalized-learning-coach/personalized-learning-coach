# personalized_learning_coach/agents/planner_agent.py
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from personalized_learning_coach.utils.llm_client import LLMClient
from personalized_learning_coach.memory.kv_store import put, get, append_event
from observability.logger import get_logger
from observability.tracer import trace_agent

logger = get_logger("PlannerAgent")


class PlannerAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_ns = f"session:{user_id}"
        self.llm = LLMClient()

    def _build_prompt(self, assessment_data: Dict[str, Any], topic: str) -> str:
        # Simple structured instruction for LLM to produce weeks list
        context = {"user_id": self.user_id, "topic": topic, "assessment": assessment_data}
        return (
            "You are a curriculum planner. Produce a 4-week learning plan for the topic provided.\n\n"
            "Return a JSON object with 'weeks' (list of objects with keys: topic, goal, activities) and 'summary'.\n\n"
            f"Context:\n{json.dumps(context)}"
        )

    def _safe_parse(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            # try to find first JSON object inside text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end+1])
                except Exception:
                    pass
        return {}

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if True: # Legacy tracer block
            requested = payload.get("request", "") if isinstance(payload, dict) else ""
            topic = payload.get("topic") or payload.get("request") or "General Topic"
            prompt = self._build_prompt(payload, topic)
            try:
                resp = self.llm.generate_content(prompt, system_instruction="Curriculum planner - produce JSON plan")
                plan = self._safe_parse(resp)
            except Exception as e:
                logger.exception("Planner LLM failed")
                plan = {}

            # If the model didn't produce weeks, create a reasonable fallback
            if not plan or "weeks" not in plan:
                clean_topic = topic
                plan = {
                    "weeks": [
                        {"topic": f"{clean_topic} Basics", "goal": f"Understand key concepts of {clean_topic}", "activities": ["Reading", "Video", "Example"]},
                        {"topic": f"Intermediate {clean_topic}", "goal": f"Practice and apply {clean_topic}", "activities": ["Project", "Exercises"]},
                        {"topic": f"Advanced {clean_topic}", "goal": f"Build a real-world project using {clean_topic}", "activities": ["Capstone project"]},
                        {"topic": f"Revision & Assessment for {clean_topic}", "goal": "Consolidate and test knowledge", "activities": ["Quiz", "Review"]}
                    ],
                    "summary": f"A 4-week plan to learn {clean_topic}."
                }

            # persist a simple current plan to KV store
            try:
                put(f"user:{self.user_id}", "current_plan", plan)
            except Exception:
                logger.exception("Failed to persist plan")

            return plan