import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.agents.coach_agent import CoachAgent
from personalized_learning_coach.memory.kv_store import put

def main():
    print("Testing Coach Agent...")
    
    user_id = "test_student_coach"
    
    # 1. Setup mock memory
    put(f"user:{user_id}", "skill_profiles", [
        {"skill_id": "fractions.add", "mastery_score": 0.65},
        {"skill_id": "multiplication.basic", "mastery_score": 0.9}
    ])
    
    # 2. Simulate recent progress update
    progress_data = {
        "skill_id": "fractions.add",
        "delta": 0.15,
        "trend_summary": "improving"
    }
    
    # 3. Run Agent
    agent = CoachAgent(user_id)
    result = agent.run(progress_data)
    
    print("\nCoach Response:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
