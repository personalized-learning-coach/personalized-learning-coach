import json
import os
from typing import List, Dict

class StandardsLookupTool:
    """
    Tool to look up educational standards from a local JSON file.
    """
    def __init__(self, standards_file: str = "standards.json"):
        # Resolve path relative to this file
        base_path = os.path.dirname(__file__)
        self.file_path = os.path.join(base_path, standards_file)
        self.standards = self._load_standards()

    def _load_standards(self) -> List[Dict]:
        if not os.path.exists(self.file_path):
            print(f"Warning: Standards file not found at {self.file_path}")
            return []
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading standards: {e}")
            return []

    def lookup(self, query: str) -> List[Dict]:
        """
        Search for standards containing the query string (case-insensitive).
        """
        query = query.lower().strip()
        results = []
        for std in self.standards:
            # Search in description, category, or ID
            text = f"{std.get('id','')} {std.get('category','')} {std.get('description','')}".lower()
            if query in text:
                results.append(std)
        return results

# Demo usage
if __name__ == "__main__":
    tool = StandardsLookupTool()
    print(json.dumps(tool.lookup("fraction"), indent=2))
