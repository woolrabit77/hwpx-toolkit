from __future__ import annotations

from xml.etree import ElementTree as ET

from .equations import estimate_equation_box, normalize_equation
from .ids import IdRegistry
from .model import Document, Note, Paragraph, Run, Table


HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS = "http://www.hancom.co.kr/hwpml/2011/section"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HC = "http://www.hancom.co.kr/hwpml/2011/core"
OPF = "http://www.idpf.org/2007/opf"
OCF = "urn:oasis:names:tc:opendocument:xmlns:container"
XML = "http://www.w3.org/XML/1998/namespace"


STYLE_SPECS: list[dict[str, object]] = [
    {"name": "body", "size": 1000, "font": 0, "align": "JUSTIFY", "line": 160},
    {"name": "document-title", "size": 2200, "font": 1, "bold": True, "align": "CENTER", "line": 130, "before": 700, "after": 700, "keep": True},
    {"name": "subtitle", "size": 1300, "font": 1, "bold": True, "align": "CENTER", "line": 140, "after": 400},
    {"name": "meta", "size": 850, "font": 1, "align": "RIGHT", "line": 130},
    {"name": "heading-1", "size": 1600, "font": 1, "bold": True, "align": "LEFT", "line": 145, "before": 700, "after": 350, "keep": True},
    {"name": "heading-2", "size": 1300, "font": 1, "bold": True, "align": "LEFT", "line": 145, "before": 500, "after": 250, "keep": True},
    {"name": "heading-3", "size": 1100, "font": 1, "bold": True, "align": "LEFT", "line": 150, "before": 350, "after": 180, "keep": True},
    {"name": "body-small", "size": 850, "font": 0, "align": "JUSTIFY", "line": 145},
    {"name": "centered", "size": 1000, "font": 0, "align": "CENTER", "line": 150},
    {"name": "right", "size": 1000, "font": 0, "align": "RIGHT", "line": 150},
    {"name": "toc-1", "size": 1050, "font": 1, "bold": True, "align": "LEFT", "line": 155, "after": 100},
    {"name": "toc-2", "size": 950, "font": 0, "align": "LEFT", "line": 150, "left": 1200},
    {"name": "toc-3", "size": 900, "font": 0, "align": "LEFT", "line": 145, "left": 2400},
    {"name": "index", "size": 900, "font": 0, "align": "LEFT", "line": 145},
    {"name": "equation", "size": 1000, "font": 0, "align": "CENTER", "line": 155, "before": 150, "after": 150},
    {"name": "question", "size": 950, "font": 0, "align": "JUSTIFY", "line": 145, "after": 220, "keep": True},
    {"name": "instruction", "size": 850, "font": 1, "align": "LEFT", "line": 140, "after": 180},
    {"name": "form-label", "size": 900, "font": 1, "bold": True, "align": "LEFT", "line": 140},
    {"name": "table-cell", "size": 850, "font": 0, "align": "LEFT", "line": 135},
    {"name": "table-header", "size": 850, "font": 1, "bold": True, "align": "CENTER", "line": 135},
    {"name": "source-note", "size": 750, "font": 0, "align": "LEFT", "line": 130},
    {"name": "abstract-title", "size": 1050, "font": 1, "bold": True, "align": "CENTER", "line": 140, "before": 250, "after": 180},
    {"name": "abstract-body", "size": 850, "font": 0, "align": "JUSTIFY", "line": 145, "left": 600, "right": 600},
    {"name": "references", "size": 850, "font": 0, "align": "LEFT", "line": 140, "left": 700, "intent": -700},
    {"name": "section-label", "size": 900, "font": 1, "bold": True, "align": "LEFT", "line": 135, "after": 100},
]
STYLE_IDS = {str(spec["name"]): index for index, spec in enumerate(STYLE_SPECS)}

for prefix, namespace in {"hp": HP, "hs": HS, "hh": HH, "hc": HC, "opf": OPF}.items():
    ET.register_namespace(prefix, namespace)


