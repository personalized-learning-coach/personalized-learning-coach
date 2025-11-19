# personalized_learning_coach/agents/assessment_agent.py
from typing import Dict, List, Any
from datetime import datetime

from personalized_learning_coach.memory.kv_store import (
    append_event,
    compact_session,
    get,
    put
)

from personalized_learning_coach.tools.grader_tool import grade_question


class AssessmentAgent:
    """
    AssessmentAgent responsibilities:
    - Provide diagnostic questions (LLM-powered later; stub now)
    - Receive answers from user
    - Grade using custom MCP-like grader tool
    - Write events to memory
    - Compact session to reduce token usage
    - Return structured results to orchestrator
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_ns = f"session:{user_id}"

    def _seed_questions(self) -> List[Dict[str, Any]]:
        """
        Stub questions for now.
        Later this will call Gemini to generate topic-specific assessments.
        """
        return [
            {
                "qid": "q1",
                "prompt": "What is 3/4 as a decimal?",
                "expected": "0.75",
                "type": "numeric",
            },
            {
                "qid": "q2",
                "prompt": "Simplify the fraction 6/8.",
                "expected": "3/4",
                "type": "short-answer",
            },
        ]

    def run(self, answers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        If answers=None → Start assessment
        If answers provided → Grade answers and return summary
        """
        # -----------------------------------------
        # 1) User has not answered yet → send questions
        # -----------------------------------------
        if answers is None:
            append_event(
                self.session_ns,
                {
                    "role": "agent",
                    "type": "assessment_started",
                    "content": {
                        "message": "Assessment started",
                        "time": datetime.utcnow().isoformat(),
                    },
                },
            )

            questions = self._seed_questions()

            # Store questions so we know what to grade later
            put(self.session_ns, "questions", questions)

            return {
                "status": "ok",
                "phase": "questions",
                "questions": questions,
            }

        # -----------------------------------------
        # 2) User submitted answers → grade them
        # -----------------------------------------
        stored_session = get(self.session_ns, "") or {}
        questions = stored_session.get("questions", self._seed_questions())

        results = []
        total_score = 0.0

        for q in questions:
            qid = q["qid"]
            expected = q["expected"]
            user_answer = answers.get(qid, "")

            # Grade using MCP-style tool
            grade_payload = {
                "expected": expected,
                "answer": user_answer,
                "mode": "mixed",
            }

            grade = grade_question(grade_payload)
            total_score += grade["score"]

            results.append(
                {
                    "qid": qid,
                    "prompt": q["prompt"],
                    "expected": expected,
                    "answer": user_answer,
                    "score": grade["score"],
                    "correct": grade["correct"],
                    "feedback": grade["feedback"],
                }
            )

            # Write memory events
            append_event(
                self.session_ns,
                {
                    "role": "user",
                    "type": "answer",
                    "content": {"qid": qid, "answer": user_answer},
                },
            )

            append_event(
                self.session_ns,
                {
                    "role": "agent",
                    "type": "graded",
                    "content": {
                        "qid": qid,
                        "score": grade["score"],
                        "correct": grade["correct"],
                    },
                },
            )

        avg_score = total_score / max(len(questions), 1)

        # Compact memory — workshop concept!
        compacted_session = compact_session(self.session_ns, keep_last=10)

        # Return structured summary
        append_event(
            self.session_ns,
            {
                "role": "agent",
                "type": "assessment_summary",
                "content": {"avg_score": avg_score},
            },
        )

        return {
            "status": "ok",
            "phase": "results",
            "avg_score": avg_score,
            "results": results,
            "compacted_summary": compacted_session["state"].get("short_summary", ""),
        }