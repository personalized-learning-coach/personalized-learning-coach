# personalized_learning_coach/agents/orchestrator.py
from typing import Any, Dict, Optional
from observability.logger import get_logger
from observability.tracer import trace_agent

# local imports (these modules are provided below)
from personalized_learning_coach.agents.planner_agent import PlannerAgent
from personalized_learning_coach.agents.tutor_agent import TutorAgent
from personalized_learning_coach.agents.coach_agent import CoachAgent
from personalized_learning_coach.agents.progress_agent import ProgressAgent
from personalized_learning_coach.agents.assessment_agent import AssessmentAgent
from personalized_learning_coach.security.guardrails import SecurityGuard

logger = get_logger("OrchestratorAgent")


def _sanitize_topic(raw: str) -> str:
    """Sanitize a user request into a human-friendly topic title."""
    if not raw:
        return "General Topic"
    s = raw.strip().lower()
    lead_ins = [
        "i want to learn about",
        "i want to learn",
        "i want to study",
        "teach me about",
        "teach me",
        "learn about",
        "learn",
        "study",
        "please teach me",
        "please teach",
        "start lesson on",
        "start lesson",
        "create a learning path for",
        "create learning path for",
        "create a plan for",
        "create plan for",
        "add a learning path for",
        "add learning path for",
        "add a plan for",
        "add plan for",
        "make a plan for",
        "add a new learning path",
        "create a new learning path",
        "new learning path",
        "new plan",
        "add a new laerning path",
        "create a new laerning path",
        "new laerning path",
        "what is",
        "what are",
        "how does",
        "quiz me on",
        "quiz on",
        "assess me on",
        "test me on",
        "give me a quiz on"
        "how do",
        "tell me about",
        "explain",
    ]
    for phrase in lead_ins:
        if s.startswith(phrase):
            s = s[len(phrase):].strip()
            break
    s = s.strip(" -:,.!?\"'")
    if not s:
        return "" # Return empty string instead of "General Topic" to allow detection
    # Title case but keep short acronyms uppercase
    parts = []
    for w in s.split():
        if w.isalpha() and len(w) <= 3:
            parts.append(w.upper())
        else:
            parts.append(w.capitalize())
    return " ".join(parts)


from personalized_learning_coach.utils.llm_client import LLMClient

class OrchestratorAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.logger = logger
        self.planner = PlannerAgent(user_id)
        self.tutor = TutorAgent(user_id)
        self.coach = CoachAgent(user_id)
        self.progress = ProgressAgent(user_id)
        self.assessment = AssessmentAgent(user_id)
        self.llm = LLMClient()
        self.guard = SecurityGuard()
        
        # Initialize Session for Persistence
        from personalized_learning_coach.memory.session import Session
        self.session = Session(user_id)
        
        # Load State from Session
        loaded_state = self.session.get_state()
        if loaded_state and "plans" in loaded_state:
            self.state = loaded_state
            self.logger.info("Restored state from session")
        else:
            # New State Structure for Multi-Path Support
            self.state: Dict[str, Any] = {
                "plans": {},  # {plan_id: {topic, plan_data, current_topic, ...}}
                "active_plan_id": None,
                "last_action": None,
                "assessment_in_progress": False,
                "proposed_topic": None,  # Store topic from off-topic questions
                "pending_review": None,
                "last_assessment_data": None,
                "last_assessment_result": None,
                "chats": {} # {chat_key: [messages]}
            }
            self._save_state()

    def save_chat_history(self, chat_key: str, messages: list):
        """Save chat history for a specific context."""
        self.state.setdefault("chats", {})
        self.state["chats"][chat_key] = messages
        self._save_state()

    def get_chat_history(self, chat_key: str) -> list:
        """Retrieve chat history for a specific context."""
        return self.state.get("chats", {}).get(chat_key, [])

    def _save_state(self):
        """Persist current state to session."""
        # We save the whole state dict under "state" key in session
        # Session.update_state merges keys, so we iterate
        for k, v in self.state.items():
            self.session.update_state(k, v)

    def _safe_lower(self, text: Any) -> str:
        if not text:
            return ""
        try:
            return str(text).lower()
        except Exception:
            return ""

    def _parse_bulk_answers(self, user_text: str, questions: list) -> Dict[str, str]:
        """Uses LLM to parse unstructured bulk answers into {qid: answer}."""
        import json
        q_summary = "\n".join([f"{q.get('qid', 'q'+str(i))}: {q.get('prompt')}" for i, q in enumerate(questions)])
        prompt = (
            f"The user provided the following answers to a quiz:\n"
            f"User Text: \"{user_text}\"\n\n"
            f"Questions:\n{q_summary}\n\n"
            "Map the user's answers to the Question IDs (q1, q2, etc.). "
            "Return ONLY a valid JSON object where keys are 'q1', 'q2', etc. and values are the user's answer string. "
            "If an answer is missing, omit the key. Do not include markdown formatting."
        )
        try:
            resp = self.llm.generate_content(prompt, system_instruction="Data Parser")
            # Clean potential markdown
            clean = resp.strip()
            if clean.startswith("```"):
                lines = clean.splitlines()
                if len(lines) >= 2:
                    clean = "\n".join(lines[1:-1])
            return json.loads(clean)
        except Exception as e:
            self.logger.error(f"Failed to parse bulk answers: {e}")
            return {}

    def create_plan(self, topic: str, plan_data: Dict[str, Any]) -> str:
        """Creates a new plan and sets it as active. Returns the new plan_id."""
        import uuid
        plan_id = str(uuid.uuid4())[:8]  # Simple ID
        
        # Derive first topic
        first_week = plan_data.get("weeks", [{}])[0] if isinstance(plan_data, dict) else {}
        first_topic = first_week.get("topic") or topic

        self.state["plans"][plan_id] = {
            "id": plan_id,
            "main_topic": topic,
            "data": plan_data,
            "current_topic": first_topic,
            "active_week_index": 0, # Start at Week 1 (index 0)
            "progress": 0.0,
            "pending_review": None, # Scoped to this plan
            "last_assessment_result": None # Scoped to this plan
        }
        self.state["active_plan_id"] = plan_id
        # Clear global state to avoid confusion (though we should prefer plan state)
        self.state["pending_review"] = None
        self.state["last_assessment_result"] = None
        return plan_id

    def switch_plan(self, plan_id: str):
        if plan_id in self.state["plans"]:
            self.state["active_plan_id"] = plan_id

    def switch_week(self, plan_id: str, week_index: int):
        """Switches the active plan and the specific week within it."""
        self.logger.info(f"Switching week for plan {plan_id} to index {week_index}")
        if plan_id in self.state["plans"]:
            self.state["active_plan_id"] = plan_id
            plan = self.state["plans"][plan_id]
            
            # Validate week index
            weeks = plan.get("data", {}).get("weeks", [])
            if not weeks:
                weeks = plan.get("weeks", [])
            
            if 0 <= week_index < len(weeks):
                plan["active_week_index"] = week_index
                plan["current_topic"] = weeks[week_index].get("topic", plan["main_topic"])
                self._save_state()
            else:
                self.logger.warning(f"Invalid week index {week_index} for plan {plan_id}")
        else:
            self.logger.warning(f"Plan {plan_id} not found")

    def get_active_context(self) -> Dict[str, Any]:
        aid = self.state.get("active_plan_id")
        if aid and aid in self.state["plans"]:
            return self.state["plans"][aid]
        return {}

    @trace_agent
    def run(self, user_input: str) -> str:
        try:
            # Guard input check is handled in _run_internal


            response = self._run_internal(user_input)
            self._save_state()
            return response
        except Exception as e:
            self.logger.exception("Orchestrator run failed")
            return f"I encountered an error: {str(e)}. Please try again."

    def _run_internal(self, user_input: str) -> str:
        # Guard input (Double check, but mainly for logic flow)
        is_safe, refusal = self.guard.check_input(user_input)
        if not is_safe:
            self.logger.warning("Input blocked", extra={"user_input": user_input})
            return refusal or "I cannot answer that."

        if True: # Legacy tracer block (indentation preservation)
            user_input = (user_input or "").strip()
            trimmed = self._safe_lower(user_input)
            
            # Context
            ctx = self.get_active_context()
            current_topic = ctx.get("current_topic")
            current_plan_data = ctx.get("data")

            # Handle Assessment Flow
            if self.state.get("assessment_in_progress"):
                assessment_data = self.state.get("assessment_data", {})
                mode = assessment_data.get("mode", "interactive")
                
                if mode == "bulk":
                    # Handle Bulk Assessment (End of Week)
                    questions = assessment_data.get("questions", [])
                    
                    # Check if input is JSON (from UI Form)
                    import json
                    answers = {}
                    is_json = False
                    try:
                        if user_input.strip().startswith("{"):
                            answers = json.loads(user_input)
                            is_json = True
                    except Exception:
                        pass
                    
                    if not is_json:
                        # Fallback: Parse unstructured text
                        answers = self._parse_bulk_answers(user_input, questions)
                    
                    # Grade
                    res = self.assessment.run({
                        "answers": answers, 
                        "topic": assessment_data.get("topic"),
                        "questions": questions # Pass questions explicitly
                    })
                    score = res.get("avg_score", 0.0)
                    results = res.get("results", [])
                    
                    # Build Report
                    out = [f"### Assessment Results\n**Score:** {score*100:.0f}%"]
                    for r in results:
                        q_text = r.get("prompt")
                        is_correct = r.get("correct")
                        feedback = r.get("feedback")
                        user_ans = r.get("answer", "N/A")
                        expected = r.get("expected", "N/A")
                        
                        icon = "✅" if is_correct else "❌"
                        out.append(f"\n{icon} **{q_text}**")
                        out.append(f"Your Answer: {user_ans}")
                        if not is_correct:
                            out.append(f"Correct Answer: {expected}")
                        out.append(f"Feedback: {feedback}")
                    
                    self.state["assessment_in_progress"] = False
                    self.state["last_assessment_data"] = assessment_data # Retain for context
                    self.state["assessment_data"] = None

                    # Gating Logic
                    if score >= 0.7:
                        # PASS -> Advance Week
                        self.state["last_assessment_result"] = "pass"
                        self.state["pending_review"] = None # Clear any previous weak areas
                        
                        # Save to Plan State
                        plan_id = self.state.get("active_plan_id")
                        if plan_id and plan_id in self.state["plans"]:
                            self.state["plans"][plan_id]["last_assessment_result"] = "pass"
                            self.state["plans"][plan_id]["pending_review"] = None

                        out.append("\n\n🎉 **Congratulations!** You passed the assessment.")
                        
                        # Advance Logic
                        current_plan_data = self.get_active_context().get("data", {})
                        if current_plan_data and "weeks" in current_plan_data:
                            weeks = current_plan_data["weeks"]
                            # Advance Logic
                            # Advance Logic
                            # Re-fetch plan to be safe (though plan_id should be set above)
                            plan_id = self.state.get("active_plan_id")
                            if plan_id and plan_id in self.state["plans"]:
                                plan = self.state["plans"][plan_id]
                                current_idx = plan.get("active_week_index", 0)
                                
                                if current_idx + 1 < len(weeks):
                                    next_idx = current_idx + 1
                                    next_topic = weeks[next_idx].get("topic")
                                    
                                    # Update State IN PLACE
                                    self.state["plans"][plan_id]["active_week_index"] = next_idx
                                    self.state["plans"][plan_id]["current_topic"] = next_topic
                                    
                                    # Update global state to reflect change immediately
                                    self.state["active_plan_id"] = plan_id
                                    self._save_state() # Force save immediately
                                    
                                    # CRITICAL: Update local current_topic so subsequent logic uses the NEW topic
                                    current_topic = next_topic 
                                    
                                    out.append(f"\n**Next Up:** {next_topic}\n\nReady to start?")
                                else:
                                    out.append("\n**You have completed the entire learning path!** 🎓")
                    else:
                        # FAIL -> Recommend Review
                        self.state["last_assessment_result"] = "fail"
                        
                        # Identify weak areas
                        weak_areas = []
                        for r in results:
                            if not r.get("correct"):
                                weak_areas.append(r.get("prompt"))
                        
                        self.state["pending_review"] = weak_areas
                        
                        # Save to Plan State
                        plan_id = self.state.get("active_plan_id")
                        if plan_id and plan_id in self.state["plans"]:
                            self.state["plans"][plan_id]["last_assessment_result"] = "fail"
                            self.state["plans"][plan_id]["pending_review"] = weak_areas

                        out.append("\n\n⚠️ **Review Needed**")
                        out.append("You didn't quite reach the 70% passing score. I recommend reviewing the following concepts:")
                        for wa in weak_areas:
                            out.append(f"\n* {wa}")
                        out.append("\n\n(Say 'finished' again when you want to retake the quiz.)")
                    
                    return "\n".join(out)

                else:
                    # Interactive Mode (Quiz Me)
                    # Check if input is JSON (from UI Form)
                    import json
                    answers = {}
                    is_json = False
                    try:
                        if user_input.strip().startswith("{"):
                            answers = json.loads(user_input)
                            is_json = True
                    except Exception:
                        pass

                    if is_json:
                        # Treat as full submission
                        self.state["assessment_in_progress"] = False
                        self.state["assessment_data"] = None # Clear data
                        
                        # Call AssessmentAgent to grade
                        res = self.assessment.run({"answers": answers, "topic": assessment_data.get("topic")})
                        
                        score = res.get("avg_score", 0.0)
                        results = res.get("results", [])
                        
                        out = [f"### Quiz Complete!\n**Score:** {score*100:.0f}%"]
                        for r in results:
                            q_text = r.get("prompt")
                            is_correct = r.get("correct")
                            feedback = r.get("feedback")
                            icon = "✅" if is_correct else "❌"
                            out.append(f"\n{icon} **{q_text}**\n{feedback}")
                        
                        out.append("\n")
                        if score < 0.7:
                            out.append("### ⚠️ Review Recommended\n")
                            out.append("You missed a few key concepts. I recommend reviewing:\n")
                            weak_areas = []
                            for r in results:
                                if not r.get("correct"):
                                    weak_areas.append(r.get("prompt"))
                            for area in weak_areas[:3]:
                                out.append(f"- {area}\n")
                            
                            # Store for immediate review
                            self.state["pending_review"] = weak_areas[:3]
                            
                            out.append("\nWould you like me to explain these concepts again?")
                        else:
                            out.append("\nGreat job! Would you like to continue with the next lesson?")
                        
                        return "\n".join(out)

                    # Normal Interactive Flow (Text Input)
                    questions = assessment_data.get("questions", [])
                    current_idx = assessment_data.get("current_index", 0)
                    answers = assessment_data.get("answers", {})
                    
                    # Store answer for current question
                    if 0 <= current_idx < len(questions):
                        current_q = questions[current_idx]
                        qid = current_q.get("qid")
                        answers[qid] = user_input
                        assessment_data["answers"] = answers
                    
                    # Advance to next question
                    next_idx = current_idx + 1
                    assessment_data["current_index"] = next_idx
                    
                    if next_idx < len(questions):
                        # Ask next question
                        next_q = questions[next_idx]
                        prompt = next_q.get("prompt")
                        options = next_q.get("options")
                        
                        self.state["assessment_data"] = assessment_data
                        # Just return the intro message. The UI (app.py) handles the form.
                        return f"**Question {next_idx + 1}/{len(questions)}**\n{prompt}"
                    else:
                        # Quiz finished -> Grade
                        self.state["assessment_in_progress"] = False
                        self.state["assessment_data"] = None # Clear data
                        
                        # Call AssessmentAgent to grade
                        res = self.assessment.run({"answers": answers, "topic": assessment_data.get("topic")})
                        
                        score = res.get("avg_score", 0.0)
                        results = res.get("results", [])
                        
                        out = [f"### Quiz Complete!\n**Score:** {score*100:.0f}%"]
                        for r in results:
                            q_text = r.get("prompt")
                            is_correct = r.get("correct")
                            feedback = r.get("feedback")
                            icon = "✅" if is_correct else "❌"
                            out.append(f"\n{icon} **{q_text}**\n{feedback}")
                        
                        out.append("\n")
                        if score < 0.7:
                            out.append("### ⚠️ Review Recommended\n")
                            out.append("You missed a few key concepts. I recommend reviewing:\n")
                            
                            # Identify weak areas from results
                            weak_areas = []
                            for r in results:
                                if not r.get("correct"):
                                    # Extract a keyword or just use the question prompt as a proxy for the topic
                                    # Ideally, the question object would have a 'concept' field, but we can use the prompt for now.
                                    prompt = r.get("prompt")
                                    # Simple heuristic: take the first few words or the whole prompt
                                    weak_areas.append(prompt)
                            
                            for area in weak_areas[:3]: # Limit to top 3
                                out.append(f"- {area}\n")
                            
                            # Store for immediate review
                            self.state["pending_review"] = weak_areas[:3]
                            
                            out.append("\nWould you like me to explain these concepts again? (Type 'Review' or 'Explain')")
                        else:
                            out.append("\nGreat job! Would you like to continue with the next lesson?")
                        
                        return "\n".join(out)

            # Triggers
            wants_quiz = any(kw in trimmed for kw in ("quiz", "assess", "test me"))
            
            # Explicit Plan Creation
            # Check for exact phrases or "add ... path" pattern
            plan_keywords = [
                "new plan", "add plan", "create plan", "start path", "add path", 
                "learning path", "new path", "create path",
                "new laerning path", "add laerning path", "create laerning path" # Typos
            ]
            
            explicit_plan_request = any(kw in trimmed for kw in plan_keywords)
            
            # Also check for "add ... path" or "create ... path" if not found
            if not explicit_plan_request:
                if ("add" in trimmed or "create" in trimmed or "new" in trimmed) and \
                   ("path" in trimmed or "plan" in trimmed or "course" in trimmed):
                    explicit_plan_request = True

            # Fallback Plan Trigger (only if NO active plan)
            needs_plan = explicit_plan_request or (
                not ctx and any(kw in trimmed for kw in ("learn", "plan", "study", "curriculum"))
            )
            
            affirmative = any(kw in trimmed for kw in ("start", "yes", "let's", "lets", "teach", "begin", "review", "explain"))
            finished = any(kw in trimmed for kw in ("finished", "done", "complete", "i'm done", "i am done"))
            continue_trigger = any(kw in trimmed for kw in ("continue", "next", "move on", "proceed"))

            if continue_trigger:
                # User wants to move forward.
                if self.state.get("last_action") == "reviewing":
                     return "I hope that review helped! We can **retake the quiz** to verify your understanding, or I can **teach the lesson again**. What would you like to do?"
                
                # Check if we can advance week
                plan_id = self.state.get("active_plan_id")
                if plan_id:
                    plan = self.state["plans"][plan_id]
                    weeks = plan.get("weeks", [])
                    current_idx = plan.get("active_week_index", 0)
                    
                    # If user passed the last assessment, advance week (Auto-Advance)
                    if self.state.get("last_assessment_result") == "pass":
                        if current_idx + 1 < len(weeks):
                            next_idx = current_idx + 1
                            next_topic = weeks[next_idx]["topic"]
                            
                            # Update State
                            plan["active_week_index"] = next_idx
                            plan["current_topic"] = next_topic
                            self.state["last_assessment_result"] = None # Reset so we don't loop
                            self.state["pending_review"] = None
                            self.state["last_action"] = "planning"
                            
                            # Force save
                            self._save_state()
                            
                            # Update local current_topic so we generate the NEW lesson immediately
                            current_topic = next_topic
                            
                            # Fall through to 'affirmative' to generate lesson
                            affirmative = True
                            # return f"Moving to **Week {next_idx + 1}: {next_topic}**.\n\nReady to start the lesson?"
                        else:
                            return "You have completed all weeks in this plan! 🎓"

                    # If user says "next week" specifically (Manual Advance)
                    elif "week" in trimmed and "next" in trimmed:
                        if current_idx + 1 < len(weeks):
                            next_idx = current_idx + 1
                            next_topic = weeks[next_idx]["topic"]
                            plan["active_week_index"] = next_idx
                            plan["current_topic"] = next_topic
                            self.state["last_assessment_result"] = None
                            self.state["pending_review"] = None
                            self.state["last_action"] = "planning"
                            self._save_state()
                            
                            current_topic = next_topic
                            affirmative = True
                            # return f"Moving to **Week {next_idx + 1}: {next_topic}**.\n\nReady to start the lesson?"
                        else:
                            return "You have completed all weeks in this plan! 🎓"
 
                if current_topic:
                    # If user says "next" and we are at the start of a topic (not reviewing), just START.
                    # We can assume if they say "next", they want the lesson.
                    # Fall through to 'affirmative' logic by setting affirmative = True
                    affirmative = True
                    # return f"We are currently on **{current_topic}**. Would you like to start the lesson?"
                
                # return "I'm ready! What would you like to do next?"

            try:
                if wants_quiz:
                    topic = current_topic or _sanitize_topic(user_input) or "General"
                    res = self.assessment.run({"topic": topic})
                    questions = res.get("questions", [])
                    
                    if not questions:
                        return f"Sorry, I couldn't generate a quiz for {topic}. Try again?"

                    # Initialize Quiz State
                    self.state["assessment_in_progress"] = True
                    self.state["assessment_data"] = {
                        "mode": "interactive",
                        "topic": topic,
                        "questions": questions,
                        "current_index": 0,
                        "answers": {}
                    }
                    
                    # Just return the intro message. The UI (app.py) handles the form.
                    return f"Here is a quick diagnostic quiz for **{topic}**:"

                elif needs_plan:
                    # Create NEW plan
                    topic = _sanitize_topic(user_input)
                    
                    # Check if we have a proposed topic from a previous turn
                    if not topic and self.state.get("proposed_topic"):
                        topic = self.state.pop("proposed_topic")

                    # If topic is STILL empty, ask for topic
                    if not topic:
                        # Store intent
                        self.state["proposed_topic"] = "General" # Placeholder
                        return "What topic would you like to create a learning path for?"

                    # Create Plan
                    plan = self.planner.run({"topic": topic, "assessment_data": self.state.get("last_assessment_data")})
                    
                    if not plan or "weeks" not in plan:
                        return f"I couldn't create a plan for {topic}. Please try again."

                    # Store Plan
                    import uuid
                    plan_id = str(uuid.uuid4())[:8]
                    plan["id"] = plan_id
                    plan["active_week_index"] = 0
                    plan["current_topic"] = plan["weeks"][0]["topic"]
                    plan["main_topic"] = topic # Required by UI
                    
                    self.state["plans"][plan_id] = plan
                    self.state["active_plan_id"] = plan_id
                    
                    first_topic = plan["weeks"][0]["topic"]
                    
                    # Store context for next turn
                    self.state["proposed_topic"] = None
                    
                    # Update context
                    ctx = self.get_active_context()
                    first_topic = ctx.get("current_topic")
                    
                    self.state["last_action"] = "planning"
                    return f"I've created a **new learning path** for **{topic}**!\n\nWeek 1 Focus: {first_topic}\n\nWould you like to start a lesson on {first_topic}?"

                elif affirmative:
                    # Check for Pending Review (Weak Areas)
                    pending_review = self.state.get("pending_review")
                    if pending_review:
                        # Trigger Targeted Review
                        topic = f"Review: {', '.join(pending_review)}"
                        # Clear pending review
                        self.state["pending_review"] = None
                        
                        # Use Tutor to explain specific concepts
                        # We pass the weak areas as the topic or context
                        lesson = self.tutor.run({"topic": topic}) or {}
                        self.state["last_action"] = "reviewing"
                        content = lesson.get("lesson_content", {})
                        
                        out = [f"### Targeted Review\nI've prepared a review on: **{', '.join(pending_review)}**\n"]
                        if isinstance(content, dict):
                            overview = content.get("overview") or content.get("text") or ""
                            out.append(overview)
                        else:
                            out.append(str(content))
                            
                        out.append("\nDoes that help clarify things? We can continue with the next lesson when you're ready.")
                        return "\n".join(out)

                    # If user says "yes", they want the CURRENT topic. 
                    # Do NOT fallback to sanitizing "yes" as a topic.
                    
                    # SPECIAL CASE: If user just passed, "yes"/"start" means "start the new lesson"
                    if self.state.get("last_assessment_result") == "pass":
                        self.state["last_assessment_result"] = None # Reset flag
                        # Fall through to normal lesson generation for the NEW current_topic

                    topic = current_topic
                    if not topic:
                        # If no active topic, check if we have a proposed one
                        topic = self.state.get("proposed_topic")
                    
                    if not topic:
                        return "I'm ready to start! What topic would you like to begin with?"

                    lesson = self.tutor.run({"topic": topic}) or {}
                    self.state["last_action"] = "teaching"
                    content = lesson.get("lesson_content", {})
                    
                    # Format response
                    out = [f"### Lesson: {topic}\n"]
                    if isinstance(content, dict):
                        overview = content.get("overview") or content.get("text") or ""
                        if overview:
                            out.append("Lesson content:\n\n" + overview)
                        
                        example = content.get("worked_example")
                        if example:
                            out.append("\n**Worked Example:**\n")
                            if isinstance(example, str):
                                out.append(example)
                            elif isinstance(example, dict):
                                if "code" in example:
                                    title = example.get("title", "Example")
                                    code = example.get("code", "")
                                    explanation = example.get("explanation", [])
                                    out.append(f"**{title}**\n")
                                    out.append(f"```java\n{code}\n```\n")
                                    if isinstance(explanation, list):
                                        for line in explanation:
                                            out.append(f"- {line}")
                                    else:
                                        out.append(str(explanation))
                                else:
                                    out.append(str(example))

                        problems = content.get("practice_problems") or []
                        if problems:
                            out.append("\n**Practice Problems:**\n")
                            for p in problems:
                                if isinstance(p, dict):
                                    q = p.get("q")
                                    diff = p.get("difficulty", "?")
                                    out.append(f"- {q} (Difficulty: {diff})")
                                else:
                                    out.append(f"- {str(p)}")
                        else:
                            out.append("\n**Practice Problems:**\n\n(No practice problems available)")
                    else:
                        out.append(str(content))
                    out.append("\nLet me know when you're done practicing!")
                    return "\n\n".join(out)

                elif finished:
                    # Check if we just finished/passed
                    if self.state.get("last_assessment_result") == "pass":
                         return "You've already completed this week! Say **'next week'** to move on."

                    # Trigger End-of-Week Assessment
                    topic = current_topic or "general"
                    
                    # Generate Quiz
                    res = self.assessment.run({"topic": topic})
                    questions = res.get("questions", [])
                    
                    if not questions:
                        # Fallback if generation fails
                        return f"Great job on finishing! I couldn't generate a quiz right now, but you can move on to the next week."

                    # Initialize Bulk Assessment State
                    self.state["assessment_in_progress"] = True
                    self.state["assessment_data"] = {
                        "mode": "bulk",
                        "topic": topic,
                        "questions": questions,
                        "answers": {}
                    }
                    
                    # Return intro text. The UI (app.py) will render the form based on 'questions' in state.
                    return f"### End-of-Week Assessment: {topic}\nTo complete this week, please answer the following questions."

                else:
                    # Fallback / Smart Switch
                    # If input is substantial, try to answer it.
                    if len(user_input) > 2:
                        current_topic_name = current_topic or "General"
                        
                        # Context from last assessment?
                        last_quiz_ctx = ""
                        if self.state.get("last_assessment_data"):
                            lqd = self.state["last_assessment_data"]
                            q_list = lqd.get("questions", [])
                            # Summarize last quiz
                            q_summary = "\n".join([f"Q: {q.get('prompt')}" for q in q_list])
                            last_quiz_ctx = f"\n\nContext from recent quiz on '{lqd.get('topic')}':\n{q_summary}\n"

                        prompt = (
                            f"The user is currently learning '{current_topic_name}'. "
                            f"They asked: '{user_input}'. "
                            f"{last_quiz_ctx}"
                            "Answer their question naturally and helpfully as a tutor. "
                            "If the user explicitly wants to learn a NEW topic (even if there are typos like 'kleaern'), "
                            "start your response with 'SWITCH_TOPIC: <new_topic>'. "
                            "Otherwise, just answer the question. "
                            "Do NOT ask them to create a new learning path unless they explicitly ask for a new topic. "
                            "If the question is about the recent quiz, use the quiz context to explain. "
                            "If you don't understand (e.g. foreign language), politely explain that you only speak English."
                        )
                        answer = self.llm.generate_content(prompt, system_instruction="Helpful Tutor")
                        
                        # Check for SWITCH_TOPIC signal
                        if "SWITCH_TOPIC:" in answer:
                            parts = answer.split("SWITCH_TOPIC:", 1)
                            new_topic = parts[1].strip().split("\n")[0].strip()
                            
                            # Trigger Plan Creation
                            if new_topic:
                                # Recursively call run with the sanitized topic to trigger plan creation
                                # But we need to be careful not to loop. 
                                # Instead, just execute the plan creation logic here.
                                
                                plan_data = self.planner.run({"request": user_input, "topic": new_topic}) or {}
                                self.create_plan(new_topic, plan_data)
                                ctx = self.get_active_context()
                                first_topic = ctx.get("current_topic")
                                self.state["last_action"] = "planning"
                                return f"I've created a **new learning path** for **{new_topic}**!\n\nWeek 1 Focus: {first_topic}\n\nWould you like to start a lesson on {first_topic}?"

                        return answer
                    
                    return "I'm here to help you learn. You can ask for a **plan** (e.g. 'I want to learn Python'), say **Start lesson**, ask for a **quiz**, or say **Done** when finished practicing."

            except Exception as e:
                logger.exception("Error in orchestrator run")
                return f"Sorry — something went wrong: {e}"

            except Exception as e:
                logger.exception("Error in orchestrator run")
                return f"Sorry — something went wrong: {e}"