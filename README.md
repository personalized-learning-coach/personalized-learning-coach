Hybrid ADK-inspired multi-agent personalized learning coach for the Capstone Project (Agents Intensive).
1. python3 -m venv .venv
2. source .venv/bin/activate
3. pip install -e .
4. pip install -r requirements-dev.txt
5. python -m run_local
- agents/: agent implementations
- tools/: MCP-style tools
- memory/: session & long-term memory
- prompts/: prompt templates
- evaluation/: golden sets + evaluation runner
- observability/: logger & traces
- deploy/: Docker + deployment scripts
