from __future__ import annotations

from xml.etree import ElementTree as ET

from .equations import estimate_equation_box, normalize_equation
from .ids import IdRegistry
from .layouts import resolve_layout
from .model import Document, ImageAsset, Note, PageBreak, Paragraph, Run, Section, Table


HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS = "http://www.hancom.co.kr/hwpml/2011/section"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HC = "http://www.hancom.co.kr/hwpml/2011/core"
OPF = "http://www.idpf.org/2007/opf/"
OCF = "urn:oasis:names:tc:opendocument:xmlns:container"
HV = "http://www.hancom.co.kr/hwpml/2011/version"
HA = "http://www.hancom.co.kr/hwpml/2011/app"
CONFIG = "urn:oasis:names:tc:opendocument:xmlns:config:1.0"
ODF_MANIFEST = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
PKG_META = "http://www.hancom.co.kr/hwpml/2016/meta/pkg#"
XML = "http://www.w3.org/XML/1998/namespace"
BLACK = "#000000"
MIN_FONT_SIZE = 1000


STYLE_SPECS: list[dict[str, object]] = [
    {"name": "body", "size": 1100, "font": 0, "align": "JUSTIFY", "line": 160},
    {"name": "document-title", "size": 2000, "font": 1, "bold": True, "align": "CENTER", "line": 130, "before": 500, "after": 500, "keep": True},
    {"name": "subtitle", "size": 1400, "font": 1, "bold": True, "align": "CENTER", "line": 140, "after": 300},
    {"name": "meta", "size": 1000, "font": 1, "align": "RIGHT", "line": 135},
    {"name": "heading-1", "size": 1600, "font": 1, "bold": True, "align": "LEFT", "line": 145, "before": 700, "after": 350, "keep": True},
    {"name": "heading-2", "size": 1400, "font": 1, "bold": True, "align": "LEFT", "line": 145, "before": 500, "after": 250, "keep": True},
    {"name": "heading-3", "size": 1200, "font": 1, "bold": True, "align": "LEFT", "line": 150, "before": 350, "after": 180, "keep": True},
    {"name": "body-small", "size": 1000, "font": 0, "align": "JUSTIFY", "line": 145},
    {"name": "centered", "size": 1100, "font": 0, "align": "CENTER", "line": 150},
    {"name": "right", "size": 1100, "font": 0, "align": "RIGHT", "line": 150},
    {"name": "toc-1", "size": 1100, "font": 1, "bold": True, "align": "LEFT", "line": 155, "after": 100},
    {"name": "toc-2", "size": 1000, "font": 0, "align": "LEFT", "line": 150, "left": 1200},
    {"name": "toc-3", "size": 1000, "font": 0, "align": "LEFT", "line": 145, "left": 2400},
    {"name": "index", "size": 1000, "font": 0, "align": "LEFT", "line": 145},
    {"name": "equation", "size": 1100, "font": 0, "align": "CENTER", "line": 155, "before": 150, "after": 150},
    {"name": "question", "size": 1100, "font": 0, "align": "JUSTIFY", "line": 145, "after": 220, "keep": True},
    {"name": "instruction", "size": 1000, "font": 1, "align": "LEFT", "line": 140, "after": 180},
    {"name": "form-label", "size": 1000, "font": 1, "bold": True, "align": "LEFT", "line": 140},
    {"name": "table-cell", "size": 1000, "font": 0, "align": "LEFT", "line": 135},
    {"name": "table-header", "size": 1000, "font": 1, "bold": True, "align": "CENTER", "line": 135},
    {"name": "source-note", "size": 1000, "font": 0, "align": "LEFT", "line": 130},
    {"name": "abstract-title", "size": 1100, "font": 1, "bold": True, "align": "CENTER", "line": 140, "before": 250, "after": 180},
    {"name": "abstract-body", "size": 1000, "font": 0, "align": "JUSTIFY", "line": 145, "left": 600, "right": 600},
    {"name": "references", "size": 1000, "font": 0, "align": "LEFT", "line": 140, "left": 700, "intent": -700},
    {"name": "section-label", "size": 1000, "font": 1, "bold": True, "align": "LEFT", "line": 135, "after": 100},
]
STYLE_IDS = {str(spec["name"]): index for index, spec in enumerate(STYLE_SPECS)}

for prefix, namespace in {
    "hp": HP,
    "hs": HS,
    "hh": HH,
    "hc": HC,
    "opf": OPF,
    "hv": HV,
    "ha": HA,
    "config": CONFIG,
    "odf": ODF_MANIFEST,
    "rdf": RDF,
    "pkg": PKG_META,
}.items():
    ET.register_namespace(prefix, namespace)


def q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _border_profile(border_style: str) -> tuple[str, str]:
    if border_style in {"none", "plain"}:
        return "NONE", "#000000"
    if border_style == "subtle":
        return "SOLID", "#808080"
    return "SOLID", "#000000"


def _shading_ids(document: Document) -> dict[tuple[str, str], int]:
    keys: set[tuple[str, str]] = set()
    sections = document.sections or [Section(blocks=document.blocks, metadata=document.metadata)]
    for section_model in sections:
        for block in section_model.blocks:
            if not isinstance(block, Table):
                continue
            if block.shading:
                keys.add((block.shading, block.border_style))
            for row in block.rows:
                for cell in row:
                    if cell.shading:
                        keys.add((cell.shading, block.border_style))
    return {key: index for index, key in enumerate(sorted(keys), start=3)}


