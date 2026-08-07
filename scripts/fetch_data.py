"""Download SEC filings for a single company into data/raw.

XLSX comes from EDGAR's generated Financial_Report.xlsx (10-Q filings).
10-K PDFs are NOT on EDGAR — download those from the company's IR site.
"""
import time
import requests
from pathlib import Path

# --- Configuration -------------------------------------------------
CIK = "320193"           # Apple. NVIDIA = 1045810
PREFIX = "aapl"          # filename prefix; nvda for NVIDIA
UA = "Arjun V Arun arjun_pg25@cse.nits.ac.in"   # SEC requires a real contact
WANT = 9                 # 3 years of 10-Qs (Q4 is inside the 10-K)
SCAN = 20                # candidates to examine; gaps are expected

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
HEADERS = {"User-Agent": UA}


def get(url):
    """Single chokepoint for every EDGAR request: identity + throttle."""
    time.sleep(0.15)                      # SEC limit is 10 req/sec
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()                  # fail loudly, at the call site
    return r


def recent_filings(form_type, limit):
    """Return (accession, report_date) for recent filings of one form type.

    report_date is the period the data DESCRIBES, not when it was filed.
    """
    url = f"https://data.sec.gov/submissions/CIK{CIK.zfill(10)}.json"
    recent = get(url).json()["filings"]["recent"]
    out = []
    for form, acc, report in zip(
        recent["form"], recent["accessionNumber"], recent["reportDate"]
    ):
        if form == form_type:
            out.append((acc.replace("-", ""), report))
        if len(out) == limit:
            break
    return out


def filing_files(accession):
    """Enumerate a filing's directory. Never guess a filename."""
    url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession}/index.json"
    return {item["name"] for item in get(url).json()["directory"]["item"]}


def fetch_xlsx(accession, report_date):
    """Download Financial_Report.xlsx if this filing has one."""
    if "Financial_Report.xlsx" not in filing_files(accession):
        print(f"  skip {report_date}: no Financial_Report.xlsx")
        return False
    url = (f"https://www.sec.gov/Archives/edgar/data/"
           f"{CIK}/{accession}/Financial_Report.xlsx")
    dest = RAW / f"{PREFIX}_10q_{report_date}.xlsx"
    dest.write_bytes(get(url).content)
    print(f"  saved {dest.name}")
    return True


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"Fetching up to {WANT} quarterly reports for CIK {CIK}...")

    saved = 0
    for accession, report_date in recent_filings("10-Q", SCAN):
        if fetch_xlsx(accession, report_date):
            saved += 1
        if saved == WANT:
            break

    print(f"\n{saved} XLSX files in {RAW}")
    print("Reminder: 10-K PDFs must come from the company's IR site.")


if __name__ == "__main__":
    main()