from __future__ import annotations

from pathlib import Path
from struct import unpack
from typing import Any
from urllib.parse import urlparse

from .errors import SpecError
from .features import enforce_conformance
from .formulas import evaluate_formula
from .ids import IdRegistry
from .layouts import resolve_layout
from .model import Document, ImageAsset, Note, PageBreak, Paragraph, Run, Section, Table, TableCell
from .templates import apply_template


ALLOWED_SCHEMES = {"http", "https", "mailto"}
TABLE_BORDER_STYLES = {"none", "plain", "subtle", "grid", "form"}
TAB_TYPES = {"LEFT", "CENTER", "RIGHT", "DECIMAL"}
TAB_LEADERS = {"NONE", "SOLID", "DOTTED", "DASHED"}
NUMBER_FORMATS = {
    "DIGIT",
    "CIRCLED_DIGIT",
    "HANGUL_SYLLABLE",
    "LATIN_SMALL",
    "LATIN_CAPITAL",
    "ROMAN_SMALL",
    "ROMAN_CAPITAL",
}
PAGE_NUMBER_POSITIONS = {"TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "BOTTOM_LEFT", "BOTTOM_CENTER", "BOTTOM_RIGHT"}
PAGE_NUMBER_FORMATS = {"DIGIT", "ROMAN_SMALL", "ROMAN_CAPITAL", "LATIN_SMALL", "LATIN_CAPITAL"}


def parse_document_spec(raw: dict[str, Any], *, base_dir: Path | None = None) -> tuple[Document, IdRegistry]:
    if not isinstance(raw, dict):
        raise SpecError("The top-level document spec must be an object.")
    raw, template_id = apply_template(raw)
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise SpecError("metadata must be an object.")
    try:
        resolve_layout(metadata)
    except ValueError as exc:
        raise SpecError(str(exc)) from exc
    raw_sections = raw.get("sections")
    blocks = raw.get("blocks")
    if raw_sections is not None and blocks is not None:
        raise SpecError("Specify either blocks or sections, not both.")
    if raw_sections is not None:
        if not isinstance(raw_sections, list) or not raw_sections:
            raise SpecError("sections must be a non-empty array.")
        section_inputs = raw_sections
    else:
        if blocks is None:
            blocks = []
        if not isinstance(blocks, list):
            raise SpecError("blocks must be an array.")
        section_inputs = _split_section_breaks(blocks)
        top_section = section_inputs[0]
        for key in ("header", "footer", "page_number", "pageNum"):
            if key in raw:
                top_section[key] = raw[key]
        if isinstance(raw.get("section_metadata"), dict):
            top_section["metadata"] = raw["section_metadata"]
    for section_index, section in enumerate(section_inputs):
        if not isinstance(section, dict) or not isinstance(section.get("blocks", []), list):
            raise SpecError(f"sections[{section_index}] must contain a blocks array.")

    registry = IdRegistry()
    headings: list[tuple[int, str, str]] = []
    parsed_blocks: list[object] = []

    all_raw_blocks = [block for section in section_inputs for block in section.get("blocks", [])]
    # Targets must be known before cross-reference resolution, including targets
    # that appear after an explicit section break.
    for index, block in enumerate(all_raw_blocks):
        if not isinstance(block, dict):
            raise SpecError(f"blocks[{index}] must be an object.")
        block_type = str(block.get("type", "paragraph"))
        enforce_conformance(block_type)
        if block_type in {"page_break", "section_break"}:
            continue
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

    sections: list[Section] = []
    for section_index, section_input in enumerate(section_inputs):
        if not isinstance(section_input, dict) or not isinstance(section_input.get("blocks", []), list):
            raise SpecError(f"sections[{section_index}] must contain a blocks array.")
        section_metadata = dict(metadata)
        overrides = section_input.get("metadata") or {}
        if not isinstance(overrides, dict):
            raise SpecError(f"sections[{section_index}].metadata must be an object.")
        section_metadata.update(overrides)
        try:
            resolve_layout(section_metadata)
        except ValueError as exc:
            raise SpecError(str(exc)) from exc
        parsed_section: list[object] = []
        for block_index, block in enumerate(section_input.get("blocks", [])):
            if not isinstance(block, dict):
                raise SpecError(f"sections[{section_index}].blocks[{block_index}] must be an object.")
            parsed = _parse_block(block, registry, headings, base_dir=base_dir)
            if isinstance(parsed, list):
                parsed_section.extend(parsed)
            else:
                parsed_section.append(parsed)
        sections.append(
            Section(
                blocks=parsed_section,
                header=_parse_header_footer(section_input.get("header"), registry, headings, base_dir=base_dir, name=f"sections[{section_index}].header"),
                footer=_parse_header_footer(section_input.get("footer"), registry, headings, base_dir=base_dir, name=f"sections[{section_index}].footer"),
                page_number=_parse_page_number(section_input.get("page_number", section_input.get("pageNum")), f"sections[{section_index}].page_number"),
                metadata=section_metadata,
            )
        )
        parsed_blocks.extend(parsed_section)

    document = Document(
        title=str(metadata.get("title", "")),
        author=str(metadata.get("author", "")),
        blocks=parsed_blocks,
        metadata=dict(metadata),
        template_id=template_id,
        sections=sections,
    )
    return document, registry


def _split_section_breaks(blocks: list[object]) -> list[dict[str, Any]]:
    """Convert explicit section-break blocks into real section descriptors."""
    sections: list[dict[str, Any]] = [{"blocks": []}]
    for index, value in enumerate(blocks):
        if not isinstance(value, dict):
            sections[-1]["blocks"].append(value)
            continue
        block_type = str(value.get("type", "paragraph"))
        if block_type != "section_break":
            sections[-1]["blocks"].append(value)
            continue
        if any(key in value for key in ("text", "runs", "style")):
            raise SpecError(f"blocks[{index}] section_break cannot contain paragraph content.")
        next_section = {key: value[key] for key in ("header", "footer", "page_number", "pageNum", "metadata") if key in value}
        next_section["blocks"] = []
        sections.append(next_section)
    return sections


def _parse_block(block: dict[str, Any], registry: IdRegistry, headings: list[tuple[int, str, str]], *, base_dir: Path | None) -> object:
    block_type = str(block.get("type", "paragraph"))
    if block_type in {"page_break", "section_break"}:
        if block_type == "section_break":
            raise SpecError("section_break is only valid in the top-level blocks array.")
        return PageBreak()
    if block_type in {"paragraph", "heading"}:
        return _parse_paragraph(block, registry, heading=block_type == "heading")
    if block_type == "equation":
        script = str(block.get("script", "")).strip()
        if not script:
            raise SpecError("equation.script must not be empty.")
        return Paragraph(runs=[Run(equation=script)], style="equation")
    if block_type == "table":
        return _parse_table(block, base_dir=base_dir)
    if block_type in {"footnote", "endnote"}:
        text = str(block.get("text", "")).strip()
        if not text:
            raise SpecError(f"{block_type} text must not be empty.")
        return Note(kind=block_type, text=text)
    if block_type == "toc":
        levels = block.get("levels", [1, 2, 3])
        if not isinstance(levels, list) or not all(isinstance(v, int) for v in levels):
            raise SpecError("toc.levels must be an array of integers.")
        return [Paragraph(runs=[Run(text=("  " * (level - 1)) + text, hyperlink=f"#{target}")], style=f"toc-{level}") for level, text, target in headings if level in levels]
    if block_type == "index":
        terms = block.get("terms", [])
        if not isinstance(terms, list):
            raise SpecError("index.terms must be an array.")
        return [Paragraph(runs=[Run(text=term)], style="index") for term in sorted({str(term).strip() for term in terms if str(term).strip()})]
    raise SpecError(f"Unsupported block type: {block_type}")


def _parse_header_footer(raw: object, registry: IdRegistry, headings: list[tuple[int, str, str]], *, base_dir: Path | None, name: str) -> list[Paragraph]:
    if raw in (None, ""):
        return []
    if isinstance(raw, str):
        raw = [{"type": "paragraph", "text": raw}]
    elif isinstance(raw, dict):
        if "blocks" in raw:
            raw = raw["blocks"]
        elif "text" in raw or "runs" in raw:
            raw = [dict(raw, type="paragraph")]
        else:
            raise SpecError(f"{name} must contain text, runs, or blocks.")
    if not isinstance(raw, list):
        raise SpecError(f"{name} must be a string, object, or array.")
    result: list[Paragraph] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            item = {"type": "paragraph", "text": item}
        if not isinstance(item, dict) or str(item.get("type", "paragraph")) not in {"paragraph", "heading"}:
            raise SpecError(f"{name}[{index}] supports only paragraph and heading blocks.")
        parsed = _parse_paragraph(item, registry, heading=str(item.get("type", "paragraph")) == "heading")
        result.append(parsed)
    return result


def _parse_page_number(raw: object, name: str) -> dict[str, str] | None:
    if raw in (None, False):
        return None
    config: dict[str, object] = {} if raw is True else raw if isinstance(raw, dict) else {"position": raw}
    position = str(config.get("position", "BOTTOM_CENTER")).upper()
    number_format = str(config.get("format", config.get("formatType", "DIGIT"))).upper()
    side_char = str(config.get("side_char", config.get("sideChar", "")))
    if position not in PAGE_NUMBER_POSITIONS:
        raise SpecError(f"{name}.position must be one of: {', '.join(sorted(PAGE_NUMBER_POSITIONS))}.")
    if number_format not in PAGE_NUMBER_FORMATS:
        raise SpecError(f"{name}.format must be one of: {', '.join(sorted(PAGE_NUMBER_FORMATS))}.")
    if len(side_char) > 2:
        raise SpecError(f"{name}.side_char must contain at most two characters.")
    start = config.get("start")
    if start is not None and (isinstance(start, bool) or not isinstance(start, int) or start < 1):
        raise SpecError(f"{name}.start must be a positive JSON integer.")
    result = {"position": position, "format": number_format, "side_char": side_char}
    if start is not None:
        result["start"] = str(start)
    return result


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
    tabs = _parse_tabs(block.get("tabs", block.get("tab_stops", [])))
    indent = _parse_indent(block)
    list_type, list_level, list_start, list_format, bullet_char = _parse_list(block)
    return Paragraph(
        runs=runs,
        style=f"heading-{level}" if heading else str(block.get("style", "body")),
        heading_level=level,
        bookmark=str(block.get("bookmark")) if block.get("bookmark") else None,
        index_terms=[str(value) for value in block.get("index_terms", [])],
        tabs=tabs,
        indent=indent,
        list_type=list_type,
        list_level=list_level,
        list_start=list_start,
        list_format=list_format,
        bullet_char=bullet_char,
    )


def _parse_tabs(raw: object) -> list[dict[str, object]]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise SpecError("paragraph.tabs must be an array.")
    parsed: list[dict[str, object]] = []
    previous = -1
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            raise SpecError(f"paragraph.tabs[{index}] must be an object.")
        position = _strict_int(value.get("position", value.get("pos", 0)), f"paragraph.tabs[{index}].position")
        if position < 0 or position <= previous:
            raise SpecError("paragraph tab positions must be strictly increasing non-negative integers.")
        tab_type = str(value.get("type", "LEFT")).upper()
        leader = str(value.get("leader", "NONE")).upper()
        if tab_type not in TAB_TYPES:
            raise SpecError(f"paragraph.tabs[{index}].type must be one of: {', '.join(sorted(TAB_TYPES))}.")
        if leader not in TAB_LEADERS:
            raise SpecError(f"paragraph.tabs[{index}].leader must be one of: {', '.join(sorted(TAB_LEADERS))}.")
        parsed.append({"position": position, "type": tab_type, "leader": leader})
        previous = position
    return parsed


def _parse_indent(block: dict[str, Any]) -> dict[str, int]:
    raw = block.get("indent", {})
    if raw in (None, {}):
        raw = {}
    if not isinstance(raw, dict):
        raise SpecError("paragraph.indent must be an object.")
    aliases = {
        "left": "left",
        "right": "right",
        "first_line": "first_line",
        "firstLine": "first_line",
        "hanging": "first_line",
    }
    parsed: dict[str, int] = {}
    for source, target in aliases.items():
        if source not in raw:
            continue
        parsed[target] = _strict_int(raw[source], f"paragraph.indent.{source}")
    for source, target in (("indent_left", "left"), ("indent_right", "right"), ("first_line_indent", "first_line")):
        if source in block and target not in parsed:
            parsed[target] = _strict_int(block[source], source)
    return parsed


def _parse_list(block: dict[str, Any]) -> tuple[str | None, int, int, str, str]:
    candidates: list[tuple[str, object]] = []
    for key in ("bullet", "numbering", "list"):
        if key in block and block[key] not in (None, False):
            candidates.append((key, block[key]))
    if len(candidates) > 1:
        raise SpecError("A paragraph may specify only one of bullet, numbering, or list.")
    if not candidates:
        return None, 1, 1, "DIGIT", "•"
    key, raw = candidates[0]
    if key == "list":
        if not isinstance(raw, dict):
            raise SpecError("paragraph.list must be an object.")
        kind = str(raw.get("type", raw.get("kind", "numbering"))).lower()
        config = raw
    elif isinstance(raw, dict):
        kind = "bullet" if key == "bullet" else "numbering"
        config = raw
    elif raw is True:
        kind = "bullet" if key == "bullet" else "numbering"
        config = {}
    else:
        raise SpecError(f"paragraph.{key} must be true or an object.")
    if kind in {"number", "numbered", "ordered"}:
        kind = "numbering"
    if kind not in {"bullet", "numbering"}:
        raise SpecError("paragraph.list.type must be 'bullet' or 'numbering'.")
    level = _strict_int(config.get("level", 1), "List level")
    if level < 1 or level > 10:
        raise SpecError("List level must be between 1 and 10.")
    start = _strict_int(config.get("start", 1), "List start")
    if start < 1:
        raise SpecError("List start must be a positive integer.")
    if kind == "bullet":
        char = str(config.get("char", config.get("bullet_char", "•")))
        if len(char) != 1:
            raise SpecError("Bullet char must contain exactly one Unicode character.")
        return kind, level, start, "DIGIT", char
    list_format = str(config.get("format", config.get("number_format", "DIGIT"))).upper()
    if list_format not in NUMBER_FORMATS:
        raise SpecError(f"Number format must be one of: {', '.join(sorted(NUMBER_FORMATS))}.")
    return kind, level, start, list_format, "•"


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
    border_style = str(block.get("border_style", "grid"))
    if border_style not in TABLE_BORDER_STYLES:
        allowed = ", ".join(sorted(TABLE_BORDER_STYLES))
        raise SpecError(f"table.border_style must be one of: {allowed}")
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
        border_style=border_style,
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


def _strict_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SpecError(f"{name} must be a JSON integer.")
    return value


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
