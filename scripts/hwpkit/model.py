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
    tabs: list[dict[str, object]] = field(default_factory=list)
    indent: dict[str, int] = field(default_factory=dict)
    list_type: str | None = None
    list_level: int = 1
    list_id: int | None = None
    list_start: int = 1
    list_format: str = "DIGIT"
    bullet_char: str = "•"


@dataclass
class ImageAsset:
    source: str
    data: bytes
    extension: str
    media_type: str
    width_px: int
    height_px: int
    width_mm: float | None = None
    height_mm: float | None = None
    alt: str = ""


@dataclass
class TableCell:
    value: str = ""
    formula: str | None = None
    style: str = "table-cell"
    image: ImageAsset | None = None
    row_span: int = 1
    col_span: int = 1
    row_index: int = 0
    col_index: int = 0
    shading: str | None = None


@dataclass
class Table:
    rows: list[list[TableCell]] = field(default_factory=list)
    caption: str | None = None
    bookmark: str | None = None
    column_widths: list[int] = field(default_factory=list)
    header_rows: int = 1
    border_style: str = "grid"
    row_heights_mm: list[float] = field(default_factory=list)
    shading: str | None = None
    split: str = "cell"
    repeat_header: bool = True
    col_count: int = 0


@dataclass
class Note:
    kind: str
    text: str


@dataclass
class PageBreak:
    """A genuine paragraph-level page break, not a run of padding text."""

    kind: str = "page"


@dataclass
class Section:
    blocks: list[Any] = field(default_factory=list)
    header: list[Paragraph] = field(default_factory=list)
    footer: list[Paragraph] = field(default_factory=list)
    page_number: dict[str, str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    title: str = ""
    author: str = ""
    blocks: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    template_id: str | None = None
    sections: list[Section] = field(default_factory=list)
