import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.agents.tutor_agent import TutorAgent
from personalized_learning_coach.memory.kv_store import put

def main():
    print("Testing Tutor Agent...")
    
    # 1. Setup mock memory
    user_id = "test_student"
    put(f"user:{user_id}", "skill_profiles", [
        {"skill_id": "fractions.simplify", "mastery_score": 0.3}
    ])
    
    # 2. Define a lesson item (as if from Planner)
    lesson_item = {
        "topic": "Simplifying Fractions",
        "learning_goal": "Understand how to reduce fractions to lowest terms",
        "time_minutes": 20
    }
    
    # 3. Run Agent
    agent = TutorAgent(user_id)
    result = agent.run(lesson_item)
    
    print("\nGenerated Lesson Content:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
