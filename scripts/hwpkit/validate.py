from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET
from zipfile import ZIP_STORED, BadZipFile, ZipFile

from .package import MIMETYPE_NAME, MIMETYPE_VALUE, REQUIRED_ENTRIES, safe_name


HWPX_VERSION_NS = "http://www.hancom.co.kr/hwpml/2011/version"
HWPX_APP_NS = "http://www.hancom.co.kr/hwpml/2011/app"
HWPX_OPF_NS = "http://www.idpf.org/2007/opf/"
ODF_MANIFEST_NS = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


def validate_hwpx(path: Path, *, full: bool = True) -> list[str]:
    errors: list[str] = []
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            names_list = [info.filename for info in infos]
            names = set(names_list)
            if not infos:
                return ["The package is empty."]
            for name, count in Counter(names_list).items():
                if count > 1:
                    errors.append(f"Duplicate ZIP entry: {name}")
            for name in names:
                if not safe_name(name):
                    errors.append(f"Unsafe ZIP path: {name}")
            if infos[0].filename != MIMETYPE_NAME:
                errors.append("mimetype is not the first ZIP entry.")
            elif infos[0].compress_type != ZIP_STORED:
                errors.append("mimetype must be stored without compression.")
            if MIMETYPE_NAME in names and archive.read(MIMETYPE_NAME) != MIMETYPE_VALUE:
                errors.append("The mimetype value is invalid.")
            for missing in sorted(REQUIRED_ENTRIES - names):
                errors.append(f"Required entry is missing: {missing}")
            bad = archive.testzip()
            if bad:
                errors.append(f"CRC verification failed: {bad}")
            roots: dict[str, ET.Element] = {}
            for name in names_list:
                if name.endswith((".xml", ".hpf")):
                    try:
                        roots[name] = ET.fromstring(archive.read(name))
                    except ET.ParseError as exc:
                        errors.append(f"XML parsing failed: {name}: {exc}")
            _validate_package_parts(roots, errors)
            _validate_container(roots, names, errors)
            _validate_manifest(roots, names, errors)
            _validate_odf_manifest(roots, errors)
            _validate_rdf(roots, errors)
            if "META-INF/container.rdf" in names:
                _validate_rdf_serialization(archive.read("META-INF/container.rdf"), errors)
            if full:
                _validate_references(roots, errors)
    except (OSError, BadZipFile, RuntimeError) as exc:
        return [f"Unreadable HWPX package: {exc}"]
    return errors


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr(element: ET.Element, local: str) -> str | None:
    for key, value in element.attrib.items():
        if _local(key) == local:
            return value
    return None


def _namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def _validate_package_parts(roots: dict[str, ET.Element], errors: list[str]) -> None:
    version = roots.get("version.xml")
    if version is not None:
        if _local(version.tag) != "HCFVersion" or _namespace(version.tag) != HWPX_VERSION_NS:
            errors.append("version.xml does not use the Hancom HCFVersion namespace.")
        if version.get("tagetApplication") != "WORDPROCESSOR":
            errors.append("version.xml tagetApplication must be WORDPROCESSOR.")
        if not version.get("xmlVersion"):
            errors.append("version.xml has no xmlVersion.")
    settings = roots.get("settings.xml")
    if settings is not None:
        if _local(settings.tag) != "HWPApplicationSetting" or _namespace(settings.tag) != HWPX_APP_NS:
            errors.append("settings.xml does not use the Hancom application namespace.")
        if not any(_local(element.tag) == "CaretPosition" for element in settings.iter()):
            errors.append("settings.xml has no CaretPosition.")


