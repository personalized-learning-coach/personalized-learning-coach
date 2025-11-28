import sys
import os
import json
import time

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.agents.planner_agent import PlannerAgent
from observability.tracer import Tracer

def main():
    print("Testing Tracing & Metrics...")
    
    # Run Planner within a root trace
    with Tracer("root_workflow"):
        planner = PlannerAgent("trace_test_user")
        planner.run({"skills": []})
    
    # Check log file
    log_file = "logs/app.jsonl"
    if os.path.exists(log_file):
        print(f"\n[OK] Log file found at {log_file}")
        print("Checking for trace_id and metrics...")
        
        found_trace = False
        found_metrics = False
        
        with open(log_file, "r") as f:
            lines = f.readlines()
            # Check last few lines
            for line in lines[-10:]:
                entry = json.loads(line)
                if "trace_id" in entry:
                    found_trace = True
                if entry.get("event") == "metric":
                    found_metrics = True
                    print(f"Metric found: {entry.get('data')}")
        
        if found_trace:
            print("[PASS] Trace IDs propagated.")
        else:
            print("[FAIL] No trace_id found in recent logs.")
            
        if found_metrics:
            print("[PASS] Metrics logged.")
        else:
            print("[FAIL] No metrics found in recent logs.")
            
    else:
        print(f"\n[FAIL] Log file not found at {log_file}")

if __name__ == "__main__":
    main()
