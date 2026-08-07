"""Single source of truth for configuration and filesystem paths."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths: derived from this file's location, never the working directory ---
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SYNTHETIC_DIR = ROOT / "data" / "synthetic"
ARTIFACTS_DIR = ROOT / "artifacts"

CHUNKS_PATH = ARTIFACTS_DIR / "chunks.jsonl"
DB_PATH = ARTIFACTS_DIR / "facts.db"
CHROMA_DIR = ARTIFACTS_DIR / "chroma"
SUMMARIES_PATH = ARTIFACTS_DIR / "doc_summaries.json"

# --- LLM ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
MODEL = os.getenv("MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
        "from https://aistudio.google.com/apikey"
    )

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)