import datetime
from typing import Dict, Any, List
from personalized_learning_coach.memory.kv_store import get, put

class ProgressAgent:
    """
    Progress Tracker Agent.
    Updates mastery scores and tracks improvement over time.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.alpha = 0.3  # Learning rate for EMA

    def run(self, lesson_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates progress based on lesson results.
        Expected lesson_results: {"skill_id": str, "score": float (0.0-1.0)}
        """
        skill_id = lesson_results.get("skill_id")
        current_score = float(lesson_results.get("score", 0.0))
        
        if not skill_id:
            return {"error": "Missing skill_id in lesson results"}

        print(f"ProgressAgent: Updating progress for {self.user_id} on skill {skill_id}")

        # 1. Fetch current profiles
        profiles: List[Dict] = get(f"user:{self.user_id}", "skill_profiles") or []
        
        # 2. Find specific skill
        target_skill = None
        for p in profiles:
            if p["skill_id"] == skill_id:
                target_skill = p
                break
        
        # 3. Calculate new mastery (EMA)
        if target_skill:
            prev_mastery = target_skill.get("mastery_score", 0.5) # Default start at 0.5 if unknown
            new_mastery = (prev_mastery * (1 - self.alpha)) + (current_score * self.alpha)
            target_skill["mastery_score"] = new_mastery
            target_skill["last_practiced"] = datetime.datetime.now().isoformat()
            delta = new_mastery - prev_mastery
        else:
            # New skill
            new_mastery = current_score # Or some initialization logic
            target_skill = {
                "skill_id": skill_id,
                "mastery_score": new_mastery,
                "last_practiced": datetime.datetime.now().isoformat()
            }
            profiles.append(target_skill)
            delta = new_mastery # Delta from 0

        # 4. Update memory
        put(f"user:{self.user_id}", "skill_profiles", profiles)

        return {
            "skill_id": skill_id,
            "new_mastery": round(new_mastery, 3),
            "delta": round(delta, 3),
            "trend_summary": "improving" if delta > 0 else "needs practice"
        }
