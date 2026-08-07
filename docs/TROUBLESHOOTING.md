# Troubleshooting

## Virtual environment does not start

Symptom: Python reports an executable path from a different machine or user
directory.

Cause: Windows virtual environments embed absolute interpreter paths, so
`.venv` isn't portable between machines.

Fix: delete `.venv`, recreate it locally, and install `requirements.txt`
again.

## `GROQ_API_KEY is not set`

Copy `.env.example` to `.env`, add the key, and launch commands from the
repository root. Offline artifact commands do not require the key.

## Chroma collection does not exist

Run:

```powershell
python -m app.ingest
python -m app.embed
```

The embedding command rebuilds the collection from `chunks.jsonl`.

## `no such table: facts`

Run `python -m app.facts`. It creates the schema and repopulates exact HR rows.

## CEO cannot retrieve HR data

Regenerate the synthetic workbook, rerun ingestion, facts, and embeddings, then
confirm `HR_COMP` appears in the ingestion summary.

## Streamlit cannot import `app`

Run it from the repository root:

```powershell
python -m streamlit run app/ui.py
```

Do not change into the `app` directory first.

## Model emits malformed tool syntax

The agent retries malformed tool calls within a maximum of three turns. If it
persists, verify the configured model supports OpenAI-compatible tool calling
or choose a supported Groq model.

## Feedback seems to have no effect

- Repeat the exact normalized question.
- Use the same role.
- Confirm the answer cited document chunk IDs.
- Multiple votes may be needed when semantic-score gaps exceed `0.08`.
- The boost caps at `0.24` and cannot introduce chunks outside the retrieved
  policy-permitted candidate pool.

## December quarter appears in the next fiscal year

This is expected for Apple. A quarter ending in December 2024 is Q1 FY2025,
because Apple's fiscal year ends in late September.
