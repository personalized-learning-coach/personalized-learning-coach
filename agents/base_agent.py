from typing import Dict

class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    def run(self, payload: Dict) -> Dict:
        raise NotImplementedError()
