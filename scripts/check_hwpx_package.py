from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import unquote, urlparse
from zipfile import ZIP_STORED, BadZipFile, LargeZipFile, ZipFile
from xml.etree import ElementTree as ET

from hwpx_package import MIMETYPE_NAME, MIMETYPE_VALUE, REQUIRED_ENTRIES, is_safe_member_name


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _attr(element: ET.Element, local_name: str) -> str | None:
    for key, value in element.attrib.items():
        if _local_name(key) == local_name:
            return value
    return None


def _resolve_manifest_href(href: str, names: set[str]) -> str | None:
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc:
        return None
    clean = unquote(parsed.path).lstrip("./")
    if not clean:
        return None
    candidates = [clean]
    if not clean.startswith(("Contents/", "BinData/", "Preview/", "META-INF/")):
        candidates.append(f"Contents/{clean}")
    return next((candidate for candidate in candidates if candidate in names), candidates[0])


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with ZipFile(path) as zf:
            infos = zf.infolist()
            names_list = [info.filename for info in infos]
            names = set(names_list)

            if not infos:
                return ["Archive is empty."]

            duplicates = sorted({name for name in names_list if names_list.count(name) > 1})
            for name in duplicates:
                errors.append(f"Duplicate ZIP entry: {name}")
            for name in names_list:
                if not is_safe_member_name(name):
                    errors.append(f"Unsafe ZIP entry name: {name}")

            for info in infos:
                if info.flag_bits & 0x1:
                    errors.append(f"Encrypted ZIP entry is unsupported: {info.filename}")

            bad_member = zf.testzip()
            if bad_member:
                errors.append(f"CRC check failed: {bad_member}")

            first = infos[0]
            if first.filename != MIMETYPE_NAME:
                errors.append("mimetype is not the first ZIP entry.")
            if first.filename == MIMETYPE_NAME and first.compress_type != ZIP_STORED:
                errors.append("mimetype must be stored without compression.")

            for required in REQUIRED_ENTRIES:
                if required not in names:
                    errors.append(f"Missing required entry: {required}")

            if MIMETYPE_NAME in names and zf.read(MIMETYPE_NAME) != MIMETYPE_VALUE:
                errors.append(
                    "mimetype payload must be exactly b'application/hwp+zip' "
                    "without a BOM, newline, or surrounding spaces."
                )

            roots: dict[str, ET.Element] = {}
            encrypted_names = {info.filename for info in infos if info.flag_bits & 0x1}
            for name in names_list:
                if name.endswith((".xml", ".hpf")):
                    if name in encrypted_names:
                        continue
                    payload = zf.read(name)
                    if not payload.strip():
                        errors.append(f"XML entry is empty: {name}")
                        continue
                    try:
                        roots[name] = ET.fromstring(payload)
                    except ET.ParseError as exc:
                        errors.append(f"XML parse failed: {name}: {exc}")

            container = roots.get("META-INF/container.xml")
            if container is not None:
                rootfiles = [
                    _attr(element, "full-path")
                    for element in container.iter()
                    if _local_name(element.tag) == "rootfile"
                ]
                rootfiles = [value for value in rootfiles if value]
                if not rootfiles:
                    errors.append("container.xml has no rootfile full-path.")
                for rootfile in rootfiles:
                    if rootfile not in names:
                        errors.append(f"container.xml points to a missing rootfile: {rootfile}")

            content = roots.get("Contents/content.hpf")
            manifest_ids: dict[str, str] = {}
            manifest_targets: set[str] = set()
            if content is not None:
                for element in content.iter():
                    if _local_name(element.tag) != "item":
                        continue
                    item_id = _attr(element, "id")
                    href = _attr(element, "href") or _attr(element, "full-path")
                    if not href:
                        continue
                    target = _resolve_manifest_href(href, names)
                    if target:
                        manifest_targets.add(target)
                    if item_id:
                        if item_id in manifest_ids:
                            errors.append(f"Duplicate manifest item id: {item_id}")
                        manifest_ids[item_id] = target or href
                    if target and target not in names:
                        errors.append(f"content.hpf points to a missing package entry: {href}")

                for element in content.iter():
                    if _local_name(element.tag) != "itemref":
                        continue
                    idref = _attr(element, "idref")
                    if idref and idref not in manifest_ids:
                        errors.append(f"content.hpf spine references an unknown manifest id: {idref}")

                for name in names:
                    if name.startswith("BinData/") and not name.endswith("/") and name not in manifest_targets:
                        errors.append(f"BinData entry not declared in content.hpf: {name}")
                for target in manifest_targets:
                    if target.startswith("BinData/") and target not in names:
                        errors.append(f"Declared BinData entry is missing from the package: {target}")

                section_names = {
                    name
                    for name in names
                    if name.startswith("Contents/section") and name.endswith(".xml")
                }
                for section in section_names:
                    if section not in manifest_targets:
                        errors.append(f"Section entry not declared in content.hpf: {section}")

            if "Preview/PrvText.txt" in names:
                try:
                    zf.read("Preview/PrvText.txt").decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    errors.append(f"Preview/PrvText.txt is not valid UTF-8 text: {exc}")

    except (BadZipFile, LargeZipFile, RuntimeError):
        return ["Not a readable ZIP/HWPX archive."]
    except OSError as exc:
        return [f"Could not read HWPX: {exc}"]

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hwpx", type=Path)
    args = parser.parse_args()

    errors = validate(args.hwpx)
    if errors:
        print("HWPX package validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("HWPX package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