def serialize_document(document: Document, registry: IdRegistry) -> dict[str, bytes]:
    images = _collect_images(document)
    image_ids = {id(image): f"image{index}" for index, image in enumerate(images, start=1)}
    shading_ids = _shading_ids(document)
    paragraph_profiles = _paragraph_profiles(document)
    sections = document.sections or [Section(blocks=document.blocks, metadata=document.metadata)]
    section_parts: dict[str, bytes] = {}
    previews: list[str] = []
    for index, section_model in enumerate(sections):
        section, preview = _section(document, section_model, registry, image_ids, paragraph_profiles, shading_ids)
        section_parts[f"Contents/section{index}.xml"] = _xml_bytes(section)
        previews.append(preview)
    parts = {
        "version.xml": _version_xml(),
        "settings.xml": _xml_bytes(_settings()),
        "Contents/header.xml": _xml_bytes(_header(paragraph_profiles, shading_ids, len(sections))),
        "Contents/content.hpf": _xml_bytes(_content(document, images, len(sections))),
        "META-INF/container.xml": _container_xml(),
        "META-INF/manifest.xml": _xml_bytes(_odf_manifest(images)),
        "META-INF/container.rdf": _container_rdf(len(sections)),
        "Preview/PrvText.txt": "\n".join(item for item in previews if item).encode("utf-8"),
    }
    parts.update(section_parts)
    for index, image in enumerate(images, start=1):
        parts[f"BinData/image{index}.{image.extension}"] = image.data
    return parts


def _header(
    paragraph_profiles: list[dict[str, object]] | None = None,
    shading_ids: dict[tuple[str, str], int] | None = None,
    section_count: int = 1,
) -> ET.Element:
    _validate_style_specs()
    paragraph_profiles = paragraph_profiles or []
    numbering_profiles: dict[tuple[str, int], int] = {}
    bullet_profiles: dict[str, int] = {}
    tab_profiles: dict[tuple[tuple[int, str, str], ...], int] = {(): 0}
    for profile in paragraph_profiles:
        tabs = tuple((int(item["position"]), str(item["type"]), str(item["leader"])) for item in profile["tabs"])
        if tabs not in tab_profiles:
            tab_profiles[tabs] = len(tab_profiles)
        profile["tab_id"] = tab_profiles[tabs]
        if profile["list_type"] == "numbering":
            key = (str(profile["list_format"]), int(profile["list_start"]))
            if key not in numbering_profiles:
                numbering_profiles[key] = len(numbering_profiles) + 1
            profile["list_id"] = numbering_profiles[key]
        elif profile["list_type"] == "bullet":
            char = str(profile["bullet_char"])
            if char not in bullet_profiles:
                bullet_profiles[char] = len(bullet_profiles) + 1
            profile["list_id"] = bullet_profiles[char]
    root = ET.Element(q(HH, "head"), {"version": "1.5", "secCnt": str(section_count)})
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
    shading_ids = shading_ids or {}
    border_fills = ET.SubElement(ref_list, q(HH, "borderFills"), {"itemCnt": str(3 + len(shading_ids))})
    for border_id, border_type, color in ((0, "NONE", "#000000"), (1, "SOLID", "#000000"), (2, "SOLID", "#808080")):
        border_fill = ET.SubElement(border_fills, q(HH, "borderFill"), {"id": str(border_id), "threeD": "0", "shadow": "0", "centerLine": "NONE", "breakCellSeparateLine": "0"})
        for edge in ("leftBorder", "rightBorder", "topBorder", "bottomBorder", "diagonal"):
            edge_type = "NONE" if edge == "diagonal" else border_type
            ET.SubElement(border_fill, q(HH, edge), {"type": edge_type, "width": "0.1 mm", "color": color})
    for (color, border_style), border_id in sorted(shading_ids.items(), key=lambda item: item[1]):
        border_type, border_color = _border_profile(border_style)
        border_fill = ET.SubElement(
            border_fills,
            q(HH, "borderFill"),
            {"id": str(border_id), "threeD": "0", "shadow": "0", "centerLine": "NONE", "breakCellSeparateLine": "0"},
        )
        for edge in ("leftBorder", "rightBorder", "topBorder", "bottomBorder", "diagonal"):
            edge_type = "NONE" if edge == "diagonal" else border_type
            ET.SubElement(border_fill, q(HH, edge), {"type": edge_type, "width": "0.1 mm", "color": border_color})
        fill_brush = ET.SubElement(border_fill, q(HC, "fillBrush"))
        ET.SubElement(fill_brush, q(HC, "winBrush"), {"faceColor": color, "hatchColor": "#000000", "alpha": "0"})
    char_properties = ET.SubElement(ref_list, q(HH, "charProperties"), {"itemCnt": str(len(STYLE_SPECS))})
    all_hundred = {language.lower(): "100" for language in languages}
    all_zero_spacing = {language.lower(): "0" for language in languages}
    for style_id, spec in enumerate(STYLE_SPECS):
        char_pr = ET.SubElement(char_properties, q(HH, "charPr"), {"id": str(style_id), "height": str(spec.get("size", 1000)), "textColor": BLACK, "shadeColor": "#FFFFFF", "useFontSpace": "0", "useKerning": "0", "symMark": "NONE", "borderFillIDRef": "0"})
        font_ref = {language.lower(): str(spec.get("font", 0)) for language in languages}
        ET.SubElement(char_pr, q(HH, "fontRef"), font_ref)
        ET.SubElement(char_pr, q(HH, "ratio"), all_hundred)
        ET.SubElement(char_pr, q(HH, "spacing"), all_zero_spacing)
        ET.SubElement(char_pr, q(HH, "relSz"), all_hundred)
        ET.SubElement(char_pr, q(HH, "offset"), all_zero_spacing)
        if spec.get("bold"):
            ET.SubElement(char_pr, q(HH, "bold"))
    tab_properties = ET.SubElement(ref_list, q(HH, "tabProperties"), {"itemCnt": str(len(tab_profiles))})
    for tabs, tab_id in sorted(((key, value) for key, value in tab_profiles.items()), key=lambda item: item[1]):
        tab_pr = ET.SubElement(tab_properties, q(HH, "tabPr"), {"id": str(tab_id), "autoTabLeft": "0", "autoTabRight": "0"})
        for position, tab_type, leader in tabs:
            ET.SubElement(tab_pr, q(HH, "tabItem"), {"pos": str(position), "type": tab_type, "leader": leader})
    numberings = ET.SubElement(ref_list, q(HH, "numberings"), {"itemCnt": str(len(numbering_profiles))})
    for (number_format, start), numbering_id in sorted(numbering_profiles.items(), key=lambda item: item[1]):
        numbering = ET.SubElement(numberings, q(HH, "numbering"), {"id": str(numbering_id), "start": str(start)})
        for level in range(1, 11):
            para_head = ET.SubElement(numbering, q(HH, "paraHead"), {
                "start": "1", "level": str(level), "align": "LEFT", "useInstWidth": "1",
                "autoIndent": "1", "widthAdjust": "0", "textOffsetType": "PERCENT", "textOffset": "50",
                "numFormat": number_format, "charPrIDRef": "4294967295", "checkable": "0",
            })
            para_head.text = f"^{level}."
    bullets = ET.SubElement(ref_list, q(HH, "bullets"), {"itemCnt": str(len(bullet_profiles))})
    for char, bullet_id in sorted(bullet_profiles.items(), key=lambda item: item[1]):
        ET.SubElement(bullets, q(HH, "bullet"), {"id": str(bullet_id), "char": char})
    para_properties = ET.SubElement(ref_list, q(HH, "paraProperties"), {"itemCnt": str(len(STYLE_SPECS) + len(paragraph_profiles))})
    for style_id, spec in enumerate(STYLE_SPECS):
        _write_para_property(para_properties, style_id, spec, tab_id=0, list_type=None, list_id=0, list_level=0)
    for index, profile in enumerate(paragraph_profiles, start=len(STYLE_SPECS)):
        list_type = {"numbering": "NUMBER", "bullet": "BULLET"}.get(str(profile["list_type"]), None)
        _write_para_property(para_properties, index, profile["style_spec"], tab_id=int(profile["tab_id"]), list_type=list_type, list_id=int(profile.get("list_id") or 0), list_level=int(profile["list_level"]), indent=profile["indent"])
    styles = ET.SubElement(ref_list, q(HH, "styles"), {"itemCnt": str(len(STYLE_SPECS))})
    for style_id, spec in enumerate(STYLE_SPECS):
        name = str(spec["name"])
        ET.SubElement(styles, q(HH, "style"), {"id": str(style_id), "type": "PARA", "name": name, "engName": name, "paraPrIDRef": str(style_id), "charPrIDRef": str(style_id), "nextStyleIDRef": "0", "langID": "1033", "lockForm": "0"})
    return root


