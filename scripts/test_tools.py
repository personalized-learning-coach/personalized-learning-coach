import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from personalized_learning_coach.tools.grader_tool import grade_question
from personalized_learning_coach.tools.standards_lookup import StandardsLookupTool

def test_grader():
    print("--- Testing Grader Tool ---")
    cases = [
        {"expected": "3/4", "answer": "0.75", "mode": "mixed"},
        {"expected": "Paris", "answer": "paris", "mode": "exact"},
        {"expected": "The Pythagorean theorem", "answer": "pythagorean theorem", "mode": "fuzzy"}
    ]
    
    for case in cases:
        result = grade_question(case)
        print(f"Input: {case}")
        print(f"Result: {json.dumps(result)}\n")
        if not result["correct"]:
            print("[FAIL] Expected correct result")

def test_standards():
    print("--- Testing Standards Lookup Tool ---")
    tool = StandardsLookupTool()
    
    query = "fraction"
    results = tool.lookup(query)
    print(f"Query: '{query}' found {len(results)} results.")
    
    if len(results) > 0:
        print(f"First match: {results[0]['id']}")
    else:
        print("[FAIL] Expected to find standards for 'fraction'")

def main():
    test_grader()
    test_standards()

if __name__ == "__main__":
    main()
