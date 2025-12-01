# personalized_learning_coach/agents/adk_agents.py
import os
import logging
from typing import Callable

LOG = logging.getLogger(__name__)

# Defensive ADK imports (support multiple ADK/SDK versions)
try:
    from google.adk.agents import Agent
    from google.adk.models.google_llm import Gemini
    from google.genai import types
except Exception:
    LOG.warning("google.adk imports failed — ADK not available or different version. Using local stubs.", exc_info=True)
    # Minimal stubs so other code can import the module in tests/dev without ADK
    class Agent:
        def __init__(self, name=None, model=None, description=None, instruction=None, tools=None):
            self.name = name
            self.model = model
            self.description = description
            self.instruction = instruction
            self.tools = tools or []

    class Gemini:
        def __init__(self, model="gemini-pro", **kwargs):
            self.model = model

    types = None

from dotenv import load_dotenv
from personalized_learning_coach.tools.grader_tool import grade_question
from personalized_learning_coach.tools.standards_lookup import StandardsLookupTool

load_dotenv(".env.local")

# Retry config — try to use types.HttpRetryOptions if available
retry_config = None
if types is not None:
    try:
        retry_config = types.HttpRetryOptions(
            attempts=3,
            exp_base=2,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )
    except Exception:
        retry_config = None

_standards_tool = StandardsLookupTool()

def _load_prompt(name: str, default: str = "") -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(base, "prompts", name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        LOG.debug("Prompt not found: %s", path)
        return default

def _make_model(system_instruction: str, model_name: str = "gemini-pro") -> Gemini:
    kwargs = {"model": model_name}
    if retry_config is not None:
        kwargs["retry_options"] = retry_config
    try:
        # if types.Content exists we could set system_instruction, but keep simple
        return Gemini(**kwargs)
    except Exception:
        LOG.exception("Failed creating Gemini model; falling back to minimal Gemini", exc_info=True)
        return Gemini(model=model_name)

def _tool_to_callable(tool) -> Callable:
    if callable(tool):
        return tool
    for attr in ("lookup", "run", "call"):
        if hasattr(tool, attr) and callable(getattr(tool, attr)):
            return getattr(tool, attr)
    raise TypeError("Unsupported tool type: %r" % (tool,))

def create_planner_agent(model_name: str = "gemini-pro") -> Agent:
    instruction = _load_prompt("planner_prompt.md", default="You are the Planner Agent.")
    model = _make_model(instruction, model_name=model_name)
    return Agent(
        name="Planner",
        model=model,
        description="Creates personalized weekly learning plans.",
        instruction=instruction,
        tools=[_tool_to_callable(_standards_tool)],
    )

def create_tutor_agent(model_name: str = "gemini-pro") -> Agent:
    instruction = _load_prompt("tutor_prompt.md", default="You are the Tutor Agent.")
    model = _make_model(instruction, model_name=model_name)
    return Agent(
        name="Tutor",
        model=model,
        description="Provides interactive lessons and practice problems.",
        instruction=instruction,
        tools=[_tool_to_callable(grade_question)],
    )

def create_coach_agent(model_name: str = "gemini-pro") -> Agent:
    instruction = _load_prompt("coach_prompt.md", default="You are the Coach Agent.")
    model = _make_model(instruction, model_name=model_name)
    return Agent(
        name="Coach",
        model=model,
        description="Tracks progress and provides motivation.",
        instruction=instruction,
    )

def create_assessment_agent(model_name: str = "gemini-pro") -> Agent:
    instruction = _load_prompt("assessment_prompt.md", default="You are the Assessment Agent.")
    model = _make_model(instruction, model_name=model_name)
    return Agent(
        name="Assessment",
        model=model,
        description="Diagnoses student skill levels via adaptive quizzes.",
        instruction=instruction,
        tools=[_tool_to_callable(grade_question)],
    )

def create_orchestrator_agent(model_name: str = "gemini-pro") -> Agent:
    instruction = _load_prompt("orchestrator_prompt.md", default="You are the Orchestrator Agent.")
    model = _make_model(instruction, model_name=model_name)
    return Agent(
        name="Orchestrator",
        model=model,
        description="Coordinates the learning journey.",
        instruction=instruction,
    )

__all__ = [
    "create_planner_agent",
    "create_tutor_agent",
    "create_coach_agent",
    "create_assessment_agent",
    "create_orchestrator_agent",
]