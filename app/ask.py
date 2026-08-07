"""CLI entrypoint: python -m app.ask --role CTO "your question"."""
from __future__ import annotations

import argparse

from app import feedback, policy as policy_mod
from app.agent import ask


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the financial agent.")
    parser.add_argument("question")
    parser.add_argument("--role", default="CEO",
                        choices=policy_mod.roles())
    parser.add_argument(
        "--learn",
        action="store_true",
        help="prompt for feedback and use it to rerank this question later",
    )
    args = parser.parse_args()

    policy = policy_mod.load(args.role)
    answer = ask(args.question, policy)

    print(f"\n[{args.role}] {args.question}\n")
    print(answer.text)
    if answer.citations:
        print(f"\nSources: {', '.join(sorted(set(answer.citations))[:6])}")
    if answer.withheld:
        print(f"Withheld from this role: {', '.join(answer.withheld)}")

    if args.learn:
        rating = input("\nWas this answer useful? [y/n/skip]: ").strip().lower()
        vote = {"y": 1, "yes": 1, "n": -1, "no": -1}.get(rating)
        if vote is None:
            print("Feedback skipped.")
        else:
            count = feedback.record(
                args.question, args.role, answer.citations, vote
            )
            print(f"Recorded feedback for {count} cited chunk(s).")


if __name__ == "__main__":
    main()