def _write_para_property(
    parent: ET.Element,
    para_id: int,
    spec: dict[str, object],
    *,
    tab_id: int,
    list_type: str | None,
    list_id: int,
    list_level: int,
    indent: dict[str, int] | None = None,
) -> None:
    para_pr = ET.SubElement(parent, q(HH, "paraPr"), {"id": str(para_id), "tabPrIDRef": str(tab_id), "condense": "0", "fontLineHeight": "0", "snapToGrid": "1", "suppressLineNumbers": "0", "checked": "0"})
    ET.SubElement(para_pr, q(HH, "align"), {"horizontal": str(spec.get("align", "LEFT")), "vertical": "BASELINE"})
    heading_type = list_type if list_type in {"NUMBER", "BULLET"} else "NONE"
    ET.SubElement(para_pr, q(HH, "heading"), {"type": heading_type, "idRef": str(list_id), "level": str(list_level if heading_type != "NONE" else 0)})
    ET.SubElement(para_pr, q(HH, "breakSetting"), {"breakLatinWord": "KEEP_WORD", "breakNonLatinWord": "KEEP_WORD", "widowOrphan": "1", "keepWithNext": "1" if spec.get("keep") else "0", "keepLines": "0", "pageBreakBefore": "0", "lineWrap": "BREAK"})
    margin = ET.SubElement(para_pr, q(HH, "margin"))
    values = {
        "intent": int(spec.get("intent", 0)),
        "left": int(spec.get("left", 0)),
        "right": int(spec.get("right", 0)),
        "prev": int(spec.get("before", 0)),
        "next": int(spec.get("after", 0)),
    }
    for key, value in (indent or {}).items():
        if key == "first_line":
            values["intent"] = value
        elif key in {"left", "right"}:
            values[key] = value
    for side, value in values.items():
        ET.SubElement(margin, q(HC, side), {"value": str(value), "unit": "HWPUNIT"})
    ET.SubElement(para_pr, q(HH, "lineSpacing"), {"type": "PERCENT", "value": str(spec.get("line", 160)), "unit": "CHAR"})
    ET.SubElement(para_pr, q(HH, "autoSpacing"), {"eAsianEng": "0", "eAsianNum": "0"})


def _paragraph_profiles(document: Document) -> list[dict[str, object]]:
    """Return deterministic dynamic paragraph properties for P01 formatting."""
    profiles: list[dict[str, object]] = []
    by_key: dict[tuple[object, ...], dict[str, object]] = {}
    source_sections = document.sections or [Section(blocks=document.blocks, metadata=document.metadata)]
    for source_section in source_sections:
      for block in source_section.blocks:
          if not isinstance(block, Paragraph):
              continue
          if not block.tabs and not block.indent and not block.list_type:
              continue
          tabs = tuple((int(item["position"]), str(item["type"]), str(item["leader"])) for item in block.tabs)
          indent = tuple(sorted((str(key), int(value)) for key, value in block.indent.items()))
          key = (
            _style_id(block.style),
            tabs,
            indent,
            block.list_type,
            int(block.list_level),
            int(block.list_start),
            str(block.list_format),
            str(block.bullet_char),
          )
          profile = by_key.get(key)
          if profile is None:
              profile = {
                "block_id": id(block),
                "tabs": [dict(item) for item in block.tabs],
                "indent": dict(block.indent),
                "list_type": block.list_type,
                "list_level": block.list_level,
                "list_start": block.list_start,
                "list_format": block.list_format,
                "bullet_char": block.bullet_char,
                "style_spec": STYLE_SPECS[_style_id(block.style)],
              }
              by_key[key] = profile
              profiles.append(profile)
          profile.setdefault("block_ids", []).append(id(block))
    for index, profile in enumerate(profiles, start=len(STYLE_SPECS)):
        profile["para_id"] = index
    return profiles