def _validate_container(roots: dict[str, ET.Element], names: set[str], errors: list[str]) -> None:
    root = roots.get("META-INF/container.xml")
    if root is None:
        return
    rootfiles = [element for element in root.iter() if _local(element.tag) == "rootfile"]
    targets = [_attr(element, "full-path") for element in rootfiles]
    targets = [target for target in targets if target]
    if not targets:
        errors.append("container.xml has no rootfile.")
    for target in targets:
        if target not in names:
            errors.append(f"container.xml points to a missing entry: {target}")
    expected = {
        "Contents/content.hpf": "application/hwpml-package+xml",
        "Preview/PrvText.txt": "text/plain",
        "META-INF/container.rdf": "application/rdf+xml",
    }
    declared = {
        _attr(element, "full-path"): _attr(element, "media-type")
        for element in rootfiles
        if _attr(element, "full-path")
    }
    for path, media_type in expected.items():
        if path not in declared:
            errors.append(f"container.xml does not declare required rootfile: {path}")
        elif declared[path] != media_type:
            errors.append(f"container.xml has an invalid media type for {path}: {declared[path]}")


def _validate_manifest(roots: dict[str, ET.Element], names: set[str], errors: list[str]) -> None:
    root = roots.get("Contents/content.hpf")
    if root is None:
        return
    if _local(root.tag) != "package" or _namespace(root.tag) != HWPX_OPF_NS:
        errors.append("content.hpf does not use the Hancom OPF package namespace.")
    ids: set[str] = set()
    targets: set[str] = set()
    declared: dict[str, tuple[str, str]] = {}
    for element in root.iter():
        if _local(element.tag) != "item":
            continue
        item_id = _attr(element, "id")
        href = _attr(element, "href")
        if item_id:
            if item_id in ids:
                errors.append(f"Duplicate manifest ID: {item_id}")
            ids.add(item_id)
        if href:
            target = _resolve_href(href)
            targets.add(target)
            if target not in names:
                errors.append(f"Manifest points to a missing entry: {href}")
            if item_id:
                declared[item_id] = (href, _attr(element, "media-type") or "")
    for element in root.iter():
        if _local(element.tag) == "itemref":
            idref = _attr(element, "idref")
            if idref and idref not in ids:
                errors.append(f"Spine points to an unknown manifest ID: {idref}")
    for section in (name for name in names if name.startswith("Contents/section") and name.endswith(".xml")):
        if section not in targets:
            errors.append(f"Section is not declared in the manifest: {section}")
    expected = {
        "header": ("Contents/header.xml", "application/xml"),
        "section0": ("Contents/section0.xml", "application/xml"),
        "settings": ("settings.xml", "application/xml"),
    }
    for item_id, value in expected.items():
        if item_id not in declared:
            errors.append(f"content.hpf is missing required manifest item: {item_id}")
        elif declared[item_id] != value:
            errors.append(
                f"content.hpf manifest item {item_id} must be href={value[0]} and media-type={value[1]}."
            )
    spine = [
        _attr(element, "idref")
        for element in root.iter()
        if _local(element.tag) == "itemref" and _attr(element, "idref")
    ]
    for required in ("header", "section0"):
        if required not in spine:
            errors.append(f"content.hpf spine is missing required itemref: {required}")


def _resolve_href(href: str) -> str:
    parsed = urlparse(href)
    clean = unquote(parsed.path)
    path = PurePosixPath(clean.lstrip("/"))
    parts: list[str] = []
    for part in path.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part not in (".", ""):
            parts.append(part)
    return "/".join(parts)


def _validate_odf_manifest(roots: dict[str, ET.Element], errors: list[str]) -> None:
    root = roots.get("META-INF/manifest.xml")
    if root is not None and (
        _local(root.tag) != "manifest" or _namespace(root.tag) != ODF_MANIFEST_NS
    ):
        errors.append("META-INF/manifest.xml does not use the ODF manifest namespace.")


def _validate_rdf(roots: dict[str, ET.Element], errors: list[str]) -> None:
    root = roots.get("META-INF/container.rdf")
    if root is None:
        return
    if _local(root.tag) != "RDF" or _namespace(root.tag) != RDF_NS:
        errors.append("META-INF/container.rdf does not use the RDF namespace.")
        return
    resources = {
        _attr(element, "resource")
        for element in root.iter()
        if _attr(element, "resource")
    }
    for required in ("Contents/header.xml", "Contents/section0.xml"):
        if required not in resources:
            errors.append(f"container.rdf does not link required document part: {required}")


