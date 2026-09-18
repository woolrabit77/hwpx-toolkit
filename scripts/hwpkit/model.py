from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Run:
    text: str = ""
    bookmark: str | None = None
    hyperlink: str | None = None
    crossref: str | None = None
    equation: str | None = None


@dataclass
class Paragraph:
    runs: list[Run] = field(default_factory=list)
    style: str = "body"
    heading_level: int | None = None
    bookmark: str | None = None
    index_terms: list[str] = field(default_factory=list)


@dataclass
class TableCell:
    value: str = ""
    formula: str | None = None
    style: str = "table-cell"


@dataclass
class Table:
    rows: list[list[TableCell]] = field(default_factory=list)
    caption: str | None = None
    bookmark: str | None = None
    column_widths: list[int] = field(default_factory=list)
    header_rows: int = 1
    border_style: str = "grid"


@dataclass
class Note:
    kind: str
    text: str


@dataclass
class Document:
    title: str = ""
    author: str = ""
    blocks: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    template_id: str | None = None
