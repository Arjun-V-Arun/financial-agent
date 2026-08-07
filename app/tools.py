"""Tools the agent may call. Every tool is policy-gated internally.

The model chooses which tool to invoke and with what arguments. It cannot
choose the role: that is bound by the caller, so no text in a document
or a user message can widen access.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app import config
from app import policy as policy_mod
from app.retrieve import search

MAX_RESULTS = 4          # trimmed: Groq free tier caps tokens/minute
EXCERPT_CHARS = 800


@dataclass
class ToolResult:
    payload: dict          # returned to the model
    chunk_ids: list[str]   # for citations
    denied: list[str]      # labels withheld, for honest refusals


# --- Declarations the model sees (OpenAI tool-call format) ---------------
# Descriptions are prompt engineering: the model selects tools by reading
# these, so vague wording produces wrong tool selection.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_facts",
            "description": (
                "Look up exact numeric HR/compensation values from structured "
                "data. Use this INSTEAD of search_documents whenever the "
                "question asks for a specific number about headcount, "
                "attrition, open roles, salary bands, equity grants or bonus "
                "targets. This does NOT cover financial-statement figures "
                "(net sales, operating income, etc.) — use search_documents "
                "for those, and cite the filing excerpt. Returns matching "
                "rows and their total. Omit function, region or "
                "fiscal_period to aggregate across all of them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": (
                            "One of: headcount, attrition_pct, open_roles, "
                            "band_min_usd, band_median_usd, band_max_usd, "
                            "avg_equity_grant_usd, bonus_target_pct"
                        ),
                    },
                    "fiscal_period": {
                        "type": "string",
                        "description": (
                            "e.g. 'FY2025' or 'Q2 FY2025'. Periods ending in "
                            "'(6M cumulative)' are half-year totals, not "
                            "quarterly. Omit for all periods."
                        ),
                    },
                    "function": {
                        "type": "string",
                        "description": (
                            "Business function for HR metrics, e.g. "
                            "Engineering, Sales, Legal. Omit for all."
                        ),
                    },
                    "region": {
                        "type": "string",
                        "description": (
                            "e.g. Americas, Europe. Omit to aggregate across "
                            "all regions."
                        ),
                    },
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search Apple's SEC filings and internal data for passages "
                "relevant to a question. Returns excerpts with their source "
                "and location. Use this for narrative or explanatory "
                "questions — risk factors, business segments, management "
                "discussion, accounting policies — and for context around a "
                "figure. For the figure itself, use query_facts. Results are "
                "automatically limited to what the current user may see."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of the information "
                            "needed. Be specific: include the topic, fiscal "
                            "period and segment where relevant."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_my_access",
            "description": (
                "Report what data categories the current user may and may not "
                "see. Call this when a question appears to require restricted "
                "data, so the refusal can name what was withheld."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# --- Execution ------------------------------------------------------------

def _search_documents(args: dict, policy) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return ToolResult({"error": "query is required"}, [], [])

    hits = search(query, policy, k=MAX_RESULTS)
    excerpts = [{
        "source": h.source_file,
        "location": h.location,
        "fiscal_period": h.fiscal_period,
        "chunk_id": h.chunk_id,
        "text": h.text[:EXCERPT_CHARS],
    } for h in hits]

    return ToolResult(
        payload={
            "results": excerpts,
            "count": len(excerpts),
            "withheld_categories": policy.denied_labels(),
        },
        chunk_ids=[h.chunk_id for h in hits],
        denied=policy.denied_labels(),
    )


def _similar_metrics(conn, metric: str, allowed: list[str]) -> list[str]:
    """Candidate metric names, so a near-miss teaches rather than dead-ends."""
    if not metric:
        return []
    placeholders = ",".join("?" * len(allowed))
    rows = conn.execute(
        f"SELECT DISTINCT metric FROM facts WHERE metric LIKE ? "
        f"AND sensitivity_label IN ({placeholders}) LIMIT 8",
        [f"%{metric.split()[0]}%"] + allowed,
    )
    return [r[0] for r in rows]


def _query_facts(args: dict, policy) -> ToolResult:
    metric = (args.get("metric") or "").strip().lower()
    if not metric:
        return ToolResult({"error": "metric is required"}, [], [])

    allowed = sorted(policy.allowed_labels)

    # Policy applied IN the SQL, not after: rows this role may not see are
    # never selected, so there is nothing to filter out downstream.
    clauses = [f"sensitivity_label IN ({','.join('?' * len(allowed))})"]
    params: list = list(allowed)

    clauses.append("metric = ?")
    params.append(metric)

    for column in ("fiscal_period", "function", "region", "statement"):
        value = (args.get(column) or "").strip()
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)

    sql = (
        "SELECT fiscal_period, function, region, statement, value, unit, "
        "source_file FROM facts WHERE " + " AND ".join(clauses) +
        " ORDER BY fiscal_period, function, region LIMIT 60"
    )

    conn = sqlite3.connect(config.DB_PATH)
    try:
        rows = conn.execute(sql, params).fetchall()
        if not rows:
            return ToolResult(
                {
                    "rows": [], "count": 0,
                    "note": "No permitted rows matched. The metric name may "
                            "differ, or this role may not access this data.",
                    "similar_metrics": _similar_metrics(conn, metric, allowed),
                    "withheld_categories": policy.denied_labels(),
                },
                [], policy.denied_labels(),
            )
    finally:
        conn.close()

    unit = rows[0][5]
    payload = {
        "rows": [{
            "fiscal_period": r[0],
            "function": r[1] or None,
            "region": r[2] or None,
            "statement": r[3] or None,
            "value": r[4],
            "unit": r[5],
        } for r in rows],
        "count": len(rows),
        # Summing percentages is meaningless; return nothing rather than noise.
        "total": round(sum(r[4] for r in rows), 2) if unit != "percent" else None,
        "source": rows[0][6],
        "withheld_categories": policy.denied_labels(),
    }
    return ToolResult(payload, [], policy.denied_labels())


def _list_my_access(_args: dict, policy) -> ToolResult:
    return ToolResult(
        payload={
            "role": policy.role,
            "description": policy.description,
            "can_see": sorted(policy.allowed_labels),
            "cannot_see": policy.denied_labels(),
        },
        chunk_ids=[],
        denied=policy.denied_labels(),
    )


DISPATCH = {
    "search_documents": _search_documents,
    "query_facts": _query_facts,
    "list_my_access": _list_my_access,
}


def execute(name: str, args: dict, policy) -> ToolResult:
    """Run a tool under a policy. Unknown tool names are refused."""
    handler = DISPATCH.get(name)
    if handler is None:
        return ToolResult({"error": f"unknown tool {name!r}"}, [], [])
    return handler(args, policy)


if __name__ == "__main__":
    for role in ("CEO", "CTO"):
        pol = policy_mod.load(role)
        result = execute("query_facts",
                         {"metric": "headcount", "fiscal_period": "FY2025"},
                         pol)
        print(f"\n{role} headcount FY2025: count={result.payload.get('count')} "
              f"total={result.payload.get('total')}")

        result = execute("search_documents",
                         {"query": "FY2025 net sales"}, pol)
        print(f"{role} net sales search: {result.payload['count']} results, "
              f"withheld {result.payload['withheld_categories']}")