from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile
from xml.etree import ElementTree as ET

from equation_utils import has_normalized_spacing, normalize_equation_script


HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hp": HP}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _has_empty_text_after_equation(run: ET.Element, equation: ET.Element) -> bool:
    children = list(run)
    try:
        index = children.index(equation)
    except ValueError:
        return False

    for child in children[index + 1 :]:
        if _local_name(child.tag) == "t" and (child.text is None or child.text == ""):
            return True
    return False


def _int_attr(element: ET.Element, attr: str) -> int | None:
    value = element.get(attr)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _paragraph_has_equation(paragraph: ET.Element) -> bool:
    return any(_local_name(elem.tag) == "equation" for elem in paragraph.iter())


def _paragraph_text(paragraph: ET.Element) -> str:
    chunks = []
    for elem in paragraph.iter():
        if _local_name(elem.tag) == "t" and elem.text:
            chunks.append(elem.text)
    return "".join(chunks).strip()


def validate_hwpx(
    path: Path,
    expected_count: int | None = None,
    fail_trailing_breaks: bool = False,
    require_auto_size: bool = False,
    require_token_spacing: bool = False,
) -> list[str]:
    errors: list[str] = []
    equation_count = 0

    with ZipFile(path) as zf:
        section_names = [
            name
            for name in zf.namelist()
            if name.startswith("Contents/section") and name.endswith(".xml")
        ]
        if not section_names:
            errors.append("No Contents/section*.xml files found.")
            return errors

        for section_name in section_names:
            root = ET.fromstring(zf.read(section_name))
            paragraphs = [elem for elem in root.iter() if _local_name(elem.tag) == "p"]
            for run in root.findall(".//hp:run", NS):
                for equation in run.findall("hp:equation", NS):
                    equation_count += 1
                    location = f"{section_name} equation #{equation_count}"

                    script = equation.find("hp:script", NS)
                    if script is None or not (script.text or "").strip():
                        errors.append(f"{location}: missing or empty hp:script.")
                    elif require_token_spacing and not has_normalized_spacing(script.text or ""):
                        errors.append(
                            f"{location}: script token spacing is not normalized; suggested: "
                            f"{normalize_equation_script(script.text or '')!r}"
                        )

                    for attr in ["version", "baseUnit", "font", "lineMode"]:
                        if not equation.get(attr):
                            errors.append(f"{location}: missing {attr} attribute.")

                    if equation.get("lineMode") and equation.get("lineMode") != "CHAR":
                        errors.append(f"{location}: lineMode should usually be CHAR for inline equations.")

                    size = equation.find("hp:sz", NS)
                    if size is None:
                        errors.append(f"{location}: missing hp:sz.")
                    else:
                        width = _int_attr(size, "width")
                        height = _int_attr(size, "height")
                        base_unit = _int_attr(equation, "baseUnit")
                        if require_auto_size and (width != 0 or height != 0):
                            errors.append(
                                f"{location}: auto-size requires hp:sz width=0 and height=0 "
                                "before the Hancom renderer round-trip."
                            )
                        if height is not None and base_unit is not None and height > base_unit * 4:
                            errors.append(
                                f"{location}: hp:sz height looks large relative to baseUnit; "
                                "this can leave abnormal equation spacing."
                            )

                    pos = equation.find("hp:pos", NS)
                    if pos is None:
                        errors.append(f"{location}: missing hp:pos.")
                    else:
                        if pos.get("treatAsChar") != "1":
                            errors.append(f"{location}: hp:pos treatAsChar should be 1 for inline flow.")
                        if pos.get("vertRelTo") and pos.get("vertRelTo") != "PARA":
                            errors.append(f"{location}: hp:pos vertRelTo should usually be PARA.")
                        if pos.get("horzRelTo") and pos.get("horzRelTo") != "PARA":
                            errors.append(f"{location}: hp:pos horzRelTo should usually be PARA.")

                    out_margin = equation.find("hp:outMargin", NS)
                    if out_margin is not None:
                        for edge in ["top", "bottom"]:
                            value = _int_attr(out_margin, edge)
                            if value and value > 0:
                                errors.append(
                                    f"{location}: hp:outMargin {edge} is non-zero; "
                                    "this can create extra equation spacing."
                                )

                    if not _has_empty_text_after_equation(run, equation):
                        errors.append(f"{location}: missing empty hp:t after equation.")

            if fail_trailing_breaks:
                for index, paragraph in enumerate(paragraphs[:-1]):
                    if not _paragraph_has_equation(paragraph):
                        continue
                    next_paragraph = paragraphs[index + 1]
                    if not _paragraph_text(next_paragraph) and not _paragraph_has_equation(next_paragraph):
                        errors.append(
                            f"{section_name} paragraph #{index + 1}: equation is followed by "
                            "an empty paragraph; avoid adding a line break after an inline equation."
                        )

    if expected_count is not None and equation_count != expected_count:
        errors.append(
            f"Equation count mismatch: expected {expected_count}, found {equation_count}."
        )
    if equation_count == 0:
        errors.append("No hp:equation elements found.")

    return errors


def make_sample_hwpx(path: Path) -> None:
    section_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hp="{HP}" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">
  <hp:p id="1" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
    <hp:run charPrIDRef="1">
      <hp:t>Equation </hp:t>
    </hp:run>
    <hp:run charPrIDRef="1">
      <hp:equation id="1001" zOrder="0" numberingType="EQUATION"
          textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0"
          version="Equation Version 60" baseLine="85"
          textColor="#000000" baseUnit="1000" lineMode="CHAR" font="HYhwpEQ">
        <hp:sz width="0" widthRelTo="ABSOLUTE"
               height="0" heightRelTo="ABSOLUTE" protect="0"/>
        <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1"
                allowOverlap="0" holdAnchorAndSO="0"
                vertRelTo="PARA" horzRelTo="PARA"
                vertAlign="TOP" horzAlign="LEFT"
                vertOffset="0" horzOffset="0"/>
        <hp:outMargin left="56" right="56" top="0" bottom="0"/>
        <hp:shapeComment>Editable equation.</hp:shapeComment>
        <hp:script>x^rm{{2}} + rm{{3}} x + rm{{2}} = rm{{0}}</hp:script>
      </hp:equation>
      <hp:t/>
    </hp:run>
  </hp:p>
</hs:sec>
"""
    with ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip", compress_type=ZIP_STORED)
        zf.writestr("Contents/section0.xml", section_xml, compress_type=ZIP_DEFLATED)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hwpx", nargs="?", type=Path)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--fail-trailing-breaks", action="store_true")
    parser.add_argument("--require-auto-size", action="store_true")
    parser.add_argument("--require-token-spacing", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample_equation.hwpx"
            make_sample_hwpx(sample)
            errors = validate_hwpx(
                sample,
                expected_count=1,
                require_auto_size=True,
                require_token_spacing=True,
            )
    elif args.hwpx:
        errors = validate_hwpx(
            args.hwpx,
            expected_count=args.expected_count,
            fail_trailing_breaks=args.fail_trailing_breaks,
            require_auto_size=args.require_auto_size,
            require_token_spacing=args.require_token_spacing,
        )
    else:
        parser.error("provide an HWPX path or --self-test")

    if errors:
        print("Equation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Equation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