def _validate_rdf_serialization(payload: bytes, errors: list[str]) -> None:
    if not payload.startswith(b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'):
        errors.append("container.rdf does not use the Hancom-compatible XML declaration.")
    declaration_end = payload.find(b">")
    if declaration_end < 0:
        return
    rdf_open_end = payload.find(b">", declaration_end + 1)
    if rdf_open_end < 0:
        return
    rdf_open = payload[declaration_end + 1 : rdf_open_end + 1]
    if b"<rdf:RDF" not in rdf_open or b"xmlns:rdf=" not in rdf_open:
        errors.append("container.rdf does not use the Hancom-compatible rdf:RDF root serialization.")
    if b"xmlns:pkg=" in rdf_open or b"xmlns:ns0=" in rdf_open:
        errors.append("container.rdf declares the package namespace on rdf:RDF; Hangul requires local hasPart declarations.")
    if payload.count(b"<ns0:hasPart xmlns:ns0=") < 2:
        errors.append("container.rdf does not use local package namespace declarations for hasPart.")


def _validate_references(roots: dict[str, ET.Element], errors: list[str]) -> None:
    header = roots.get("Contents/header.xml")
    declared: dict[str, set[str]] = {
        "charPr": set(),
        "paraPr": set(),
        "style": set(),
        "borderFill": set(),
        "tabPr": set(),
    }
    if header is not None:
        for element in header.iter():
            local = _local(element.tag)
            if local in declared and element.get("id") is not None:
                declared[local].add(element.get("id", ""))
    bookmarks: set[str] = set()
    content = roots.get("Contents/content.hpf")
    image_ids = {
        _attr(element, "id")
        for element in content.iter()
        if _local(element.tag) == "item" and (_attr(element, "media-type") or "").startswith("image/")
    } if content is not None else set()
    field_begins: Counter[tuple[str, str]] = Counter()
    field_ends: Counter[tuple[str, str]] = Counter()
    ids: Counter[tuple[str, str]] = Counter()
    for name, root in roots.items():
        if not name.startswith("Contents/section"):
            continue
        local_counts = Counter(_local(element.tag) for element in root.iter())
        for required in ("secPr", "pagePr", "margin", "colPr"):
            if local_counts[required] == 0:
                errors.append(f"{name}: missing page-layout element: {required}")
        for sec_pr in (element for element in root.iter() if _local(element.tag) == "secPr"):
            direct_children = {_local(child.tag) for child in sec_pr}
            required_children = {
                "grid",
                "startNum",
                "visibility",
                "lineNumberShape",
                "pagePr",
                "footNotePr",
                "endNotePr",
                "pageBorderFill",
            }
            for missing in sorted(required_children - direct_children):
                errors.append(f"{name}: secPr is missing Hancom-required child: {missing}")
        for page_pr in (element for element in root.iter() if _local(element.tag) == "pagePr"):
            try:
                width = int(page_pr.get("width", "0"))
                height = int(page_pr.get("height", "0"))
            except ValueError:
                width = height = 0
            if width <= 0 or height <= 0:
                errors.append(f"{name}: pagePr dimensions are invalid.")
        for element in root.iter():
            local = _local(element.tag)
            value = element.get("id")
            # Paragraph IDs are scoped by their containing list in valid Hancom
            # files, so only globally addressed drawing/object IDs are checked.
            if value and local in {"equation", "tbl"}:
                ids[(local, value)] += 1
            if local == "pic" and value:
                ids[(local, value)] += 1
            if local == "img":
                image_ref = element.get("binaryItemIDRef")
                if not image_ref or image_ref not in image_ids:
                    errors.append(f"{name}: picture points to an undeclared image: {image_ref or '(missing)'}")
            if local == "bookmark":
                bookmark = element.get("name", "")
                if not bookmark:
                    errors.append(f"{name}: bookmark has no name")
                elif bookmark in bookmarks:
                    errors.append(f"{name}: duplicate bookmark name: {bookmark}")
                bookmarks.add(bookmark)
            elif local == "fieldBegin":
                field_begins[(element.get("id", ""), element.get("fieldid", ""))] += 1
            elif local == "fieldEnd":
                field_ends[(element.get("beginIDRef", ""), element.get("fieldid", ""))] += 1
            if local == "run":
                _require_declared(name, "charPrIDRef", element, declared["charPr"], errors)
            elif local == "pageNum":
                if element.get("pos") not in {"TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "BOTTOM_LEFT", "BOTTOM_CENTER", "BOTTOM_RIGHT"}:
                    errors.append(f"{name}: pageNum has an unsupported position.")
                if element.get("formatType") not in {"DIGIT", "ROMAN_SMALL", "ROMAN_CAPITAL", "LATIN_SMALL", "LATIN_CAPITAL"}:
                    errors.append(f"{name}: pageNum has an unsupported formatType.")
            elif local in {"header", "footer"}:
                if not any(_local(child.tag) == "subList" for child in element):
                    errors.append(f"{name}: {local} is missing its subList content.")
            elif local == "p":
                _require_declared(name, "paraPrIDRef", element, declared["paraPr"], errors)
                _require_declared(name, "styleIDRef", element, declared["style"], errors)
            elif local in {"tbl", "tc"}:
                _require_declared(name, "borderFillIDRef", element, declared["borderFill"], errors)
    for key, count in ids.items():
        if count > 1:
            errors.append(f"Duplicate object ID: {key[0]}:{key[1]}")
    if field_begins != field_ends:
        errors.append("fieldBegin and fieldEnd IDs are not balanced.")


def _require_declared(
    part: str,
    attribute: str,
    element: ET.Element,
    valid: set[str],
    errors: list[str],
) -> None:
    value = element.get(attribute)
    if value is not None and value not in valid:
        errors.append(f"{part}: undeclared {attribute}: {value}")


def inspect_hwpx(path: Path) -> dict[str, object]:
    with ZipFile(path) as archive:
        names = archive.namelist()
        counts: Counter[str] = Counter()
        header_counts: Counter[str] = Counter()
        bookmarks: list[str] = []
        header = ET.fromstring(archive.read("Contents/header.xml")) if "Contents/header.xml" in names else None
        if header is not None:
            for element in header.iter():
                header_counts[_local(element.tag)] += 1
        for name in names:
            if not (name.startswith("Contents/section") and name.endswith(".xml")):
                continue
            root = ET.fromstring(archive.read(name))
            for element in root.iter():
                counts[_local(element.tag)] += 1
                if _local(element.tag) == "p" and element.get("pageBreak") == "1":
                    counts["pageBreak"] += 1
                if _local(element.tag) == "bookmark" and element.get("name"):
                    bookmarks.append(element.get("name", ""))
        return {
            "entries": len(names),
            "sections": len([name for name in names if name.startswith("Contents/section")]),
            "paragraphs": counts["p"],
            "tables": counts["tbl"],
            "equations": counts["equation"],
            "images": counts["pic"],
            "footnotes": counts["footNote"],
            "endnotes": counts["endNote"],
            "bookmarks": bookmarks,
            "fields": counts["fieldBegin"],
            "page_numbers": counts["pageNum"],
            "headers": counts["header"],
            "footers": counts["footer"],
            "page_breaks": counts["pageBreak"],
            "numberings": header_counts["numbering"],
            "bullets": header_counts["bullet"],
            "tab_stops": header_counts["tabItem"],
            "formatted_paragraph_properties": max(0, header_counts["paraPr"] - header_counts["style"]),
        }
