import sys
import os
import json
import time

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.agents.planner_agent import PlannerAgent
from personalized_learning_coach.agents.tutor_agent import TutorAgent

def main():
    print("Testing Logging...")
    
    # Run Planner
    planner = PlannerAgent("log_test_user")
    planner.run({"skills": []})
    
    # Run Tutor
    tutor = TutorAgent("log_test_user")
    tutor.run({"topic": "Logging Demo"})
    
    # Check log file
    log_file = "logs/app.jsonl"
    if os.path.exists(log_file):
        print(f"\n[OK] Log file found at {log_file}")
        print("Last 3 log entries:")
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines[-3:]:
                print(line.strip())
    else:
        print(f"\n[FAIL] Log file not found at {log_file}")

if __name__ == "__main__":
    main()
