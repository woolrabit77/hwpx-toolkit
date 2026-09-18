from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET
from zipfile import ZIP_STORED, BadZipFile, ZipFile

from .package import MIMETYPE_NAME, MIMETYPE_VALUE, REQUIRED_ENTRIES, safe_name


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
            _validate_container(roots, names, errors)
            _validate_manifest(roots, names, errors)
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


def _validate_container(roots: dict[str, ET.Element], names: set[str], errors: list[str]) -> None:
    root = roots.get("META-INF/container.xml")
    if root is None:
        return
    targets = [_attr(element, "full-path") for element in root.iter() if _local(element.tag) == "rootfile"]
    targets = [target for target in targets if target]
    if not targets:
        errors.append("container.xml has no rootfile.")
    for target in targets:
        if target not in names:
            errors.append(f"container.xml points to a missing entry: {target}")


def _validate_manifest(roots: dict[str, ET.Element], names: set[str], errors: list[str]) -> None:
    root = roots.get("Contents/content.hpf")
    if root is None:
        return
    ids: set[str] = set()
    targets: set[str] = set()
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
    for element in root.iter():
        if _local(element.tag) == "itemref":
            idref = _attr(element, "idref")
            if idref and idref not in ids:
                errors.append(f"Spine points to an unknown manifest ID: {idref}")
    for section in (name for name in names if name.startswith("Contents/section") and name.endswith(".xml")):
        if section not in targets:
            errors.append(f"Section is not declared in the manifest: {section}")


def _resolve_href(href: str) -> str:
    parsed = urlparse(href)
    clean = unquote(parsed.path)
    path = PurePosixPath("Contents") / clean
    parts: list[str] = []
    for part in path.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part not in (".", ""):
            parts.append(part)
    return "/".join(parts)


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
    field_begins: Counter[str] = Counter()
    field_ends: Counter[str] = Counter()
    ids: Counter[tuple[str, str]] = Counter()
    for name, root in roots.items():
        if not name.startswith("Contents/section"):
            continue
        local_counts = Counter(_local(element.tag) for element in root.iter())
        for required in ("secPr", "pagePr", "margin", "colPr"):
            if local_counts[required] == 0:
                errors.append(f"{name}: missing page-layout element: {required}")
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
            if value and local in {"p", "equation", "tbl"}:
                ids[(local, value)] += 1
            if local == "bookmark":
                bookmark = element.get("name", "")
                if not bookmark:
                    errors.append(f"{name}: bookmark has no name")
                elif bookmark in bookmarks:
                    errors.append(f"{name}: duplicate bookmark name: {bookmark}")
                bookmarks.add(bookmark)
            elif local == "fieldBegin":
                field_begins[element.get("id", "")] += 1
            elif local == "fieldEnd":
                field_ends[element.get("id", "")] += 1
            if local == "run":
                _require_declared(name, "charPrIDRef", element, declared["charPr"], errors)
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
        bookmarks: list[str] = []
        for name in names:
            if not (name.startswith("Contents/section") and name.endswith(".xml")):
                continue
            root = ET.fromstring(archive.read(name))
            for element in root.iter():
                counts[_local(element.tag)] += 1
                if _local(element.tag) == "bookmark" and element.get("name"):
                    bookmarks.append(element.get("name", ""))
        return {
            "entries": len(names),
            "sections": len([name for name in names if name.startswith("Contents/section")]),
            "paragraphs": counts["p"],
            "tables": counts["tbl"],
            "equations": counts["equation"],
            "footnotes": counts["footNote"],
            "endnotes": counts["endNote"],
            "bookmarks": bookmarks,
            "fields": counts["fieldBegin"],
        }
