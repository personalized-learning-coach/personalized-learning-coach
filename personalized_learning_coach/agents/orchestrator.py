from typing import Dict, Any
from personalized_learning_coach.memory.kv_store import put
from personalized_learning_coach.agents.assessment_agent import AssessmentAgent


class Orchestrator:
    """
    Handles routing between user action and correct agent.
    """

    def handle_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        user_id = mission.get("user_id", "anon")
        action = mission.get("action")

        if action == "start_assessment":
            put(f"session:{user_id}", "started_at", {"t": True})
            agent = AssessmentAgent(user_id)
            return agent.run(None)

        if action == "submit_assessment":
            answers = mission.get("answers", {})
            agent = AssessmentAgent(user_id)
            return agent.run(answers)

        return {"status": "error", "message": "unknown action"}