"""Provider-agnostic LLM client. Nothing else imports a vendor SDK."""
import time
from google import genai
from google.genai import types
from app import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)


def complete(prompt: str, system: str | None = None, retries: int = 3) -> str:
    """Send a single prompt, return plain text. Retries on rate limits."""
    cfg = types.GenerateContentConfig(system_instruction=system) if system else None

    for attempt in range(retries):
        try:
            response = _client.models.generate_content(
                model=config.MODEL,
                contents=prompt,
                config=cfg,
            )
            return response.text
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"[llm] call failed ({e}); retrying in {wait}s")
            time.sleep(wait)