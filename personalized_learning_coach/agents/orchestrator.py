import json
from typing import Dict
from personalized_learning_coach.memory.kv_store import put
from personalized_learning_coach.tools.grader_tool import grade_question

class Orchestrator:
    def __init__(self):
        pass

    def handle_mission(self, mission: Dict) -> Dict:
        action = mission.get("action")
        if action == "start_assessment":
            session_key = f"session:{mission.get('user_id')}"
            put(session_key, "current", {"state":"assessment_started", "mission": mission})
            return {"status":"ok", "route":"assessment", "session_key": session_key}
        return {"status":"ok", "route":"unknown"}