def q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def serialize_document(document: Document, registry: IdRegistry) -> dict[str, bytes]:
    section, preview = _section(document, registry)
    parts = {
        "Contents/header.xml": _xml_bytes(_header()),
        "Contents/section0.xml": _xml_bytes(section),
        "Contents/content.hpf": _xml_bytes(_content(document)),
        "META-INF/container.xml": _container_xml(),
        "Preview/PrvText.txt": preview.encode("utf-8"),
    }
    return parts


def _header() -> ET.Element:
    root = ET.Element(q(HH, "head"), {"version": "1.5", "secCnt": "1"})
    ET.SubElement(
        root,
        q(HH, "beginNum"),
        {"page": "1", "footnote": "1", "endnote": "1", "pic": "1", "tbl": "1", "equation": "1"},
    )
    ref_list = ET.SubElement(root, q(HH, "refList"))
    languages = ("HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER")
    fontfaces = ET.SubElement(ref_list, q(HH, "fontfaces"), {"itemCnt": str(len(languages))})
    for language in languages:
        fontface = ET.SubElement(fontfaces, q(HH, "fontface"), {"lang": language, "fontCnt": "2"})
        ET.SubElement(fontface, q(HH, "font"), {"id": "0", "face": "함초롬바탕", "type": "TTF", "isEmbedded": "0"})
        ET.SubElement(fontface, q(HH, "font"), {"id": "1", "face": "함초롬돋움", "type": "TTF", "isEmbedded": "0"})
    border_fills = ET.SubElement(ref_list, q(HH, "borderFills"), {"itemCnt": "3"})
    for border_id, border_type, color in ((0, "NONE", "#000000"), (1, "SOLID", "#000000"), (2, "SOLID", "#808080")):
        border_fill = ET.SubElement(border_fills, q(HH, "borderFill"), {"id": str(border_id), "threeD": "0", "shadow": "0", "centerLine": "NONE", "breakCellSeparateLine": "0"})
        for edge in ("leftBorder", "rightBorder", "topBorder", "bottomBorder", "diagonal"):
            edge_type = "NONE" if edge == "diagonal" else border_type
            ET.SubElement(border_fill, q(HH, edge), {"type": edge_type, "width": "0.1 mm", "color": color})
    char_properties = ET.SubElement(ref_list, q(HH, "charProperties"), {"itemCnt": str(len(STYLE_SPECS))})
    all_hundred = {language.lower(): "100" for language in languages}
    all_zero_spacing = {language.lower(): "0" for language in languages}
    for style_id, spec in enumerate(STYLE_SPECS):
        char_pr = ET.SubElement(char_properties, q(HH, "charPr"), {"id": str(style_id), "height": str(spec.get("size", 1000)), "textColor": "#000000", "shadeColor": "#FFFFFF", "useFontSpace": "0", "useKerning": "0", "symMark": "NONE", "borderFillIDRef": "0"})
        font_ref = {language.lower(): str(spec.get("font", 0)) for language in languages}
        ET.SubElement(char_pr, q(HH, "fontRef"), font_ref)
        ET.SubElement(char_pr, q(HH, "ratio"), all_hundred)
        ET.SubElement(char_pr, q(HH, "spacing"), all_zero_spacing)
        ET.SubElement(char_pr, q(HH, "relSz"), all_hundred)
        ET.SubElement(char_pr, q(HH, "offset"), all_zero_spacing)
        if spec.get("bold"):
            ET.SubElement(char_pr, q(HH, "bold"))
    tab_properties = ET.SubElement(ref_list, q(HH, "tabProperties"), {"itemCnt": "1"})
    ET.SubElement(tab_properties, q(HH, "tabPr"), {"id": "0", "autoTabLeft": "0", "autoTabRight": "0"})
    ET.SubElement(ref_list, q(HH, "numberings"), {"itemCnt": "0"})
    ET.SubElement(ref_list, q(HH, "bullets"), {"itemCnt": "0"})
    para_properties = ET.SubElement(ref_list, q(HH, "paraProperties"), {"itemCnt": str(len(STYLE_SPECS))})
    for style_id, spec in enumerate(STYLE_SPECS):
        para_pr = ET.SubElement(para_properties, q(HH, "paraPr"), {"id": str(style_id), "tabPrIDRef": "0", "condense": "0", "fontLineHeight": "0", "snapToGrid": "1", "suppressLineNumbers": "0", "checked": "0"})
        ET.SubElement(para_pr, q(HH, "align"), {"horizontal": str(spec.get("align", "LEFT")), "vertical": "BASELINE"})
        ET.SubElement(para_pr, q(HH, "heading"), {"type": "NONE", "idRef": "0", "level": "0"})
        ET.SubElement(para_pr, q(HH, "breakSetting"), {"breakLatinWord": "KEEP_WORD", "breakNonLatinWord": "KEEP_WORD", "widowOrphan": "1", "keepWithNext": "1" if spec.get("keep") else "0", "keepLines": "0", "pageBreakBefore": "0", "lineWrap": "BREAK"})
        margin = ET.SubElement(para_pr, q(HH, "margin"))
        values = {
            "intent": int(spec.get("intent", 0)),
            "left": int(spec.get("left", 0)),
            "right": int(spec.get("right", 0)),
            "prev": int(spec.get("before", 0)),
            "next": int(spec.get("after", 0)),
        }
        for side, value in values.items():
            ET.SubElement(margin, q(HC, side), {"value": str(value), "unit": "HWPUNIT"})
        ET.SubElement(para_pr, q(HH, "lineSpacing"), {"type": "PERCENT", "value": str(spec.get("line", 160)), "unit": "CHAR"})
        ET.SubElement(para_pr, q(HH, "autoSpacing"), {"eAsianEng": "0", "eAsianNum": "0"})
    styles = ET.SubElement(ref_list, q(HH, "styles"), {"itemCnt": str(len(STYLE_SPECS))})
    for style_id, spec in enumerate(STYLE_SPECS):
        name = str(spec["name"])
        ET.SubElement(styles, q(HH, "style"), {"id": str(style_id), "type": "PARA", "name": name, "engName": name, "paraPrIDRef": str(style_id), "charPrIDRef": str(style_id), "nextStyleIDRef": "0", "langID": "1033", "lockForm": "0"})
    return root


