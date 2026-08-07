"""One-off: examine the internal grid of an SEC financial statement sheet.

Need to know: which row holds period headers, which column holds labels,
and how the values align, before writing an extractor.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from app import config

TARGET = config.RAW_DIR / "aapl_10q_2025-03-29.xlsx"
SHEET = "CONDENSED CONSOLIDATED STATEMEN"     # Operations


def main():
    df = pd.read_excel(TARGET, SHEET, header=None)
    print(f"{SHEET}  shape={df.shape}\n")
    for i in range(min(14, len(df))):
        cells = []
        for j in range(df.shape[1]):
            v = df.iloc[i, j]
            cells.append("·" if pd.isna(v) else str(v).strip()[:28])
        print(f"{i:>3} | " + " | ".join(cells))


if __name__ == "__main__":
    main()