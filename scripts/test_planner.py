import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.agents.planner_agent import PlannerAgent

def main():
    print("Testing Planner Agent...")
    
    # Mock assessment data
    assessment_data = {
        "skills": [
            {"skill_id": "fractions.add", "score": 0.4, "confidence": 0.82},
            {"skill_id": "multiplication.basic", "score": 0.9, "confidence": 0.95}
        ],
        "recommendation": "focus on fractions: addition/subtraction"
    }
    
    agent = PlannerAgent("test_user")
    plan = agent.run(assessment_data)
    
    print("\nGenerated Plan:")
    print(json.dumps(plan, indent=2))

if __name__ == "__main__":
    main()