def _content(document: Document) -> ET.Element:
    root = ET.Element(q(OPF, "package"), {"version": "3.0", "unique-identifier": "BookId"})
    metadata = ET.SubElement(root, q(OPF, "metadata"))
    ET.SubElement(metadata, q(OPF, "title")).text = document.title
    ET.SubElement(metadata, q(OPF, "creator")).text = document.author
    manifest = ET.SubElement(root, q(OPF, "manifest"))
    ET.SubElement(manifest, q(OPF, "item"), {"id": "header", "href": "header.xml", "media-type": "application/xml"})
    ET.SubElement(manifest, q(OPF, "item"), {"id": "section0", "href": "section0.xml", "media-type": "application/xml"})
    ET.SubElement(manifest, q(OPF, "item"), {"id": "preview", "href": "../Preview/PrvText.txt", "media-type": "text/plain"})
    spine = ET.SubElement(root, q(OPF, "spine"))
    ET.SubElement(spine, q(OPF, "itemref"), {"idref": "section0", "linear": "yes"})
    return root


def _container_xml() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<container xmlns="{OCF}" version="1.0"><rootfiles>'
        '<rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
        '<rootfile full-path="Preview/PrvText.txt" media-type="text/plain"/>'
        '</rootfiles></container>'
    ).encode("utf-8")


