import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from app import config

client = genai.Client(api_key=config.GEMINI_API_KEY)
for m in client.models.list():
    if "generateContent" in getattr(m, "supported_actions", []):
        print(m.name)