from personalized_learning_coach.agents.orchestrator import Orchestrator
import json

def main():
    o = Orchestrator()
    resp = o.handle_mission({"user_id":"vasudha_demo","action":"start_assessment"})
    print(json.dumps(resp, indent=2))

if __name__ == "__main__":
    main()
