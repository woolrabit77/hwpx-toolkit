from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None


HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
NS = {"hp": HP, "hh": HH}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_or_empty(value: str | None) -> str:
    return (value or "").strip()


def installed_windows_fonts() -> set[str]:
    fonts: set[str] = set()
    if winreg is not None:
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
        ]
        for hive, subkey in keys:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    for index in range(winreg.QueryInfoKey(key)[1]):
                        name, value, _ = winreg.EnumValue(key, index)
                        clean_name = name.split("(")[0].strip()
                        if clean_name:
                            fonts.add(clean_name)
                        stem = Path(str(value)).stem.strip()
                        if stem:
                            fonts.add(stem)
            except OSError:
                pass

    for folder in [Path(r"C:\Windows\Fonts"), Path.home() / r"AppData\Local\Microsoft\Windows\Fonts"]:
        if folder.exists():
            for file in folder.glob("*"):
                if file.suffix.lower() in {".ttf", ".ttc", ".otf"}:
                    fonts.add(file.stem)
    return {font.lower() for font in fonts}


def collect_fonts(header_root: ET.Element | None) -> list[str]:
    if header_root is None:
        return []

    fonts: set[str] = set()
    for elem in header_root.iter():
        if local_name(elem.tag).lower() in {"font", "fontface"}:
            for key, value in elem.attrib.items():
                if local_name(key).lower() in {"face", "name"}:
                    if text_or_empty(value):
                        fonts.add(text_or_empty(value))
    return sorted(fonts)


def count_elements(roots: list[ET.Element], target: str) -> int:
    total = 0
    for root in roots:
        total += sum(1 for elem in root.iter() if local_name(elem.tag) == target)
    return total


def collect_shapes_with_borders(roots: list[ET.Element]) -> list[dict[str, str]]:
    shapes: list[dict[str, str]] = []
    shape_names = {"shapeObject", "container", "line", "rect", "ellipse", "arc", "polygon", "curve", "connectLine"}
    for root in roots:
        for elem in root.iter():
            if local_name(elem.tag) not in shape_names:
                continue
            line_shape = next((child for child in elem.iter() if local_name(child.tag) == "lineShape"), None)
            if line_shape is not None:
                shapes.append(
                    {
                        "tag": local_name(elem.tag),
                        "color": text_or_empty(line_shape.get("color")),
                        "width": text_or_empty(line_shape.get("width")),
                        "style": text_or_empty(line_shape.get("style")),
                    }
                )
    return shapes


def parse_xml_from_zip(zf: ZipFile, name: str) -> ET.Element | None:
    try:
        return ET.fromstring(zf.read(name))
    except Exception:
        return None


def analyze_hwpx(path: Path) -> dict[str, object]:
    installed_fonts = installed_windows_fonts()

    with ZipFile(path) as zf:
        names = zf.namelist()
        header = parse_xml_from_zip(zf, "Contents/header.xml") if "Contents/header.xml" in names else None
        section_names = [name for name in names if name.startswith("Contents/section") and name.endswith(".xml")]
        sections = [root for name in section_names if (root := parse_xml_from_zip(zf, name)) is not None]

        fonts = collect_fonts(header)
        font_status = {
            font: any(font.lower() in installed or installed in font.lower() for installed in installed_fonts)
            for font in fonts
        }

        return {
            "file": str(path),
            "package_entries": len(names),
            "has_header": header is not None,
            "sections": section_names,
            "fonts": font_status,
            "counts": {
                "paragraphs": count_elements(sections, "p"),
                "tables": count_elements(sections, "tbl"),
                "equations": count_elements(sections, "equation"),
                "images": sum(1 for name in names if name.startswith("BinData/")),
                "shape_border_candidates": len(collect_shapes_with_borders(sections)),
            },
            "shape_borders": collect_shapes_with_borders(sections)[:20],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hwpx", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = analyze_hwpx(args.hwpx)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
