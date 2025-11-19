from personalized_learning_coach.agents.orchestrator import Orchestrator
import json

def main():
    o = Orchestrator()
    user = "vasudha_demo"

    print("\n--- START ASSESSMENT ---")
    q = o.handle_mission({"user_id": user, "action": "start_assessment"})
    print(json.dumps(q, indent=2))

    # mimic user answers by answering with expected values
    answers = {item["qid"]: item["expected"] for item in q["questions"]}

    print("\n--- SUBMIT ASSESSMENT ---")
    r = o.handle_mission({"user_id": user, "action": "submit_assessment", "answers": answers})
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()