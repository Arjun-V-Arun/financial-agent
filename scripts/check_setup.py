"""Smallest possible proof that key + network + SDK + wrapper all work."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import llm  # noqa: E402

if __name__ == "__main__":
    print("Calling model...")
    print(llm.complete("Reply with exactly: OK"))