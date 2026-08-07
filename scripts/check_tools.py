"""Spike: does the model reliably emit structured tool calls? Delete after."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from google.genai import types
from app import config

client = genai.Client(api_key=config.GEMINI_API_KEY)


def get_revenue(fiscal_year: int) -> str:
    """Look up Apple's total net sales for a given fiscal year.

    Args:
        fiscal_year: The Apple fiscal year, for example 2025.
    """
    return "placeholder"


cfg = types.GenerateContentConfig(
    tools=[get_revenue],
    # Critical: stop the SDK from calling the function for us.
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)

response = client.models.generate_content(
    model=config.MODEL,
    contents="What was Apple's total revenue in fiscal 2024?",
    config=cfg,
)

for part in response.candidates[0].content.parts:
    if part.function_call:
        print("TOOL CALL:", part.function_call.name, dict(part.function_call.args))
    elif part.text:
        print("TEXT:", part.text)