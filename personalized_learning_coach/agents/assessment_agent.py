from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re
from personalized_learning_coach.memory.kv_store import append_event, put, get, compact_session
from personalized_learning_coach.tools.grader_tool import grade_question
from personalized_learning_coach.utils.llm_client import LLMClient
from observability.logger import get_logger
from observability.tracer import trace_agent

logger = get_logger("AssessmentAgent")

class AssessmentAgent:
    """Agent responsible for generating and grading assessments."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_ns = f"session:{user_id}"
        self.llm = LLMClient()

    def _generate_questions(self, topic: str = "General Knowledge") -> List[Dict[str, Any]]:
        """Generates diagnostic questions for a given topic."""
        prompt = (
            f"Generate 3 high-quality diagnostic multiple-choice questions for the topic '{topic}'. "
            "Guidelines:\n"
            "1. Questions must be UNAMBIGUOUS and FACTUALLY CORRECT.\n"
            "2. Ensure there is EXACTLY ONE correct answer.\n"
            "3. Distractors must be plausible but clearly incorrect.\n"
            "4. If using code snippets, ensure they are syntactically correct Python/Java.\n"
            "5. Avoid 'trick' questions or questions about obscure trivia.\n"
            "6. DO NOT mix syntax from different languages.\n"
            "7. Ensure options are mutually exclusive.\n"
            "STRICTLY return a JSON list of objects with keys: qid, prompt, options (dict with keys A,B,C,D), answer (A/B/C/D), explanation. "
            "Do NOT generate open-ended or short-answer questions."
        )
        try:
            resp = self.llm.generate_content(prompt, system_instruction="Assessment Generator")
            # Robust JSON Extraction
            questions = [] # Initialize questions to an empty list
            clean = resp.strip()
            
            # 1. Try to find JSON list markers
            start_idx = clean.find("[")
            end_idx = clean.rfind("]")
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = clean[start_idx : end_idx + 1]
                try:
                    questions = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to fix common JSON issues if needed, or just fail
                    logger.warning("JSON decode failed on extracted string: %s...", json_str[:50])
            
            if not isinstance(questions, list):
                 # Fallback: try parsing as markdown code block if not found above
                 if "```json" in clean:
                     match = re.search(r"```json(.*?)```", clean, re.DOTALL)
                     if match:
                         try:
                             questions = json.loads(match.group(1))
                         except json.JSONDecodeError:
                             pass

            if isinstance(questions, list) and len(questions) > 0:
                # Ensure qids are unique/present and STRINGS
                for i, q in enumerate(questions):
                    if "qid" not in q:
                        q["qid"] = f"q{i+1}"
                    else:
                        q["qid"] = str(q["qid"]) # Force string
                return questions
                
            logger.error("Failed to parse questions. Raw response: %s", resp)
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Failed to generate questions: %s", e)
        
        # Fallback (Generic MCQs)
        return [
            {
                "qid": "q1", 
                "prompt": f"Which of the following best describes {topic}?", 
                "options": {"A": "A programming language", "B": "A cooking technique", "C": "A learning topic", "D": "A musical instrument"},
                "answer": "C",
                "explanation": "It is the topic you are currently learning."
            },
            {
                "qid": "q2", 
                "prompt": "True or False: This is a valid topic.", 
                "options": {"A": "True", "B": "False"},
                "answer": "A",
                "explanation": "It is a valid topic."
            },
        ]

    @trace_agent
    def run(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes the assessment agent logic."""
        # payload can be None (start), or {"answers": ...} or {"topic": ...}
        if payload is None:
            payload = {}
        
        answers = payload.get("answers")
        topic = payload.get("topic", "General Knowledge")

        if not answers:
            append_event(self.session_ns, {"role":"agent","type":"assessment_started","content":{"message":f"Assessment started for {topic}","time":datetime.utcnow().isoformat()}})
            questions = self._generate_questions(topic)
            put(self.session_ns, "questions", questions)
            return {"status":"ok", "phase":"questions", "questions": questions}
        
        # grade answers
        if not isinstance(answers, dict):
            answers = {}
        
        # Prefer questions from payload, then session
        questions = payload.get("questions") or get(self.session_ns, "questions") or []
        results = []
        total = 0.0
        for q in questions:
            qid = str(q.get("qid")) # Force string for lookup
            expected = q.get("answer") or q.get("expected") # support both new and old format
            
            # Debug: Log lookup attempt
            logger.info(f"Looking up answer for QID: '{qid}' in answers keys: {list(answers.keys())}")
            
            user_ans_raw = answers.get(qid, "").strip()
            # Extract just the letter if it looks like "A) ..." or "A. ..."
            user_ans = user_ans_raw.upper()
            if len(user_ans) > 1 and user_ans[1] in [")", "."]:
                user_ans = user_ans[0]
            elif len(user_ans) > 2 and user_ans[0] in "ABCD" and user_ans[1] in [")", "."]:
                 user_ans = user_ans[0]
            
            # If user_ans is still long, maybe it's the full text without prefix?
            # In that case, we can't easily match against "A", unless we reverse lookup.
            # But app.py sends "A) Text", so the prefix check should work.
            
            # Debug Logging
            logger.info(f"Grading QID: {qid} | User Raw: '{user_ans_raw}' | Parsed: '{user_ans}' | Expected: '{expected}'")

            # Simple MCQ grading
            is_correct = False
            score = 0.0
            feedback = ""
            
            if expected and len(expected) == 1 and expected in "ABCD":
                # It's an MCQ
                # 1. Direct match of letter
                if user_ans == expected:
                    is_correct = True
                # 2. Fallback: Check if user answer STARTS with expected letter (e.g. "A) ...")
                elif user_ans_raw.upper().startswith(f"{expected})") or user_ans_raw.upper().startswith(f"{expected}."):
                    is_correct = True
                
                score = 1.0 if is_correct else 0.0
                feedback = q.get("explanation", "") if not is_correct else "Correct!"
            else:
                # Fallback to old grader for non-MCQ
                grade = grade_question({"expected": expected, "answer": user_ans, "mode": "mixed"})
                score = grade["score"]
                is_correct = grade["correct"]
                feedback = grade["feedback"]

            total += score
            results.append({"qid": qid, "prompt": q.get("prompt"), "expected": expected, "answer": user_ans, "score": score, "correct": is_correct, "feedback": feedback})
            append_event(self.session_ns, {"role":"user","type":"answer","content":{"qid":qid,"answer":user_ans}})
            append_event(self.session_ns, {"role":"agent","type":"graded","content":{"qid":qid,"score":score,"correct":is_correct}})
            
            # MISTAKE BANK: Store weak areas
            if not is_correct:
                mistake_entry = {
                    "topic": topic,
                    "question": q.get("prompt"),
                    "timestamp": datetime.utcnow().isoformat()
                }
                # Retrieve existing mistakes
                current_mistakes = get(self.session_ns, "mistake_bank") or []
                current_mistakes.append(mistake_entry)
                put(self.session_ns, "mistake_bank", current_mistakes)
                logger.info(f"Recorded mistake for topic '{topic}'")

        avg = total / max(1, len(questions))
        compacted = compact_session(self.session_ns, keep_last=10)
        summary = ""
        if isinstance(compacted, dict):
            summary = (compacted.get("state") or {}).get("short_summary","")
        append_event(self.session_ns, {"role":"agent","type":"assessment_summary","content":{"avg_score":avg}})
        return {"status":"ok","phase":"results","avg_score":avg,"results":results,"compacted_summary":summary}