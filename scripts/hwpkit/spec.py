from __future__ import annotations

from pathlib import Path
from struct import unpack
from typing import Any
from urllib.parse import urlparse

from .errors import SpecError
from .features import enforce_conformance
from .formulas import evaluate_formula
from .ids import IdRegistry
from .model import Document, ImageAsset, Note, Paragraph, Run, Table, TableCell
from .templates import apply_template


ALLOWED_SCHEMES = {"http", "https", "mailto"}


def parse_document_spec(raw: dict[str, Any], *, base_dir: Path | None = None) -> tuple[Document, IdRegistry]:
    if not isinstance(raw, dict):
        raise SpecError("The top-level document spec must be an object.")
    raw, template_id = apply_template(raw)
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise SpecError("metadata must be an object.")
    blocks = raw.get("blocks")
    if blocks is None:
        sections = raw.get("sections") or []
        if not isinstance(sections, list):
            raise SpecError("sections must be an array.")
        blocks = []
        for section in sections:
            if not isinstance(section, dict) or not isinstance(section.get("blocks", []), list):
                raise SpecError("Every section must contain a blocks array.")
            blocks.extend(section.get("blocks", []))
    if not isinstance(blocks, list):
        raise SpecError("blocks must be an array.")

    registry = IdRegistry()
    headings: list[tuple[int, str, str]] = []
    parsed_blocks: list[object] = []

    # Targets must be known before cross-reference resolution.
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise SpecError(f"blocks[{index}] must be an object.")
        block_type = str(block.get("type", "paragraph"))
        enforce_conformance(block_type)
        bookmark = block.get("bookmark")
        if bookmark:
            registry.register_target(str(bookmark), "bookmark")
        if block_type == "heading":
            level = _positive_int(block.get("level", 1), f"blocks[{index}].level")
            if level > 9:
                raise SpecError("Heading levels must be between 1 and 9.")
            text = str(block.get("text", ""))
            target = str(bookmark or f"heading-{index + 1}")
            if not bookmark:
                registry.register_target(target, "bookmark")
                block["bookmark"] = target
            headings.append((level, text, target))

    for index, block in enumerate(blocks):
        block_type = str(block.get("type", "paragraph"))
        if block_type in {"paragraph", "heading"}:
            parsed_blocks.append(_parse_paragraph(block, registry, heading=block_type == "heading"))
        elif block_type == "equation":
            script = str(block.get("script", "")).strip()
            if not script:
                raise SpecError(f"blocks[{index}].script must not be empty.")
            parsed_blocks.append(Paragraph(runs=[Run(equation=script)], style="equation"))
        elif block_type == "table":
            parsed_blocks.append(_parse_table(block, base_dir=base_dir))
        elif block_type in {"footnote", "endnote"}:
            text = str(block.get("text", "")).strip()
            if not text:
                raise SpecError(f"blocks[{index}] note text must not be empty.")
            parsed_blocks.append(Note(kind=block_type, text=text))
        elif block_type == "toc":
            levels = block.get("levels", [1, 2, 3])
            if not isinstance(levels, list) or not all(isinstance(v, int) for v in levels):
                raise SpecError("toc.levels must be an array of integers.")
            for level, text, target in headings:
                if level in levels:
                    parsed_blocks.append(
                        Paragraph(
                            runs=[Run(text=("  " * (level - 1)) + text, hyperlink=f"#{target}")],
                            style=f"toc-{level}",
                        )
                    )
        elif block_type == "index":
            terms = block.get("terms", [])
            if not isinstance(terms, list):
                raise SpecError("index.terms must be an array.")
            for term in sorted({str(term).strip() for term in terms if str(term).strip()}):
                parsed_blocks.append(Paragraph(runs=[Run(text=term)], style="index"))
        else:
            raise SpecError(f"Unsupported block type: {block_type}")

    document = Document(
        title=str(metadata.get("title", "")),
        author=str(metadata.get("author", "")),
        blocks=parsed_blocks,
        metadata=dict(metadata),
        template_id=template_id,
    )
    return document, registry


def _parse_paragraph(block: dict[str, Any], registry: IdRegistry, *, heading: bool) -> Paragraph:
    runs_raw = block.get("runs")
    runs: list[Run] = []
    if runs_raw is None:
        runs_raw = [{"text": str(block.get("text", ""))}]
    if not isinstance(runs_raw, list):
        raise SpecError("paragraph.runs must be an array.")
    for run_raw in runs_raw:
        if isinstance(run_raw, str):
            runs.append(Run(text=run_raw))
            continue
        if not isinstance(run_raw, dict):
            raise SpecError("Each run must be a string or an object.")
        hyperlink = run_raw.get("hyperlink")
        crossref = run_raw.get("crossref")
        if hyperlink:
            _validate_link(str(hyperlink), registry)
        if crossref:
            registry.require_target(str(crossref))
        runs.append(
            Run(
                text=str(run_raw.get("text", "")),
                hyperlink=str(hyperlink) if hyperlink else None,
                crossref=str(crossref) if crossref else None,
                equation=str(run_raw.get("equation")) if run_raw.get("equation") else None,
            )
        )
    level = _positive_int(block.get("level", 1), "heading.level") if heading else None
    return Paragraph(
        runs=runs,
        style=f"heading-{level}" if heading else str(block.get("style", "body")),
        heading_level=level,
        bookmark=str(block.get("bookmark")) if block.get("bookmark") else None,
        index_terms=[str(value) for value in block.get("index_terms", [])],
    )


