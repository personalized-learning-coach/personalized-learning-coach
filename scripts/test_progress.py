import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.agents.progress_agent import ProgressAgent
from personalized_learning_coach.memory.kv_store import put, get

def main():
    print("Testing Progress Agent...")
    
    user_id = "test_student_prog"
    
    # 1. Setup initial state
    initial_profiles = [
        {"skill_id": "fractions.add", "mastery_score": 0.5, "last_practiced": "2023-01-01"}
    ]
    put(f"user:{user_id}", "skill_profiles", initial_profiles)
    
    # 2. Simulate a lesson result (good performance)
    lesson_result = {
        "skill_id": "fractions.add",
        "score": 0.9
    }
    
    # 3. Run Agent
    agent = ProgressAgent(user_id)
    result = agent.run(lesson_result)
    
    print("\nUpdate Result:")
    print(json.dumps(result, indent=2))
    
    # 4. Verify Memory Update
    updated_profiles = get(f"user:{user_id}", "skill_profiles")
    print("\nUpdated Memory Profile:")
    print(json.dumps(updated_profiles, indent=2))
    
    # Check math: 0.5 * 0.7 + 0.9 * 0.3 = 0.35 + 0.27 = 0.62
    expected = 0.62
    actual = updated_profiles[0]["mastery_score"]
    if abs(actual - expected) < 0.001:
        print("\n[PASS] Mastery score calculation correct.")
    else:
        print(f"\n[FAIL] Expected {expected}, got {actual}")

if __name__ == "__main__":
    main()
