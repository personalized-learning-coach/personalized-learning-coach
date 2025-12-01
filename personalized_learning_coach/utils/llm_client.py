# personalized_learning_coach/utils/llm_client.py
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

USE_GEMINI = os.environ.get("USE_GEMINI", "0") not in ("0", "", "false", "False")

if USE_GEMINI:
    # Import here so module still imports when gemini isn't installed.
    try:
        from google import genai    # google-genai SDK
        from google.genai import types
        genai_available = True
    except Exception as e:
        genai_available = False
        logger.exception("google-genai import failed: %s", e)
else:
    genai_available = False


class LLMClient:
    """LLM client wrapper that uses Google GenAI (Gemini) when enabled.

    - If USE_GEMINI=1 and google-genai is installed and auth is configured,
      will call the Gemini endpoint.
    - Otherwise falls back to a harmless mock generator (keeps app usable).
    """

    def __init__(self, model: Optional[str] = None):
        # Default reasonably capable model name; change to one you have access to
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.logger = logger

    def generate_content(self, prompt: str, system_instruction: Optional[str] = None, max_tokens: int = 512) -> str:
        """Return string content for the given prompt.

        When Gemini is enabled, we call the genai SDK and return concatenated text output.
        When disabled or if an error occurs, we return a deterministic mock string.
        """
        if not USE_GEMINI or not genai_available:
            self.logger.info("Gemini disabled or unavailable, returning fallback response")
            return json.dumps({
                "summary": "Gemini disabled - enable with USE_GEMINI=1 and set GOOGLE credentials",
                "prompt_echo": (prompt or "")[:400]
            })

        import time
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                # Use the new google-genai SDK pattern
                client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
                
                full_prompt = prompt
                if system_instruction:
                    full_prompt = f"System Instruction: {system_instruction}\n\n{prompt}"

                response = client.models.generate_content(
                    model=self.model,
                    contents=full_prompt,
                )
                
                if hasattr(response, "text") and response.text:
                    return response.text
                elif hasattr(response, "candidates") and response.candidates:
                    # Fallback for candidates
                    parts = []
                    for c in response.candidates:
                        if hasattr(c, "content") and hasattr(c.content, "parts"):
                            for p in c.content.parts:
                                if hasattr(p, "text"):
                                    parts.append(p.text)
                    if parts:
                        return "\n".join(parts)
                
                return str(response)

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Gemini 429 Rate Limit. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                
                logger.exception("Gemini generate failed: %s", e)
                return json.dumps({"summary": "Gemini generate raised error", "error": str(e)})