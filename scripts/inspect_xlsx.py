"""One-off: understand the structure of an SEC Financial_Report.xlsx.

Sheet names are truncated to 31 chars and collide. The real title
usually lives in the first cell. Verify that before building a parser.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "data" / "raw" / "aapl_10q_2025-03-29.xlsx"


def first_cell(df):
    """The SEC generator puts the full statement title in cell A1."""
    if df.empty or df.shape[1] == 0:
        return "<empty>"
    value = df.iloc[0, 0]
    return "<blank>" if pd.isna(value) else str(value).strip()


def main():
    book = pd.ExcelFile(TARGET)
    print(f"{TARGET.name}: {len(book.sheet_names)} sheets\n")
    print(f"{'rows':>5} {'cols':>5}  {'sheet name':<32} title")
    print("-" * 110)

    for name in book.sheet_names:
        df = book.parse(name, header=None)
        rows, cols = df.shape
        print(f"{rows:>5} {cols:>5}  {name:<32} {first_cell(df)[:60]}")


if __name__ == "__main__":
    main()