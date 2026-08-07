import sqlite3

conn = sqlite3.connect("artifacts/facts.db")

query = """
SELECT fiscal_period, value, source_file
FROM facts
WHERE metric = 'net sales' AND fiscal_period = 'Q2 FY2025'
"""

rows = list(conn.execute(query))
print(f"{len(rows)} row(s)")
for row in rows:
    print(row)