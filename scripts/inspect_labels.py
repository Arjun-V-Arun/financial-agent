"""Where does each sensitivity label start and stop, page by page?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.ingest_pdf import ingest_pdf


def main():
    path = config.RAW_DIR / "aapl_10k_fy2025.pdf"
    chunks = ingest_pdf(path)

    current = None
    for c in chunks:
        if c.sensitivity_label != current:
            current = c.sensitivity_label
            print(f"{c.location:<12} -> {current}")
            print(f"             {c.text[:90]!r}")


if __name__ == "__main__":
    main()