def _content(document: Document, images: list[ImageAsset], section_count: int = 1) -> ET.Element:
    root = ET.Element(q(OPF, "package"), {"version": "", "unique-identifier": "", "id": ""})
    metadata = ET.SubElement(root, q(OPF, "metadata"))
    ET.SubElement(metadata, q(OPF, "title")).text = document.title
    ET.SubElement(metadata, q(OPF, "language")).text = "ko"
    creator = ET.SubElement(metadata, q(OPF, "meta"), {"name": "creator", "content": "text"})
    creator.text = document.author
    manifest = ET.SubElement(root, q(OPF, "manifest"))
    ET.SubElement(manifest, q(OPF, "item"), {"id": "header", "href": "Contents/header.xml", "media-type": "application/xml"})
    for index in range(section_count):
        ET.SubElement(manifest, q(OPF, "item"), {"id": f"section{index}", "href": f"Contents/section{index}.xml", "media-type": "application/xml"})
    ET.SubElement(manifest, q(OPF, "item"), {"id": "settings", "href": "settings.xml", "media-type": "application/xml"})
    for index, image in enumerate(images, start=1):
        ET.SubElement(manifest, q(OPF, "item"), {"id": f"image{index}", "href": f"BinData/image{index}.{image.extension}", "media-type": image.media_type})
    spine = ET.SubElement(root, q(OPF, "spine"))
    ET.SubElement(spine, q(OPF, "itemref"), {"idref": "header", "linear": "yes"})
    for index in range(section_count):
        ET.SubElement(spine, q(OPF, "itemref"), {"idref": f"section{index}", "linear": "yes"})
    return root


def _odf_manifest(images: list[ImageAsset]) -> ET.Element:
    root = ET.Element(q(ODF_MANIFEST, "manifest"))
    for index, image in enumerate(images, start=1):
        ET.SubElement(root, q(ODF_MANIFEST, "file-entry"), {q(ODF_MANIFEST, "full-path"): f"BinData/image{index}.{image.extension}", q(ODF_MANIFEST, "media-type"): image.media_type})
    return root


def _container_xml() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<ocf:container xmlns:ocf="{OCF}" xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
        '<ocf:rootfiles>'
        '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
        '<ocf:rootfile full-path="Preview/PrvText.txt" media-type="text/plain"/>'
        '<ocf:rootfile full-path="META-INF/container.rdf" media-type="application/rdf+xml"/>'
        '</ocf:rootfiles></ocf:container>'
    ).encode("utf-8")


def _version_xml() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<hv:HCFVersion xmlns:hv="{HV}" tagetApplication="WORDPROCESSOR" major="5" minor="1" '
        'micro="1" buildNumber="0" os="1" xmlVersion="1.5" '
        'application="Hancom Office Hangul" appVersion="HWPX Toolkit 1.0"/>'
    ).encode("utf-8")


def _settings() -> ET.Element:
    root = ET.Element(q(HA, "HWPApplicationSetting"), {"xmlns:config": CONFIG})
    ET.SubElement(root, q(HA, "CaretPosition"), {"listIDRef": "0", "paraIDRef": "1", "pos": "0"})
    return root


def _container_rdf(section_count: int = 1) -> bytes:
    """Emit the byte-stable RDF form accepted by Hancom Hangul.

    Hangul's package reader is stricter than a general RDF/XML parser. In
    particular, declaring the package namespace on ``rdf:RDF`` and pretty
    printing the document can make otherwise equivalent RDF fail to open.
    Keep the package namespace local to each ``hasPart`` element, matching
    native HWPX output.
    """
    sections = "".join(
        f'<rdf:Description rdf:about=""><ns0:hasPart xmlns:ns0="{PKG_META}" rdf:resource="Contents/section{index}.xml"/></rdf:Description>'
        f'<rdf:Description rdf:about="Contents/section{index}.xml"><rdf:type rdf:resource="{PKG_META}SectionFile"/></rdf:Description>'
        for index in range(section_count)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<rdf:RDF xmlns:rdf="{RDF}">'
        '<rdf:Description rdf:about="">'
        f'<ns0:hasPart xmlns:ns0="{PKG_META}" rdf:resource="Contents/header.xml"/>'
        '</rdf:Description>'
        '<rdf:Description rdf:about="Contents/header.xml">'
        f'<rdf:type rdf:resource="{PKG_META}HeaderFile"/>'
        '</rdf:Description>'
        + sections +
        '<rdf:Description rdf:about="">'
        f'<rdf:type rdf:resource="{PKG_META}Document"/>'
        '</rdf:Description>'
        '</rdf:RDF>'
    ).encode("utf-8")


