"""Role-based access control, enforced at the data layer.

Every read of chunk data passes through here. The policy is loaded from
roles.yaml so access rules are auditable without reading code.

Deny by default: an unknown role raises, an unlisted label is denied,
and a role with no grants retrieves nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from app import config
from app.schema import ALL_LABELS

ROLES_PATH = config.ROOT / "roles.yaml"


@dataclass(frozen=True)
class Policy:
    role: str
    description: str
    allowed_labels: frozenset[str]
    allowed_doc_types: frozenset[str] | None = None
    allowed_periods_from: str | None = None

    def permits_label(self, label: str) -> bool:
        return label in self.allowed_labels

    def permits_doc_type(self, doc_type: str) -> bool:
        return self.allowed_doc_types is None or doc_type in self.allowed_doc_types

    def permits_period(self, period: str) -> bool:
        """Periods look like 'FY2025' or 'Q2 FY2025'. Compare fiscal years."""
        if self.allowed_periods_from is None:
            return True
        year = _fiscal_year(period)
        floor = _fiscal_year(self.allowed_periods_from)
        return year is None or floor is None or year >= floor

    def chroma_filter(self) -> dict:
        """Metadata filter applied by the vector store at query time.

        This is the primary enforcement: restricted chunks are never
        retrieved, so they never enter the model's context window.
        """
        clauses: list[dict] = [
            {"sensitivity_label": {"$in": sorted(self.allowed_labels)}}
        ]
        if self.allowed_doc_types is not None:
            clauses.append({"doc_type": {"$in": sorted(self.allowed_doc_types)}})
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def denied_labels(self) -> list[str]:
        """What this role cannot see — used to explain refusals honestly."""
        return sorted(ALL_LABELS - self.allowed_labels)


def _fiscal_year(period: str) -> int | None:
    import re
    match = re.search(r"FY(\d{4})", period or "")
    return int(match.group(1)) if match else None


@lru_cache(maxsize=1)
def _raw() -> dict:
    with ROLES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load(role: str) -> Policy:
    """Resolve a role name to its policy. Unknown roles are denied."""
    data = _raw()
    if role not in data:
        raise ValueError(
            f"Unknown role {role!r}. Known roles: {', '.join(sorted(data))}"
        )
    entry = data[role]

    labels = frozenset(entry.get("allowed_labels", []))
    unknown = labels - ALL_LABELS
    if unknown:
        raise ValueError(f"{role}: unknown label(s) in roles.yaml: {unknown}")

    doc_types = entry.get("allowed_doc_types")
    return Policy(
        role=role,
        description=entry.get("description", "").strip(),
        allowed_labels=labels,
        allowed_doc_types=frozenset(doc_types) if doc_types else None,
        allowed_periods_from=entry.get("allowed_periods_from"),
    )


def roles() -> list[str]:
    return sorted(_raw())


if __name__ == "__main__":
    for name in roles():
        p = load(name)
        print(f"\n{name}")
        print(f"  allows : {', '.join(sorted(p.allowed_labels))}")
        print(f"  denies : {', '.join(p.denied_labels()) or '(nothing)'}")
        print(f"  filter : {p.chroma_filter()}")