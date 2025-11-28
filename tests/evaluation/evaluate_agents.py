import sys
import os
import json
import traceback

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.agents.planner_agent import PlannerAgent
from personalized_learning_coach.agents.tutor_agent import TutorAgent
from personalized_learning_coach.agents.coach_agent import CoachAgent
from personalized_learning_coach.agents.progress_agent import ProgressAgent

def load_cases(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def run_evaluation():
    cases_path = "tests/evaluation/golden_cases.json"
    if not os.path.exists(cases_path):
        print(f"Error: {cases_path} not found.")
        return

    cases = load_cases(cases_path)
    print(f"Loaded {len(cases)} golden cases.\n")

    results = []
    passed_count = 0

    # Mock user ID for testing
    user_id = "eval_user"

    for case in cases:
        case_id = case["id"]
        agent_name = case["agent"]
        description = case["description"]
        input_data = case["input"]
        expected_keys = case["expected_keys"]

        print(f"Running Case {case_id}: {description} ({agent_name})")

        try:
            # Instantiate Agent
            if agent_name == "PlannerAgent":
                agent = PlannerAgent(user_id)
            elif agent_name == "TutorAgent":
                agent = TutorAgent(user_id)
            elif agent_name == "CoachAgent":
                agent = CoachAgent(user_id)
            elif agent_name == "ProgressAgent":
                agent = ProgressAgent(user_id)
            else:
                raise ValueError(f"Unknown agent: {agent_name}")

            # Run Agent
            output = agent.run(input_data)
            
            # Verify Output Structure
            missing_keys = [k for k in expected_keys if k not in output]
            
            if missing_keys:
                status = "FAIL"
                reason = f"Missing keys: {missing_keys}"
            else:
                status = "PASS"
                reason = ""
                passed_count += 1

        except Exception as e:
            status = "ERROR"
            reason = str(e)
            traceback.print_exc()

        results.append({
            "id": case_id,
            "status": status,
            "reason": reason
        })
        print(f"  -> {status} {reason}\n")

    # Summary
    print("-" * 30)
    print(f"Evaluation Complete. Passed: {passed_count}/{len(cases)}")
    print("-" * 30)
    
    if passed_count < len(cases):
        sys.exit(1)

if __name__ == "__main__":
    run_evaluation()