def _section(
    document: Document,
    section_model: Section,
    registry: IdRegistry,
    image_ids: dict[int, str],
    paragraph_profiles: list[dict[str, object]] | None = None,
    shading_ids: dict[tuple[str, str], int] | None = None,
) -> tuple[ET.Element, str]:
    root = ET.Element(q(HS, "sec"))
    preview: list[str] = []
    paragraph_id = 1
    note_number = 1
    first_block = True
    paragraph_profiles = paragraph_profiles or []
    paragraph_ids = {
        int(block_id): int(profile["para_id"])
        for profile in paragraph_profiles
        for block_id in profile.get("block_ids", [profile.get("block_id")])
        if block_id is not None
    }
    for block in section_model.blocks:
        if isinstance(block, Paragraph):
            _write_paragraph(root, block, registry, paragraph_id, section_model.metadata or document.metadata, section_start=first_block, para_pr_id=paragraph_ids.get(id(block)), section=section_model)
            preview.extend(run.text for run in block.runs if run.text)
            paragraph_id += 1
        elif isinstance(block, PageBreak):
            _write_page_break(root, paragraph_id, section_model.metadata or document.metadata, section_start=first_block, section=section_model, registry=registry)
            paragraph_id += 1
        elif isinstance(block, Table):
            _write_table(root, block, registry, paragraph_id, section_model.metadata or document.metadata, image_ids, shading_ids or {}, section_start=first_block, section=section_model)
            if block.caption:
                preview.append(block.caption)
            for row in block.rows:
                preview.append("\t".join(cell.value for cell in row))
            paragraph_id += 1
        elif isinstance(block, Note):
            _write_note(root, block, paragraph_id, note_number, section_model.metadata or document.metadata, section_start=first_block, section=section_model, registry=registry)
            preview.append(block.text)
            paragraph_id += 1
            note_number += 1
        first_block = False
    if len(root) == 0:
        _write_paragraph(root, Paragraph(runs=[Run(text="")]), registry, 1, section_model.metadata or document.metadata, section_start=True, section=section_model)
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


def _write_page_break(
    parent: ET.Element,
    paragraph_id: int,
    metadata: dict[str, object],
    *,
    section_start: bool = False,
    section: Section | None = None,
    registry: IdRegistry | None = None,
) -> None:
    p = _new_paragraph(parent, paragraph_id, _style_id("body"))
    p.set("pageBreak", "1")
    if section_start:
        _write_section_properties(p, metadata, section=section, registry=registry)
    run = ET.SubElement(p, q(HP, "run"), {"charPrIDRef": str(_style_id("body"))})
    ET.SubElement(run, q(HP, "t"))


def _write_paragraph(
    parent: ET.Element,
    paragraph: Paragraph,
    registry: IdRegistry,
    paragraph_id: int,
    metadata: dict[str, object],
    *,
    section_start: bool = False,
    para_pr_id: int | None = None,
    section: Section | None = None,
) -> None:
    style_id = _style_id(paragraph.style)
    p = _new_paragraph(parent, paragraph_id, style_id)
    p.set("paraPrIDRef", str(para_pr_id if para_pr_id is not None else style_id))
    if section_start:
        _write_section_properties(p, metadata, section=section, registry=registry)
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
                "textColor": BLACK,
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
    begin_id: int | None = None
    field_id: int | None = None
    if link:
        begin_id = registry.allocate("field_begin") + 2000
        field_id = registry.allocate("field_instance") + 3000
        ctrl = ET.SubElement(run, q(HP, "ctrl"))
        ET.SubElement(ctrl, q(HP, "fieldBegin"), {"id": str(begin_id), "type": "HYPERLINK", "name": link, "editable": "0", "dirty": "0", "zorder": "-1", "fieldid": str(field_id)})
    _write_text(run, model.text)
    if begin_id is not None and field_id is not None:
        ctrl = ET.SubElement(run, q(HP, "ctrl"))
        ET.SubElement(ctrl, q(HP, "fieldEnd"), {"beginIDRef": str(begin_id), "fieldid": str(field_id)})


def _write_table(
    parent: ET.Element,
    table: Table,
    registry: IdRegistry,
    paragraph_id: int,
    metadata: dict[str, object],
    image_ids: dict[int, str],
    shading_ids: dict[tuple[str, str], int],
    *,
    section_start: bool = False,
    section: Section | None = None,
) -> None:
    p = _new_paragraph(parent, paragraph_id)
    if section_start:
        _write_section_properties(p, metadata, section=section, registry=registry)
    run = ET.SubElement(p, q(HP, "run"), {"charPrIDRef": "0"})
    if table.bookmark:
        ctrl = ET.SubElement(run, q(HP, "ctrl"))
        ET.SubElement(ctrl, q(HP, "bookmark"), {"name": table.bookmark})
    row_count = len(table.rows)
    col_count = table.col_count or max((cell.col_index + cell.col_span for row in table.rows for cell in row), default=1)
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
        {"id": str(registry.allocate("table") + 3000), "zOrder": "0", "numberingType": "TABLE", "textWrap": "TOP_AND_BOTTOM", "textFlow": "BOTH_SIDES", "lock": "0", "pageBreak": table.split.upper(), "repeatHeader": "1" if table.repeat_header and table.header_rows else "0", "rowCnt": str(row_count), "colCnt": str(col_count), "cellSpacing": "0", "borderFillIDRef": str(border_fill_id), "noAdjust": "0"},
    )
    row_heights = [_mm(value) for value in table.row_heights_mm] if table.row_heights_mm else [2400] * row_count
    ET.SubElement(tbl, q(HP, "sz"), {"width": str(table_width), "widthRelTo": "ABSOLUTE", "height": str(sum(row_heights)), "heightRelTo": "ABSOLUTE", "protect": "0"})
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
        row_height = row_heights[row_index]
        for cell_model in row_model:
            col_index = cell_model.col_index
            cell_border_fill = shading_ids.get((cell_model.shading or table.shading, table.border_style), border_fill_id) if (cell_model.shading or table.shading) else border_fill_id
            tc = ET.SubElement(tr, q(HP, "tc"), {"name": "", "header": "1" if row_index < table.header_rows else "0", "hasMargin": "1", "protect": "0", "editable": "0", "dirty": "0", "borderFillIDRef": str(cell_border_fill)})
            ET.SubElement(tc, q(HP, "cellAddr"), {"colAddr": str(col_index), "rowAddr": str(row_index)})
            ET.SubElement(tc, q(HP, "cellSpan"), {"colSpan": str(cell_model.col_span), "rowSpan": str(cell_model.row_span)})
            cell_width = sum(cell_widths[col_index:col_index + cell_model.col_span])
            cell_height = sum(row_heights[row_index:row_index + cell_model.row_span])
            cell_style = cell_model.style
            if cell_style == "table-cell" and row_index < table.header_rows:
                cell_style = "table-header"
            cell_style_id = _style_id(cell_style)
            ET.SubElement(tc, q(HP, "cellSz"), {"width": str(cell_width), "height": str(cell_height)})
            ET.SubElement(tc, q(HP, "cellMargin"), {"left": "141", "right": "141", "top": "141", "bottom": "141"})
            sub = ET.SubElement(tc, q(HP, "subList"), {"id": "", "textDirection": "HORIZONTAL", "lineWrap": "BREAK", "vertAlign": "CENTER", "linkListIDRef": "0", "linkListNextIDRef": "0", "textWidth": str(cell_width), "textHeight": str(cell_height), "hasTextRef": "0", "hasNumRef": "0"})
            cp = _new_paragraph(sub, registry.allocate("cell_para") + 6000, cell_style_id)
            cp.set("paraPrIDRef", str(cell_style_id))
            cr = ET.SubElement(cp, q(HP, "run"), {"charPrIDRef": str(cell_style_id)})
            if cell_model.image:
                _write_picture(cr, cell_model.image, image_ids[id(cell_model.image)], registry, cell_width, cell_height)
                if cell_model.value:
                    _write_text(cr, cell_model.value)
                else:
                    ET.SubElement(cr, q(HP, "t"))
            elif cell_model.formula:
                begin_id = registry.allocate("field_begin") + 2000
                field_id = registry.allocate("field_instance") + 3000
                ctrl = ET.SubElement(cr, q(HP, "ctrl"))
                ET.SubElement(ctrl, q(HP, "fieldBegin"), {"id": str(begin_id), "type": "FORMULA", "name": cell_model.formula, "editable": "1", "dirty": "0", "zorder": "-1", "fieldid": str(field_id)})
                ET.SubElement(cr, q(HP, "t")).text = cell_model.value
                end = ET.SubElement(cr, q(HP, "ctrl"))
                ET.SubElement(end, q(HP, "fieldEnd"), {"beginIDRef": str(begin_id), "fieldid": str(field_id)})
            else:
                _write_text(cr, cell_model.value)
    ET.SubElement(run, q(HP, "t"))


