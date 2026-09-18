from __future__ import annotations

from dataclasses import dataclass

from .errors import ConformanceError


@dataclass(frozen=True)
class Feature:
    number: int
    key: str
    status: str
    note: str


FEATURES = {
    "table_formula": Feature(21, "table_formula", "beta", "Evaluate a safe formula subset and write display values."),
    "chart": Feature(26, "chart", "locked", "Editable chart conformance fixtures are required."),
    "note": Feature(29, "note", "experimental", "Footnote and endnote structure with reference checks."),
    "caption": Feature(30, "caption", "experimental", "Target, numbering, and caption structure."),
    "link": Feature(31, "link", "beta", "Bookmarks and validated internal or external hyperlinks."),
    "crossref": Feature(32, "crossref", "beta", "Static target IDs for number or text references."),
    "toc_index": Feature(33, "toc_index", "beta", "Linked TOC without page numbers and static index."),
    "changes": Feature(35, "changes", "locked", "Tracked-change conformance fixtures are required."),
    "security": Feature(40, "security", "locked", "An audited cryptographic adapter and test vectors are required."),
}


LOCKED_BLOCK_TYPES = {
    "chart": "chart",
    "tracked_change": "changes",
    "document_compare": "changes",
    "password": "security",
    "distribution": "security",
    "signature": "security",
}


def enforce_conformance(block_type: str) -> None:
    feature_key = LOCKED_BLOCK_TYPES.get(block_type)
    if not feature_key:
        return
    feature = FEATURES[feature_key]
    raise ConformanceError(
        f"Feature {feature.number} ({feature.key}) is currently {feature.status}: {feature.note}"
    )


def status_report() -> list[dict[str, object]]:
    return [feature.__dict__.copy() for feature in FEATURES.values()]
