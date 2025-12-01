# personalized_learning_coach/agents/progress_agent.py
from typing import Dict, Any, Optional
from datetime import datetime
from personalized_learning_coach.memory.kv_store import get, put
from observability.logger import get_logger

logger = get_logger("ProgressAgent")


class ProgressAgent:
    def __init__(self, user_id: str, alpha: float = 0.3):
        self.user_id = user_id
        self.alpha = float(alpha) if alpha and 0 < alpha <= 1 else 0.3
        self.logger = logger

    def _now_iso(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def run(self, lesson_results: Dict[str, Any]) -> Dict[str, Any]:
        # lesson_results expected: {"skill_id":..., "score": float 0..1}
        skill_id = lesson_results.get("skill_id")
        raw_score = lesson_results.get("score", 0.0)
        if not skill_id:
            return {"error": "missing skill_id"}
        try:
            score = float(raw_score)
        except Exception:
            score = 0.0
        score = max(0.0, min(1.0, score))
        profiles = get(f"user:{self.user_id}", "skill_profiles") or []
        found = None
        for p in profiles:
            if p.get("skill_id") == skill_id:
                found = p
                break
        now = self._now_iso()
        if found:
            prev = float(found.get("mastery_score", 0.0))
            new = prev * (1 - self.alpha) + score * self.alpha
            delta = new - prev
            found["mastery_score"] = new
            found["last_practiced"] = now
        else:
            new = score
            delta = new
            entry = {"skill_id": skill_id, "mastery_score": new, "last_practiced": now}
            profiles.append(entry)
        try:
            put(f"user:{self.user_id}", "skill_profiles", profiles)
        except Exception:
            logger.exception("Failed to persist profile")
        trend = "stable"
        if delta > 0.01:
            trend = "improving"
        elif delta < -0.01:
            trend = "declining"
        return {"skill_id": skill_id, "new_mastery": round(new, 3), "delta": round(delta, 3), "trend_summary": trend}