def _write_picture(
    parent: ET.Element,
    image: ImageAsset,
    image_id: str,
    registry: IdRegistry,
    cell_width: int,
    row_height: int,
) -> None:
    available_width = max(1000, cell_width - 282)
    available_height = max(1000, row_height - 282)
    aspect = image.width_px / image.height_px
    if image.width_mm is not None and image.height_mm is not None:
        width = _mm(image.width_mm)
        height = _mm(image.height_mm)
    elif image.width_mm is not None:
        width = _mm(image.width_mm)
        height = max(1, round(width / aspect))
    elif image.height_mm is not None:
        height = _mm(image.height_mm)
        width = max(1, round(height * aspect))
    else:
        width = available_width
        height = max(1, round(width / aspect))
    scale = min(1.0, available_width / width, available_height / height)
    width = max(1, round(width * scale))
    height = max(1, round(height * scale))
    org_width = image.width_px * 36
    org_height = image.height_px * 36
    scale_x = width / org_width
    scale_y = height / org_height
    picture_number = registry.allocate("picture") + 4000
    pic = ET.SubElement(
        parent,
        q(HP, "pic"),
        {
            "id": str(picture_number),
            "instid": str(picture_number),
            "reverse": "0",
            "numberingType": "PICTURE",
            "textWrap": "TOP_AND_BOTTOM",
            "textFlow": "BOTH_SIDES",
            "lock": "0",
            "dropcapstyle": "None",
            "href": "",
            "groupLevel": "0",
        },
    )
    ET.SubElement(pic, q(HP, "offset"), {"x": "0", "y": "0"})
    ET.SubElement(pic, q(HP, "orgSz"), {"width": str(org_width), "height": str(org_height)})
    ET.SubElement(pic, q(HP, "curSz"), {"width": str(width), "height": str(height)})
    ET.SubElement(pic, q(HP, "flip"), {"horizontal": "0", "vertical": "0"})
    ET.SubElement(pic, q(HP, "rotationInfo"), {"angle": "0", "centerX": str(width // 2), "centerY": str(height // 2), "rotateimage": "1"})
    rendering = ET.SubElement(pic, q(HP, "renderingInfo"))
    ET.SubElement(rendering, q(HC, "transMatrix"), {"e1": "1", "e2": "0", "e3": "0", "e4": "0", "e5": "1", "e6": "0"})
    ET.SubElement(rendering, q(HC, "scaMatrix"), {"e1": f"{scale_x:.8g}", "e2": "0", "e3": "0", "e4": "0", "e5": f"{scale_y:.8g}", "e6": "0"})
    ET.SubElement(rendering, q(HC, "rotMatrix"), {"e1": "1", "e2": "0", "e3": "0", "e4": "0", "e5": "1", "e6": "0"})
    ET.SubElement(pic, q(HC, "img"), {"binaryItemIDRef": image_id, "bright": "0", "contrast": "0", "effect": "REAL_PIC", "alpha": "0"})
    rect = ET.SubElement(pic, q(HP, "imgRect"))
    ET.SubElement(rect, q(HC, "pt0"), {"x": "0", "y": "0"})
    ET.SubElement(rect, q(HC, "pt1"), {"x": str(org_width), "y": "0"})
    ET.SubElement(rect, q(HC, "pt2"), {"x": str(org_width), "y": str(org_height)})
    ET.SubElement(rect, q(HC, "pt3"), {"x": "0", "y": str(org_height)})
    clip_width = image.width_px * 75
    clip_height = image.height_px * 75
    ET.SubElement(pic, q(HP, "imgClip"), {"left": "0", "right": str(clip_width), "top": "0", "bottom": str(clip_height)})
    ET.SubElement(pic, q(HP, "inMargin"), {"left": "0", "right": "0", "top": "0", "bottom": "0"})
    ET.SubElement(pic, q(HP, "imgDim"), {"dimwidth": str(clip_width), "dimheight": str(clip_height)})
    ET.SubElement(pic, q(HP, "effects"))
    ET.SubElement(pic, q(HP, "sz"), {"width": str(width), "widthRelTo": "ABSOLUTE", "height": str(height), "heightRelTo": "ABSOLUTE", "protect": "0"})
    ET.SubElement(pic, q(HP, "pos"), {"treatAsChar": "1", "affectLSpacing": "0", "flowWithText": "1", "allowOverlap": "0", "holdAnchorAndSO": "0", "vertRelTo": "PARA", "horzRelTo": "COLUMN", "vertAlign": "TOP", "horzAlign": "CENTER", "vertOffset": "0", "horzOffset": "0"})
    ET.SubElement(pic, q(HP, "outMargin"), {"left": "0", "right": "0", "top": "0", "bottom": "0"})
    ET.SubElement(pic, q(HP, "shapeComment")).text = image.alt or f"{image_id}.{image.extension} {image.width_px}x{image.height_px}"


def _write_note(
    parent: ET.Element,
    note: Note,
    paragraph_id: int,
    number: int,
    metadata: dict[str, object],
    *,
    section_start: bool = False,
    section: Section | None = None,
    registry: IdRegistry | None = None,
) -> None:
    note_style_id = _style_id("source-note")
    p = _new_paragraph(parent, paragraph_id, note_style_id)
    if section_start:
        _write_section_properties(p, metadata, section=section, registry=registry)
    run = ET.SubElement(p, q(HP, "run"), {"charPrIDRef": str(note_style_id)})
    ctrl = ET.SubElement(run, q(HP, "ctrl"))
    element_name = "footNote" if note.kind == "footnote" else "endNote"
    note_element = ET.SubElement(ctrl, q(HP, element_name), {"number": str(number), "instId": str(number)})
    sub = ET.SubElement(note_element, q(HP, "subList"), {"id": "", "textDirection": "HORIZONTAL", "lineWrap": "BREAK", "vertAlign": "TOP", "linkListIDRef": "0", "linkListNextIDRef": "0", "textWidth": "42520", "textHeight": "1200", "hasTextRef": "0", "hasNumRef": "0"})
    np = _new_paragraph(sub, paragraph_id + 10000, note_style_id)
    nr = ET.SubElement(np, q(HP, "run"), {"charPrIDRef": str(note_style_id)})
    ET.SubElement(nr, q(HP, "t")).text = note.text
    ET.SubElement(run, q(HP, "t"))


def _write_section_properties(paragraph: ET.Element, metadata: dict[str, object], *, section: Section | None = None, registry: IdRegistry | None = None) -> None:
    layout = resolve_layout(metadata)
    column_count = _column_count(metadata)
    column_gap = _column_gap(metadata)
    run = ET.SubElement(paragraph, q(HP, "run"), {"charPrIDRef": "0"})
    sec_pr = ET.SubElement(
        run,
        q(HP, "secPr"),
        {
            "id": "",
            "textDirection": "HORIZONTAL",
            "spaceColumns": str(column_gap if column_count > 1 else _mm(4)),
            "tabStop": "8000",
            "tabStopVal": "4000",
            "tabStopUnit": "HWPUNIT",
            "outlineShapeIDRef": "0",
            "memoShapeIDRef": "0",
            "textVerticalWidthHead": "0",
            "masterPageCnt": "0",
        },
    )
    ET.SubElement(sec_pr, q(HP, "grid"), {"lineGrid": "0", "charGrid": "0", "wonggojiFormat": "0"})
    page_start = 0
    if section and section.page_number and section.page_number.get("start"):
        page_start = max(0, int(section.page_number["start"]) - 1)
    ET.SubElement(sec_pr, q(HP, "startNum"), {"pageStartsOn": "BOTH", "page": str(page_start), "pic": "0", "tbl": "0", "equation": "0"})
    ET.SubElement(
        sec_pr,
        q(HP, "visibility"),
        {
            "hideFirstHeader": "0",
            "hideFirstFooter": "0",
            "hideFirstMasterPage": "0",
            "border": "SHOW_ALL",
            "fill": "SHOW_ALL",
            "hideFirstPageNum": "0",
            "hideFirstEmptyLine": "0",
            "showLineNumber": "0",
        },
    )
    ET.SubElement(
        sec_pr,
        q(HP, "lineNumberShape"),
        {"restartType": "0", "countBy": "0", "distance": "0", "startNumber": "0"},
    )
    page_pr = ET.SubElement(
        sec_pr,
        q(HP, "pagePr"),
        {"landscape": "WIDELY", "width": str(_mm(float(layout["page_width_mm"]))), "height": str(_mm(float(layout["page_height_mm"]))), "gutterType": "LEFT_ONLY"},
    )
    ET.SubElement(
        page_pr,
        q(HP, "margin"),
        {"left": str(_mm(float(layout["left_mm"]))), "right": str(_mm(float(layout["right_mm"]))), "top": str(_mm(float(layout["top_mm"]))), "bottom": str(_mm(float(layout["bottom_mm"]))), "header": str(_mm(float(layout["header_mm"]))), "footer": str(_mm(float(layout["footer_mm"]))), "gutter": "0"},
    )
    _write_note_properties(sec_pr, "footNotePr", "-1", "283", "EACH_COLUMN")
    _write_note_properties(sec_pr, "endNotePr", "14692344", "0", "END_OF_DOCUMENT")
    for border_type in ("BOTH", "EVEN", "ODD"):
        border = ET.SubElement(
            sec_pr,
            q(HP, "pageBorderFill"),
            {
                "type": border_type,
                "borderFillIDRef": "1",
                "textBorder": "PAPER",
                "headerInside": "0",
                "footerInside": "0",
                "fillArea": "PAPER",
            },
        )
        ET.SubElement(border, q(HP, "offset"), {"left": "1417", "right": "1417", "top": "1417", "bottom": "1417"})
    ctrl = ET.SubElement(run, q(HP, "ctrl"))
    ET.SubElement(
        ctrl,
        q(HP, "colPr"),
        {"id": "", "type": "NEWSPAPER", "layout": "LEFT", "colCount": str(column_count), "sameSz": "1", "sameGap": str(column_gap if column_count > 1 else 0)},
    )
    if section is None:
        return
    if section.page_number:
        page_run = ET.SubElement(paragraph, q(HP, "run"), {"charPrIDRef": str(_style_id("body"))})
        page_ctrl = ET.SubElement(page_run, q(HP, "ctrl"))
        ET.SubElement(page_ctrl, q(HP, "pageNum"), {
            "pos": section.page_number["position"],
            "formatType": section.page_number["format"],
            "sideChar": section.page_number.get("side_char", ""),
        })
    for kind, paragraphs, control_id in (("header", section.header, 1), ("footer", section.footer, 2)):
        if not paragraphs:
            continue
        field_run = ET.SubElement(paragraph, q(HP, "run"), {"charPrIDRef": str(_style_id("body"))})
        field_ctrl = ET.SubElement(field_run, q(HP, "ctrl"))
        container = ET.SubElement(field_ctrl, q(HP, kind), {"id": str(control_id), "applyPageType": "BOTH"})
        sublist = ET.SubElement(container, q(HP, "subList"), {
            "id": "", "textDirection": "HORIZONTAL", "lineWrap": "BREAK", "vertAlign": "TOP",
            "linkListIDRef": "0", "linkListNextIDRef": "0", "textWidth": str(_content_width(metadata)),
            "textHeight": str(_mm(float(resolve_layout(metadata)["header_mm" if kind == "header" else "footer_mm"]))),
            "hasTextRef": "0", "hasNumRef": "0",
        })
        for header_paragraph in paragraphs:
            _write_paragraph(sublist, header_paragraph, registry or IdRegistry(), 0, metadata)


def _write_note_properties(
    sec_pr: ET.Element,
    element_name: str,
    line_length: str,
    between_notes: str,
    placement: str,
) -> None:
    note_pr = ET.SubElement(sec_pr, q(HP, element_name))
    ET.SubElement(
        note_pr,
        q(HP, "autoNumFormat"),
        {"type": "DIGIT", "userChar": "", "prefixChar": "", "suffixChar": ")", "supscript": "0"},
    )
    ET.SubElement(
        note_pr,
        q(HP, "noteLine"),
        {"length": line_length, "type": "SOLID", "width": "0.12 mm", "color": BLACK},
    )
    ET.SubElement(
        note_pr,
        q(HP, "noteSpacing"),
        {"betweenNotes": between_notes, "belowLine": "567", "aboveLine": "850"},
    )
    ET.SubElement(note_pr, q(HP, "numbering"), {"type": "CONTINUOUS", "newNum": "1"})
    ET.SubElement(note_pr, q(HP, "placement"), {"place": placement, "beneathText": "0"})


def _style_id(name: str) -> int:
    return STYLE_IDS.get(name, STYLE_IDS["body"])


def _write_text(parent: ET.Element, value: str) -> None:
    lines = value.split("\n")
    for index, line in enumerate(lines):
        tab_parts = line.split("\t")
        for tab_index, tab_part in enumerate(tab_parts):
            text = ET.SubElement(parent, q(HP, "t"))
            text.text = tab_part
            if tab_part[:1].isspace() or tab_part[-1:].isspace():
                text.set(q(XML, "space"), "preserve")
            if tab_index < len(tab_parts) - 1:
                ET.SubElement(parent, q(HP, "tab"))
        if index < len(lines) - 1:
            ET.SubElement(parent, q(HP, "lineBreak"))


def _validate_style_specs() -> None:
    names: set[str] = set()
    for spec in STYLE_SPECS:
        name = str(spec["name"])
        if name in names:
            raise ValueError(f"Duplicate style name: {name}")
        names.add(name)
        size = int(spec.get("size", MIN_FONT_SIZE))
        if size < MIN_FONT_SIZE:
            raise ValueError(f"Generated style '{name}' is below the 10 pt minimum: {size / 100:g} pt")


def _collect_images(document: Document) -> list[ImageAsset]:
    images: list[ImageAsset] = []
    source_sections = document.sections or [Section(blocks=document.blocks, metadata=document.metadata)]
    for source_section in source_sections:
        for block in source_section.blocks:
            if not isinstance(block, Table):
                continue
            for row in block.rows:
                for cell in row:
                    if cell.image is not None:
                        images.append(cell.image)
    return images


def _mm(value: float) -> int:
    return max(0, round(value * 283.466))


def _column_count(metadata: dict[str, object]) -> int:
    layout = resolve_layout(metadata)
    try:
        return max(1, min(4, int(layout["columns"])))
    except (TypeError, ValueError):
        return 1


def _column_gap(metadata: dict[str, object]) -> int:
    layout = resolve_layout(metadata)
    try:
        return _mm(float(layout["column_gap_mm"]))
    except (TypeError, ValueError):
        return _mm(8)


def _content_width(metadata: dict[str, object]) -> int:
    layout = resolve_layout(metadata)
    page = _mm(float(layout["page_width_mm"]))
    left = _mm(float(layout["left_mm"]))
    right = _mm(float(layout["right_mm"]))
    return max(1000, page - left - right)


def _xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
