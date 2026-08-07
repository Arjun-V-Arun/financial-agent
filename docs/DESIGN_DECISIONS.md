# Design Decisions

## 1. Metadata is part of the security model

Access cannot be added reliably after ingestion if chunks never received
sensitivity labels. Classification, provenance, fiscal period, and document
type must travel with every chunk and vector.

## 2. Prompt instructions are not authorization

"Do not reveal HR" is useful model guidance, but not enforcement. The durable
boundary is a storage query that cannot return HR under the CTO policy.

## 3. RAG and structured querying solve different problems

Vector retrieval is strong at meaning and weak at exact aggregation. SQL is
strong at exact values and weak at arbitrary language. An agent becomes useful
when it routes safely between these complementary tools.

## 4. Derived state should be rebuildable

Chunks, embeddings, and facts are generated artifacts. Rebuilding from source
is safer than manually repairing an index whose data and metadata may disagree.

They're committed to the repo despite being derived, though: a deployed
instance starts from a container with no local history and constrained
resources, and rebuilding there means downloading an embedding model and
re-parsing every source document on a cold start. Shipping the already-built
`artifacts/` directory trades repo purity for a deployment that starts
immediately with the exact index that was tested. `python -m app.ingest &&
python -m app.facts && python -m app.embed` still regenerates it identically
from source at any time.

## 5. Stable IDs enable provenance and learning

Chunk IDs connect ingestion, Chroma, citations, tests, and feedback. Without a
stable identifier, it is difficult to explain or improve a retrieved answer.

## 6. Feedback needs guardrails

An unlimited vote boost could replace semantic relevance and be manipulated.
Role scoping, exact intent scoping, candidate-only reranking, and a bounded
boost keep this demonstration understandable and controlled.

## 7. Portable environments require explicit dependencies

A copied `.venv` embeds machine-specific paths. A short direct dependency file
and deterministic artifact commands are more portable than transferring the
environment directory or a huge incidental package freeze.

## 8. Provider configuration should have one source of truth

Mixed Gemini and Groq utilities create setup failures and confusing keys. The
current code consistently uses Groq's OpenAI-compatible API, while MiniLM
embeddings remain local.

## 9. A UI should remain an adapter

The frontend must not reimplement retrieval or policy. Both interfaces load a
policy and call the same `ask()` and `feedback.record()` functions, keeping one
behavior and security path.

## 10. Naming scope precisely

This is a single-tenant reference implementation, not a production financial
platform. Naming the authentication, tenancy, observability, classification,
and concurrency gaps explicitly is what makes the remaining work legible.

> Mental model: precompute what should be stable, enforce access before model
> context, use deterministic tools for exact facts, and let the LLM orchestrate
> rather than authorize.
