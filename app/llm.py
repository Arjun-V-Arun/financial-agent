"""Small Groq connectivity check used by scripts/check_setup.py."""
import time

from openai import OpenAI

from app import config


def complete(prompt: str, system: str | None = None, retries: int = 3) -> str:
    """Send a single prompt, return plain text. Retries on rate limits."""
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "key from https://console.groq.com"
        )
    client = OpenAI(api_key=config.GROQ_API_KEY,
                    base_url=config.GROQ_BASE_URL)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=config.MODEL,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"[llm] call failed ({e}); retrying in {wait}s")
            time.sleep(wait)