def _section(document: Document, registry: IdRegistry) -> tuple[ET.Element, str]:
    root = ET.Element(q(HS, "sec"))
    preview: list[str] = []
    paragraph_id = 1
    note_number = 1
    first_block = True
    for block in document.blocks:
        if isinstance(block, Paragraph):
            _write_paragraph(root, block, registry, paragraph_id, document.metadata, section_start=first_block)
            preview.extend(run.text for run in block.runs if run.text)
            paragraph_id += 1
        elif isinstance(block, Table):
            _write_table(root, block, registry, paragraph_id, document.metadata, section_start=first_block)
            if block.caption:
                preview.append(block.caption)
            for row in block.rows:
                preview.append("\t".join(cell.value for cell in row))
            paragraph_id += 1
        elif isinstance(block, Note):
            _write_note(root, block, paragraph_id, note_number, document.metadata, section_start=first_block)
            preview.append(block.text)
            paragraph_id += 1
            note_number += 1
        first_block = False
    if len(root) == 0:
        _write_paragraph(root, Paragraph(runs=[Run(text="")]), registry, 1, document.metadata, section_start=True)
    return root, "\n".join(preview)


def _new_paragraph(parent: ET.Element, paragraph_id: int, style_id: int = 0) -> ET.Element:
    return ET.SubElement(
        parent,
        q(HP, "p"),
        {
            "id": str(paragraph_id),
            "paraPrIDRef": str(style_id),
            "styleIDRef": str(style_id),
            "pageBreak": "0",
            "columnBreak": "0",
            "merged": "0",
        },
    )


def _write_paragraph(
    parent: ET.Element,
    paragraph: Paragraph,
    registry: IdRegistry,
    paragraph_id: int,
    metadata: dict[str, object],
    *,
    section_start: bool = False,
) -> None:
    style_id = _style_id(paragraph.style)
    p = _new_paragraph(parent, paragraph_id, style_id)
    p.set("paraPrIDRef", str(style_id))
    if section_start:
        _write_section_properties(p, metadata)
    if paragraph.bookmark:
        run = ET.SubElement(p, q(HP, "run"), {"charPrIDRef": str(style_id)})
        ctrl = ET.SubElement(run, q(HP, "ctrl"))
        ET.SubElement(ctrl, q(HP, "bookmark"), {"name": paragraph.bookmark})
    for run_model in paragraph.runs:
        _write_run(p, run_model, registry, style_id)
    if not paragraph.runs:
        run = ET.SubElement(p, q(HP, "run"), {"charPrIDRef": str(style_id)})
        ET.SubElement(run, q(HP, "t"))


def _write_run(parent: ET.Element, model: Run, registry: IdRegistry, style_id: int = 0) -> None:
    run = ET.SubElement(parent, q(HP, "run"), {"charPrIDRef": str(style_id)})
    if model.equation:
        width, height, baseline = estimate_equation_box(model.equation)
        equation = ET.SubElement(
            run,
            q(HP, "equation"),
            {
                "id": str(registry.allocate("equation") + 1000),
                "zOrder": "0",
                "numberingType": "EQUATION",
                "textWrap": "TOP_AND_BOTTOM",
                "textFlow": "BOTH_SIDES",
                "lock": "0",
                "version": "Equation Version 60",
                "baseLine": str(baseline),
                "textColor": "#000000",
                "baseUnit": "1000",
                "lineMode": "CHAR",
                "font": "HYhwpEQ",
            },
        )
        ET.SubElement(equation, q(HP, "sz"), {"width": str(width), "widthRelTo": "ABSOLUTE", "height": str(height), "heightRelTo": "ABSOLUTE", "protect": "0"})
        ET.SubElement(equation, q(HP, "pos"), {"treatAsChar": "1", "affectLSpacing": "0", "flowWithText": "1", "allowOverlap": "0", "holdAnchorAndSO": "0", "vertRelTo": "PARA", "horzRelTo": "PARA", "vertAlign": "TOP", "horzAlign": "LEFT", "vertOffset": "0", "horzOffset": "0"})
        ET.SubElement(equation, q(HP, "outMargin"), {"left": "56", "right": "56", "top": "0", "bottom": "0"})
        ET.SubElement(equation, q(HP, "script")).text = normalize_equation(model.equation)
        ET.SubElement(run, q(HP, "t"))
        return
    link = model.hyperlink
    if model.crossref:
        target_id = registry.require_target(model.crossref)
        model.text = model.text or str(target_id)
        link = f"#{model.crossref}"
    field_id: int | None = None
    if link:
        field_id = registry.allocate("field") + 2000
        ctrl = ET.SubElement(run, q(HP, "ctrl"))
        ET.SubElement(ctrl, q(HP, "fieldBegin"), {"id": str(field_id), "type": "HYPERLINK", "name": link, "editable": "0", "dirty": "0", "zorder": "-1", "fieldid": str(field_id)})
    text = ET.SubElement(run, q(HP, "t"))
    text.text = model.text
    if model.text[:1].isspace() or model.text[-1:].isspace():
        text.set(q(XML, "space"), "preserve")
    if field_id is not None:
        ctrl = ET.SubElement(run, q(HP, "ctrl"))
        ET.SubElement(ctrl, q(HP, "fieldEnd"), {"id": str(field_id)})


