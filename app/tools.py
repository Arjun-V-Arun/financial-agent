"""Tools the agent may call. Every tool is policy-gated internally.

The model chooses which tool to invoke and with what query. It cannot
choose the role: that is bound by the caller, so no text in a document
or a user message can widen access.
"""
from __future__ import annotations

from dataclasses import dataclass

from app import policy as policy_mod
from app.retrieve import search

MAX_RESULTS = 4          # trimmed: Groq free tier caps tokens/minute
EXCERPT_CHARS = 800


@dataclass
class ToolResult:
    payload: dict
    chunk_ids: list[str]
    denied: list[str]


# --- Declarations the model sees (OpenAI tool-call format) ---------------
# Descriptions are prompt engineering: the model selects tools by reading
# these, so vague wording produces wrong tool selection.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search Apple's SEC filings and internal data for passages "
                "relevant to a question. Returns excerpts with their source "
                "and location. Use this for any factual question about "
                "financials, business segments, risk factors, headcount or "
                "compensation. Results are automatically limited to what the "
                "current user is permitted to see."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of the information "
                            "needed. Be specific: include the metric, fiscal "
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
        result = execute("search_documents",
                         {"query": "headcount by function"}, pol)
        print(f"\n{role}: {result.payload['count']} results, "
              f"withheld {result.payload['withheld_categories']}")
        for excerpt in result.payload["results"][:2]:
            print(f"  {excerpt['source']} {excerpt['location'][:50]}")