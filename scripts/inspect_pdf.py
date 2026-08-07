"""One-off: see what pdfplumber actually extracts from a 10-K.

Checking three things before designing the parser:
  1. Is the text clean, or mangled/out-of-order?
  2. Does a repeating footer need stripping?
  3. Do financial tables survive plain text extraction?
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pdfplumber

from app import config

TARGET = config.RAW_DIR / "aapl_10k_fy2025.pdf"
# SAMPLES = [5, 22, 29]      # risk factors / MD&A / financial statements
SAMPLES = [32, 33, 34]     # hunting the Consolidated Statements of Operations

def main():
    with pdfplumber.open(TARGET) as pdf:
        print(f"{TARGET.name}: {len(pdf.pages)} pages\n")
        for i in SAMPLES:
            text = pdf.pages[i].extract_text() or ""
            print("=" * 70)
            print(f"PAGE {i}  ({len(text)} chars)")
            print("=" * 70)
            print(text[:700])
            print()


if __name__ == "__main__":
    main()