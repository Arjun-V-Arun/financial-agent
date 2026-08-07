# Feedback and Ranking

## What it does

A helpful or unhelpful rating changes which permitted chunks rank highest when
the same role asks the same normalized question later.

## Data model

Each SQLite row stores:

- normalized question key
- role
- cited chunk ID
- vote of `+1` or `-1`
- creation timestamp

Whitespace is collapsed and text is case-folded. This makes differently cased
versions of the same text match, but paraphrases remain distinct.

## Ranking equation

For candidate chunk $c$:

$$
S(c) = S_{cosine}(c) + \operatorname{clip}(0.08 \sum votes_c, -0.24, 0.24)
$$

Retrieval first asks Chroma for $3k$ policy-permitted candidates. Feedback
adjusts those scores, sorts them, and returns the top $k$.

## Why the ordering is secure

1. Chroma applies the role policy.
2. Only permitted candidates are returned.
3. Feedback reranks that permitted list.
4. Feedback cannot introduce an arbitrary or restricted chunk.

Role scoping also prevents CEO feedback from influencing CTO retrieval.

## Seeing it work

1. Ask a question with `--learn` (CLI) or through the web console.
2. Note the source IDs in the answer.
3. Mark the result not helpful.
4. Ask the exact question again as the same role.
5. Compare source order — the down-voted chunk should rank lower.
6. Ask again under a different role: the vote does not carry over.

`tests/test_feedback_reranking.py` automates exactly this: it casts a vote
and asserts `retrieve.search()` returns results in a different order
afterward, not just that the stored score is bounded.

## Why use retrieval feedback

It is deterministic, cheap, easy to inspect, and demonstrates actual behavior
change without retraining a model. The cap ensures many votes cannot completely
override semantic relevance.

## Limitations and next version

- Exact normalized questions do not share feedback with paraphrases.
- Every citation receives the same vote, even if only one passage was poor.
- There is no user reputation, abuse protection, decay, or experiment control.
- SQLite is not suitable for high-volume concurrent writes.

At scale, embed question intent into semantic clusters, collect per-citation
ratings, weight trusted users, decay stale feedback, and evaluate ranking
changes offline before deployment.