def _write_table(
    parent: ET.Element,
    table: Table,
    registry: IdRegistry,
    paragraph_id: int,
    metadata: dict[str, object],
    *,
    section_start: bool = False,
) -> None:
    p = _new_paragraph(parent, paragraph_id)
    if section_start:
        _write_section_properties(p, metadata)
    run = ET.SubElement(p, q(HP, "run"), {"charPrIDRef": "0"})
    if table.bookmark:
        ctrl = ET.SubElement(run, q(HP, "ctrl"))
        ET.SubElement(ctrl, q(HP, "bookmark"), {"name": table.bookmark})
    row_count = len(table.rows)
    col_count = max(len(row) for row in table.rows)
    table_width = _content_width(metadata)
    if _column_count(metadata) > 1:
        table_width = max(1000, (table_width - _column_gap(metadata)) // _column_count(metadata))
    if table.column_widths:
        total_weight = sum(table.column_widths)
        cell_widths = [max(1000, table_width * weight // total_weight) for weight in table.column_widths]
        cell_widths[-1] += table_width - sum(cell_widths)
    else:
        cell_widths = [max(1000, table_width // max(col_count, 1)) for _ in range(col_count)]
        cell_widths[-1] += table_width - sum(cell_widths)
    border_fill_id = {"plain": 0, "none": 0, "subtle": 2}.get(table.border_style, 1)
    tbl = ET.SubElement(
        run,
        q(HP, "tbl"),
        {"id": str(registry.allocate("table") + 3000), "zOrder": "0", "numberingType": "TABLE", "textWrap": "TOP_AND_BOTTOM", "textFlow": "BOTH_SIDES", "lock": "0", "pageBreak": "CELL", "repeatHeader": "1" if table.header_rows else "0", "rowCnt": str(row_count), "colCnt": str(col_count), "cellSpacing": "0", "borderFillIDRef": str(border_fill_id), "noAdjust": "0"},
    )
    ET.SubElement(tbl, q(HP, "sz"), {"width": str(table_width), "widthRelTo": "ABSOLUTE", "height": str(row_count * 2400), "heightRelTo": "ABSOLUTE", "protect": "0"})
    ET.SubElement(tbl, q(HP, "pos"), {"treatAsChar": "1", "affectLSpacing": "0", "flowWithText": "1", "allowOverlap": "0", "holdAnchorAndSO": "0", "vertRelTo": "PARA", "horzRelTo": "PARA", "vertAlign": "TOP", "horzAlign": "LEFT", "vertOffset": "0", "horzOffset": "0"})
    ET.SubElement(tbl, q(HP, "outMargin"), {"left": "0", "right": "0", "top": "0", "bottom": "0"})
    if table.caption:
        caption = ET.SubElement(tbl, q(HP, "caption"), {"side": "TOP", "fullSz": "1", "width": str(table_width), "gap": "300", "lastWidth": "0"})
        sub = ET.SubElement(caption, q(HP, "subList"), {"id": "", "textDirection": "HORIZONTAL", "lineWrap": "BREAK", "vertAlign": "TOP", "linkListIDRef": "0", "linkListNextIDRef": "0", "textWidth": str(table_width), "textHeight": "1200", "hasTextRef": "0", "hasNumRef": "0"})
        caption_style_id = _style_id("source-note")
        cp = _new_paragraph(sub, registry.allocate("caption_para") + 5000, caption_style_id)
        cr = ET.SubElement(cp, q(HP, "run"), {"charPrIDRef": str(caption_style_id)})
        ET.SubElement(cr, q(HP, "t")).text = table.caption
    ET.SubElement(tbl, q(HP, "inMargin"), {"left": "141", "right": "141", "top": "141", "bottom": "141"})
    for row_index, row_model in enumerate(table.rows):
        tr = ET.SubElement(tbl, q(HP, "tr"))
        for col_index, cell_model in enumerate(row_model):
            tc = ET.SubElement(tr, q(HP, "tc"), {"name": "", "header": "1" if row_index < table.header_rows else "0", "hasMargin": "1", "protect": "0", "editable": "0", "dirty": "0", "borderFillIDRef": str(border_fill_id)})
            ET.SubElement(tc, q(HP, "cellAddr"), {"colAddr": str(col_index), "rowAddr": str(row_index)})
            ET.SubElement(tc, q(HP, "cellSpan"), {"colSpan": "1", "rowSpan": "1"})
            cell_width = cell_widths[col_index]
            cell_style = cell_model.style
            if cell_style == "table-cell" and row_index < table.header_rows:
                cell_style = "table-header"
            cell_style_id = _style_id(cell_style)
            ET.SubElement(tc, q(HP, "cellSz"), {"width": str(cell_width), "height": "2400"})
            ET.SubElement(tc, q(HP, "cellMargin"), {"left": "141", "right": "141", "top": "141", "bottom": "141"})
            sub = ET.SubElement(tc, q(HP, "subList"), {"id": "", "textDirection": "HORIZONTAL", "lineWrap": "BREAK", "vertAlign": "CENTER", "linkListIDRef": "0", "linkListNextIDRef": "0", "textWidth": str(cell_width), "textHeight": "2400", "hasTextRef": "0", "hasNumRef": "0"})
            cp = _new_paragraph(sub, registry.allocate("cell_para") + 6000, cell_style_id)
            cp.set("paraPrIDRef", str(cell_style_id))
            cr = ET.SubElement(cp, q(HP, "run"), {"charPrIDRef": str(cell_style_id)})
            if cell_model.formula:
                fid = registry.allocate("field") + 2000
                ctrl = ET.SubElement(cr, q(HP, "ctrl"))
                ET.SubElement(ctrl, q(HP, "fieldBegin"), {"id": str(fid), "type": "FORMULA", "name": cell_model.formula, "editable": "1", "dirty": "0", "zorder": "-1", "fieldid": str(fid)})
                ET.SubElement(cr, q(HP, "t")).text = cell_model.value
                end = ET.SubElement(cr, q(HP, "ctrl"))
                ET.SubElement(end, q(HP, "fieldEnd"), {"id": str(fid)})
            else:
                ET.SubElement(cr, q(HP, "t")).text = cell_model.value
    ET.SubElement(run, q(HP, "t"))


def _write_note(
    parent: ET.Element,
    note: Note,
    paragraph_id: int,
    number: int,
    metadata: dict[str, object],
    *,
    section_start: bool = False,
) -> None:
    note_style_id = _style_id("source-note")
    p = _new_paragraph(parent, paragraph_id, note_style_id)
    if section_start:
        _write_section_properties(p, metadata)
    run = ET.SubElement(p, q(HP, "run"), {"charPrIDRef": str(note_style_id)})
    ctrl = ET.SubElement(run, q(HP, "ctrl"))
    element_name = "footNote" if note.kind == "footnote" else "endNote"
    note_element = ET.SubElement(ctrl, q(HP, element_name), {"number": str(number), "instId": str(number)})
    sub = ET.SubElement(note_element, q(HP, "subList"), {"id": "", "textDirection": "HORIZONTAL", "lineWrap": "BREAK", "vertAlign": "TOP", "linkListIDRef": "0", "linkListNextIDRef": "0", "textWidth": "42520", "textHeight": "1200", "hasTextRef": "0", "hasNumRef": "0"})
    np = _new_paragraph(sub, paragraph_id + 10000, note_style_id)
    nr = ET.SubElement(np, q(HP, "run"), {"charPrIDRef": str(note_style_id)})
    ET.SubElement(nr, q(HP, "t")).text = note.text
    ET.SubElement(run, q(HP, "t"))


def _write_section_properties(paragraph: ET.Element, metadata: dict[str, object]) -> None:
    layout = metadata.get("layout") if isinstance(metadata.get("layout"), dict) else {}
    assert isinstance(layout, dict)
    column_count = _column_count(metadata)
    column_gap = _column_gap(metadata)
    run = ET.SubElement(paragraph, q(HP, "run"), {"charPrIDRef": "0"})
    sec_pr = ET.SubElement(
        run,
        q(HP, "secPr"),
        {
            "id": "0",
            "textDirection": "HORIZONTAL",
            "spaceColumns": str(column_gap),
            "tabStop": "8000",
            "tabStopVal": "8000",
            "tabStopUnit": "HWPUNIT",
            "outlineShapeIDRef": "0",
            "memoShapeIDRef": "0",
            "textVerticalWidthHead": "0",
            "masterPageCnt": "0",
        },
    )
    page_pr = ET.SubElement(
        sec_pr,
        q(HP, "pagePr"),
        {"landscape": "NARROWLY", "width": str(_mm(float(layout.get("page_width_mm", 210)))), "height": str(_mm(float(layout.get("page_height_mm", 297)))), "gutterType": "LEFT_ONLY"},
    )
    ET.SubElement(
        page_pr,
        q(HP, "margin"),
        {"left": str(_mm(float(layout.get("left_mm", 25)))), "right": str(_mm(float(layout.get("right_mm", 25)))), "top": str(_mm(float(layout.get("top_mm", 20)))), "bottom": str(_mm(float(layout.get("bottom_mm", 18)))), "header": str(_mm(float(layout.get("header_mm", 12)))), "footer": str(_mm(float(layout.get("footer_mm", 12)))), "gutter": "0"},
    )
    ctrl = ET.SubElement(run, q(HP, "ctrl"))
    ET.SubElement(
        ctrl,
        q(HP, "colPr"),
        {"id": "0", "type": "NEWSPAPER", "layout": "LEFT", "colCount": str(column_count), "sameSz": "1", "sameGap": str(column_gap)},
    )


def _style_id(name: str) -> int:
    return STYLE_IDS.get(name, STYLE_IDS["body"])


def _mm(value: float) -> int:
    return max(0, round(value * 283.466))


def _column_count(metadata: dict[str, object]) -> int:
    layout = metadata.get("layout") if isinstance(metadata.get("layout"), dict) else {}
    assert isinstance(layout, dict)
    try:
        return max(1, min(4, int(layout.get("columns", 1))))
    except (TypeError, ValueError):
        return 1


def _column_gap(metadata: dict[str, object]) -> int:
    layout = metadata.get("layout") if isinstance(metadata.get("layout"), dict) else {}
    assert isinstance(layout, dict)
    try:
        return _mm(float(layout.get("column_gap_mm", 8)))
    except (TypeError, ValueError):
        return _mm(8)


def _content_width(metadata: dict[str, object]) -> int:
    layout = metadata.get("layout") if isinstance(metadata.get("layout"), dict) else {}
    assert isinstance(layout, dict)
    page = _mm(float(layout.get("page_width_mm", 210)))
    left = _mm(float(layout.get("left_mm", 25)))
    right = _mm(float(layout.get("right_mm", 25)))
    return max(1000, page - left - right)


def _xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
