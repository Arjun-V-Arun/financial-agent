# Security and RBAC

## What RBAC protects

Every chunk and structured fact has a sensitivity label:

- `PUBLIC_FINANCIAL`
- `SEGMENT_DETAIL`
- `STRATEGY`
- `HR_COMP`

`roles.yaml` grants an exhaustive set of labels. Anything absent is denied.

## Enforcement path

```mermaid
sequenceDiagram
    participant UI as CLI/UI
    participant P as Policy
    participant T as Tool executor
    participant D as Chroma/SQLite
    participant L as LLM
    UI->>P: Load known role
    UI->>L: Question + policy description
    L->>T: Tool name + data query
    T->>D: Query with policy predicate
    D-->>T: Permitted data only
    T-->>L: Filtered tool result
    L-->>UI: Answer + withholding explanation
```

The LLM does not receive a `role` tool argument. Therefore a user message or
malicious document cannot ask the model to execute a tool as CEO.

## Enforcement layers

| Layer | Mechanism | Security effect |
|---|---|---|
| Role loading | Unknown names raise `ValueError` | Deny by default |
| Vector retrieval | Chroma metadata `where` filter | Forbidden chunks are never returned |
| Structured facts | SQL `sensitivity_label IN (...)` | Forbidden rows are never selected |
| Period restriction | Policy fiscal-year check | Analyst cannot use old periods |
| Document restriction | Chroma `doc_type` filter | Auditor receives annual filings only |
| Agent prompt | Documents are declared data | Reduces prompt-injection obedience |
| Output behavior | Restricted inference is forbidden | Avoids reconstructing sensitive figures |

## Why UI-only hiding is insufficient

Hiding HR controls would still allow a user to ask for HR data in free text.
Likewise, asking the LLM to refuse is not a security boundary because prompts
can be bypassed. Here, restricted data is removed at the storage query, so the
model cannot quote what it never receives.

## Verifying it holds

Ask both roles the same question: `How many people work in Engineering?`

- CEO reaches `HR_COMP` data.
- CTO retrieves no `HR_COMP` chunks or fact rows.

The refusal text is useful UX, but `tests/test_rbac.py` is the actual proof —
it asserts on retrieved chunk labels, not on what the model says.
`tests/test_prompt_injection.py` extends this: a permitted chunk whose text
instructs the model to escalate its own access is retrievable, but the
restricted chunk it targets never becomes reachable, because retrieval reads
the bound `Policy` object, never document content.

## Production gaps

- The CLI/UI role control is not authentication.
- Chroma and SQLite are local stores without tenant isolation or encryption.
- There is no immutable audit log of identity, query, policy, and returned IDs.
- Prompt injection uses instruction isolation, not a complete detection and
  output-validation pipeline.

Production should derive roles from signed identity claims, authorize each
request server-side, isolate tenants, encrypt data, log access, and run
adversarial leakage evaluations.
