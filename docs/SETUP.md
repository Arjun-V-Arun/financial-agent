# Setup Guide

## 1. Create the environment

```powershell
cd financial-agent
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

A virtual environment copied from another machine is not portable — its
launcher can embed an absolute path to that machine's Python install. If
`.venv` doesn't run, delete it and recreate it locally with the commands
above.

If PowerShell blocks activation, use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Configure Groq

```powershell
Copy-Item .env.example .env
```

Open `.env` and set `GROQ_API_KEY`. Do not commit this file. Running ingestion,
embeddings, facts, or tests does not use Groq credits.

## 3. Understand the input data

- `data/raw/*.pdf`: Apple FY2023-FY2025 10-K annual reports.
- `data/raw/*.xlsx`: nine Apple quarterly workbooks from SEC EDGAR.
- `data/synthetic/hr_headcount_comp.xlsx`: deterministic invented HR data used
  only to prove access control.

Regenerate the synthetic workbook when required:

```powershell
python data/synthetic/make_hr_data.py
```

## 4. Build understanding artifacts

Run these in order:

```powershell
python -m app.ingest
python -m app.facts
python -m app.embed
```

What each command produces:

| Command | Output | Why it exists |
|---|---|---|
| `app.ingest` | `artifacts/chunks.jsonl` | Common auditable schema for both formats |
| `app.facts` | `artifacts/facts.db` | Exact HR values and feedback storage |
| `app.embed` | `artifacts/chroma/` | Local semantic retrieval index |

## 5. Verify locally

The setup check makes one small Groq request; tests do not call the LLM.

```powershell
python scripts/check_setup.py
python -m pytest -q
```

## 6. Run the CLI

```powershell
python -m app.ask --role CEO "What were Apple's FY2025 net sales?"
python -m app.ask --role CTO "How many people work in Engineering?"
python -m app.ask --role AUDITOR "Summarize FY2025 net sales."
```

For feedback:

```powershell
python -m app.ask --role CEO --learn "What drove FY2025 net sales?"
```

## 7. Run the frontend

```powershell
python -m streamlit run app/ui.py
```

Open the local URL printed by Streamlit. Select a role, ask a question, inspect
the source IDs and withheld categories, then rate the retrieval.

The role selector is a local control, not authentication. In production the
role must come from an authenticated identity token, not a user-editable field.