def _parse_table(block: dict[str, Any], *, base_dir: Path | None = None) -> Table:
    rows = block.get("rows", [])
    if not isinstance(rows, list) or not rows:
        raise SpecError("table.rows must be a non-empty array.")
    if not all(isinstance(row, list) and row for row in rows):
        raise SpecError("Every table row must be a non-empty array.")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise SpecError("All table rows must have the same number of columns.")
    column_widths = block.get("column_widths") or []
    if column_widths:
        if not isinstance(column_widths, list) or len(column_widths) != width:
            raise SpecError("table.column_widths must match the table column count.")
        if any(not isinstance(value, int) or value <= 0 for value in column_widths):
            raise SpecError("table.column_widths values must be positive integers.")
    header_rows = int(block.get("header_rows", 1))
    if header_rows < 0 or header_rows > len(rows):
        raise SpecError("table.header_rows is outside the valid row range.")
    row_heights_raw = block.get("row_heights_mm") or []
    if row_heights_raw:
        if not isinstance(row_heights_raw, list) or len(row_heights_raw) != len(rows):
            raise SpecError("table.row_heights_mm must match the table row count.")
        try:
            row_heights_mm = [float(value) for value in row_heights_raw]
        except (TypeError, ValueError) as exc:
            raise SpecError("table.row_heights_mm values must be positive numbers.") from exc
        if any(value <= 0 for value in row_heights_mm):
            raise SpecError("table.row_heights_mm values must be positive numbers.")
    else:
        row_heights_mm = []
    parsed: list[list[TableCell]] = []
    for row in rows:
        parsed_row: list[TableCell] = []
        for cell in row:
            if isinstance(cell, dict) and cell.get("image"):
                image_raw = cell["image"]
                if isinstance(image_raw, dict) and not str(image_raw.get("path", "")).strip():
                    parsed_row.append(
                        TableCell(value=str(cell.get("value", "")), style=str(cell.get("style", "table-cell")))
                    )
                    continue
                parsed_row.append(
                    TableCell(
                        value=str(cell.get("value", "")),
                        style=str(cell.get("style", "table-cell")),
                        image=_parse_image(image_raw, base_dir=base_dir),
                    )
                )
            elif isinstance(cell, dict) and cell.get("formula"):
                formula = str(cell["formula"])
                result = evaluate_formula(formula, rows)
                display = str(int(result)) if result.is_integer() else f"{result:.10g}"
                parsed_row.append(TableCell(value=display, formula=formula, style=str(cell.get("style", "table-cell"))))
            else:
                value = cell.get("value", "") if isinstance(cell, dict) else cell
                style = str(cell.get("style", "table-cell")) if isinstance(cell, dict) else "table-cell"
                parsed_row.append(TableCell(value=str(value), style=style))
        parsed.append(parsed_row)
    return Table(
        rows=parsed,
        caption=str(block.get("caption")) if block.get("caption") else None,
        bookmark=str(block.get("bookmark")) if block.get("bookmark") else None,
        column_widths=list(column_widths),
        header_rows=header_rows,
        border_style=str(block.get("border_style", "grid")),
        row_heights_mm=row_heights_mm,
    )


def _parse_image(raw: object, *, base_dir: Path | None) -> ImageAsset:
    if not isinstance(raw, dict):
        raise SpecError("table cell image must be an object.")
    source = str(raw.get("path", "")).strip()
    if not source:
        raise SpecError("table cell image.path must not be empty.")
    path = Path(source)
    if not path.is_absolute():
        path = (base_dir or Path.cwd()) / path
    path = path.resolve()
    if not path.is_file():
        raise SpecError(f"Image file does not exist: {path}")
    data = path.read_bytes()
    extension, media_type, width_px, height_px = _image_info(data)
    width_mm = _positive_float_or_none(raw.get("width_mm"), "image.width_mm")
    height_mm = _positive_float_or_none(raw.get("height_mm"), "image.height_mm")
    return ImageAsset(
        source=str(path),
        data=data,
        extension=extension,
        media_type=media_type,
        width_px=width_px,
        height_px=height_px,
        width_mm=width_mm,
        height_mm=height_mm,
        alt=str(raw.get("alt", "")),
    )


def _image_info(data: bytes) -> tuple[str, str, int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = unpack(">II", data[16:24])
        return "png", "image/png", width, height
    if data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            segment_length = unpack(">H", data[index:index + 2])[0]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                if index + 7 > len(data):
                    break
                height, width = unpack(">HH", data[index + 3:index + 7])
                return "jpg", "image/jpeg", width, height
            if segment_length < 2:
                break
            index += segment_length
    raise SpecError("Only valid PNG and JPEG images are supported.")


def _positive_float_or_none(value: object, name: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{name} must be a positive number.") from exc
    if parsed <= 0:
        raise SpecError(f"{name} must be a positive number.")
    return parsed


def _validate_link(value: str, registry: IdRegistry) -> None:
    if value.startswith("#"):
        registry.require_target(value[1:])
        return
    parsed = urlparse(value)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SpecError(f"Unsupported hyperlink scheme: {value}")


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise SpecError(f"{name} must be a positive integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{name} must be a positive integer.") from exc
    if parsed < 1:
        raise SpecError(f"{name} must be a positive integer.")
    return parsed
