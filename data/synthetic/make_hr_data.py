"""Generate a SYNTHETIC HR workbook — the restricted dataset for RBAC demos.

Nothing here is real Apple data. Figures are invented and internally
consistent only. This file exists so the access-control layer has
something genuinely sensitive to protect.
"""
import random
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "hr_headcount_comp.xlsx"
BANNER = "SYNTHETIC DATA - NOT REAL APPLE DATA - GENERATED FOR RBAC DEMO"

FUNCTIONS = ["Engineering", "Design", "Sales", "Marketing",
             "Operations", "Retail", "Legal", "Finance"]
REGIONS = ["Americas", "Europe", "Greater China", "Japan", "Rest of Asia Pacific"]
PERIODS = ["FY2023", "FY2024", "FY2025"]

random.seed(42)   # reproducible: same numbers on every regeneration


def headcount_rows():
    rows = []
    for period in PERIODS:
        for function in FUNCTIONS:
            for region in REGIONS:
                rows.append({
                    "fiscal_period": period,
                    "function": function,
                    "region": region,
                    "headcount": random.randint(400, 12000),
                    "attrition_pct": round(random.uniform(3.5, 14.0), 1),
                    "open_roles": random.randint(5, 300),
                })
    return pd.DataFrame(rows)


def compensation_rows():
    rows = []
    for period in PERIODS:
        for function in FUNCTIONS:
            base = random.randint(95, 210) * 1000
            rows.append({
                "fiscal_period": period,
                "function": function,
                "band_min_usd": base,
                "band_median_usd": int(base * 1.35),
                "band_max_usd": int(base * 1.9),
                "avg_equity_grant_usd": random.randint(20, 180) * 1000,
                "bonus_target_pct": random.choice([10, 15, 20, 25, 30]),
            })
    return pd.DataFrame(rows)

def write_sheet(writer, name, df):
    """Banner as a trailing column, not a leading row.

    Row 1 becomes the title during ingestion and would then dominate
    every chunk's embedding. A column keeps the provenance marker
    present without crowding out the actual content.
    """
    out = df.copy()
    out["source_note"] = "SYNTHETIC - not real Apple data"
    out.to_excel(writer, sheet_name=name, index=False)


def main():
    with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
        write_sheet(writer, "Headcount", headcount_rows())
        write_sheet(writer, "Compensation Bands", compensation_rows())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()