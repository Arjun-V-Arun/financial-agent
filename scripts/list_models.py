import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI

from app import config

if not config.GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
    )

client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)
for model in client.models.list():
    print(model.id)
