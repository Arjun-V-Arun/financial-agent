"""Single source of truth for configuration and filesystem paths."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Windows consoles default to cp1252, which can't encode punctuation the
# model routinely emits (narrow no-break spaces, non-breaking hyphens).
# Both the CLI and the Streamlit server print/log through this process's
# stdout, so fix it once here rather than per entry point.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)