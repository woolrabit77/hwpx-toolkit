from __future__ import annotations

import json
import base64
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from scripts.export_skill import export_skill
from scripts.hwpkit.equations import estimate_equation_box, normalize_equation
from scripts.hwpkit.errors import ConformanceError, SpecError
from scripts.hwpkit.formulas import evaluate_formula
from scripts.hwpkit.pipeline import build_document, inspect_document, validate_document
from scripts.hwpkit.spec import parse_document_spec
from scripts.hwpkit.templates import list_templates, starter_spec
from scripts.hwpkit.writer import MIN_FONT_SIZE, STYLE_SPECS


class EquationTests(unittest.TestCase):
    def test_normalizes_independent_tokens_without_splitting_decimal(self) -> None:
        self.assertEqual(normalize_equation("12.5+2x=0"), "12.5 + 2 x = 0")

    def test_box_grows_for_fraction(self) -> None:
        simple = estimate_equation_box("x+1")
        fraction = estimate_equation_box("{x+1} over {y+2}")
        self.assertGreater(fraction[1], simple[1])


class FormulaTests(unittest.TestCase):
    def test_sum(self) -> None:
        rows = [["Item", "Amount"], ["A", 100], ["B", 200]]
        self.assertEqual(evaluate_formula("SUM(B2:B3)", rows), 300)

    def test_extended_safe_formula_grammar(self) -> None:
        rows = [["Item", 10, 20], ["Total", {"formula": "SUM(B1:C1) * 2"}, 5]]
        self.assertEqual(evaluate_formula("B2+C2", rows), 65)

    def test_unsafe_or_ambiguous_formula_fails_closed(self) -> None:
        with self.assertRaisesRegex(SpecError, "Unsupported table formula"):
            evaluate_formula("__import__('os').system('x')", [[1]])
        with self.assertRaisesRegex(SpecError, "division by zero"):
            evaluate_formula("1/0", [[1]])
        with self.assertRaisesRegex(SpecError, "covered cell"):
            evaluate_formula("SUM(A1:B1)", [[{"value": 1}, {"covered": True}]])


class SpecTests(unittest.TestCase):
    def test_locked_feature_fails_closed(self) -> None:
        with self.assertRaises(ConformanceError):
            parse_document_spec({"blocks": [{"type": "chart"}]})

    def test_unknown_template_is_rejected(self) -> None:
        with self.assertRaises(SpecError):
            parse_document_spec({"template": "report", "blocks": []})

    def test_broken_internal_link_is_rejected(self) -> None:
        with self.assertRaises(SpecError):
            parse_document_spec(
                {"blocks": [{"type": "paragraph", "runs": [{"text": "x", "hyperlink": "#missing"}]}]}
            )

    def test_unknown_layout_profile_is_rejected(self) -> None:
        with self.assertRaises(SpecError):
            parse_document_spec({"metadata": {"layout": {"profile": "unknown"}}, "blocks": []})

    def test_p01_rejects_invalid_list_level_and_tab_order(self) -> None:
        with self.assertRaisesRegex(SpecError, "between 1 and 10"):
            parse_document_spec({"blocks": [{"type": "paragraph", "numbering": {"level": 11}, "text": "x"}]})
        with self.assertRaisesRegex(SpecError, "strictly increasing"):
            parse_document_spec({"blocks": [{"type": "paragraph", "tabs": [{"position": 100}, {"position": 100}], "text": "x"}]})

    def test_p01_rejects_invalid_number_format(self) -> None:
        with self.assertRaisesRegex(SpecError, "Number format"):
            parse_document_spec({"blocks": [{"type": "paragraph", "numbering": {"format": "EMOJI"}, "text": "x"}]})

    def test_p01_rejects_non_json_integer_fields(self) -> None:
        invalid_specs = [
            {"blocks": [{"type": "paragraph", "numbering": {"level": True}, "text": "x"}]},
            {"blocks": [{"type": "paragraph", "tabs": [{"position": 1200.5}], "text": "x"}]},
            {"blocks": [{"type": "paragraph", "indent": {"left": "1200"}, "text": "x"}]},
        ]
        for invalid in invalid_specs:
            with self.subTest(spec=invalid), self.assertRaisesRegex(SpecError, "JSON integer"):
                parse_document_spec(invalid)

    def test_p03_places_real_spans_and_rejects_overlap(self) -> None:
        document, _ = parse_document_spec({
            "blocks": [{
                "type": "table",
                "rows": [[{"value": "A", "span": {"rows": 2, "cols": 2}}, "B"], ["C"]],
            }]
        })
        table = document.blocks[0]
        self.assertEqual(table.col_count, 3)
        self.assertEqual((table.rows[0][0].row_span, table.rows[0][0].col_span), (2, 2))
        self.assertEqual((table.rows[1][0].row_index, table.rows[1][0].col_index), (1, 2))
        with self.assertRaisesRegex(SpecError, "outside the table"):
            parse_document_spec({"blocks": [{"type": "table", "rows": [[{"value": "A", "span": {"rows": 2}}]]}]})

    def test_p03_rejects_ambiguous_shading_and_split(self) -> None:
        with self.assertRaisesRegex(SpecError, "six-digit"):
            parse_document_spec({"blocks": [{"type": "table", "shading": "yellow", "rows": [["A"]]}]})
        with self.assertRaisesRegex(SpecError, "split"):
            parse_document_spec({"blocks": [{"type": "table", "split": "page", "rows": [["A"]]}]})

    def test_p03_formula_failure_fixture_is_rejected(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "p03-table-formula-failure.json"
        with self.assertRaisesRegex(SpecError, "Unsupported table formula function"):
            parse_document_spec(json.loads(fixture.read_text(encoding="utf-8")))


class PipelineTests(unittest.TestCase):
    def test_all_generated_styles_are_at_least_ten_points(self) -> None:
        self.assertTrue(STYLE_SPECS)
        self.assertTrue(all(int(style["size"]) >= MIN_FONT_SIZE for style in STYLE_SPECS))

    def test_table_cell_image_is_embedded_and_declared(self) -> None:
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "portrait.png"
            image_path.write_bytes(png)
            spec = {
                "metadata": {"title": "Image test", "author": "Codex"},
                "blocks": [{
                    "type": "table",
                    "header_rows": 0,
                    "row_heights_mm": [40],
                    "rows": [[{"image": {"path": "portrait.png", "width_mm": 30, "alt": "Portrait"}}]],
                }],
            }
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            self.assertTrue(validate_document(output)["valid"])
            self.assertEqual(inspect_document(output)["images"], 1)
            with ZipFile(output) as archive:
                self.assertEqual(archive.read("BinData/image1.png"), png)
                content = archive.read("Contents/content.hpf")
                section = archive.read("Contents/section0.xml")
                self.assertIn(b'id="image1"', content)
                self.assertIn(b'binaryItemIDRef="image1"', section)

    def test_untitled_document_uses_standard_a4_margins_and_table_grid_borders(self) -> None:
        spec = {
            "metadata": {"title": "Defaults", "author": "Codex"},
            "blocks": [{"type": "table", "header_rows": 0, "rows": [["A", "B"]]}],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as archive:
                section = ET.fromstring(archive.read("Contents/section0.xml"))
                margin = next(element for element in section.iter() if element.tag.rsplit("}", 1)[-1] == "margin")
                self.assertEqual(margin.get("left"), str(round(30 * 283.466)))
                self.assertEqual(margin.get("right"), str(round(30 * 283.466)))
                self.assertEqual(margin.get("top"), str(round(20 * 283.466)))
                self.assertEqual(margin.get("bottom"), str(round(15 * 283.466)))
                table = next(element for element in section.iter() if element.tag.rsplit("}", 1)[-1] == "tbl")
                self.assertEqual(table.get("borderFillIDRef"), "1")

    def test_build_validate_and_inspect(self) -> None:
        spec = {
            "template": None,
            "metadata": {"title": "Test", "author": "Codex"},
            "blocks": [
                {"type": "heading", "level": 1, "text": "Overview", "bookmark": "overview"},
                {"type": "paragraph", "runs": [{"text": "Overview", "hyperlink": "#overview"}]},
                {"type": "equation", "script": "12.5+2x=0"},
                {
                    "type": "table",
                    "rows": [["Item", "Amount"], ["A", 100], ["B", 200], ["Total", {"formula": "SUM(B2:B3)"}]],
                    "caption": "Cost",
                    "bookmark": "costs"
                },
                {"type": "footnote", "text": "Footnote text"},
                {"type": "toc", "levels": [1]}
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = build_document(spec_path, output)
            self.assertEqual(result["validation"], "passed")
            self.assertTrue(validate_document(output)["valid"])
            inspected = inspect_document(output)
            self.assertEqual(inspected["tables"], 1)
            self.assertEqual(inspected["equations"], 1)
            self.assertEqual(inspected["footnotes"], 1)

    def test_build_emits_complete_hancom_package_and_root_relative_manifest_paths(self) -> None:
        spec = {"metadata": {"title": "Package test", "author": "Codex"}, "blocks": []}
        required = {
            "version.xml",
            "settings.xml",
            "META-INF/manifest.xml",
            "META-INF/container.rdf",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as archive:
                self.assertTrue(required.issubset(archive.namelist()))
                content = ET.fromstring(archive.read("Contents/content.hpf"))
                items = {
                    element.get("id"): (element.get("href"), element.get("media-type"))
                    for element in content.iter()
                    if element.tag.rsplit("}", 1)[-1] == "item"
                }
                self.assertEqual(items["header"], ("Contents/header.xml", "application/xml"))
                self.assertEqual(items["section0"], ("Contents/section0.xml", "application/xml"))
                self.assertEqual(items["settings"], ("settings.xml", "application/xml"))
                spine = [
                    element.get("idref")
                    for element in content.iter()
                    if element.tag.rsplit("}", 1)[-1] == "itemref"
                ]
                self.assertEqual(spine, ["header", "section0"])

    def test_build_emits_hancom_compatible_rdf_and_complete_section_properties(self) -> None:
        spec = {"metadata": {"title": "Compatibility", "author": "Codex"}, "blocks": []}
        required_secpr_children = {
            "grid",
            "startNum",
            "visibility",
            "lineNumberShape",
            "pagePr",
            "footNotePr",
            "endNotePr",
            "pageBorderFill",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as archive:
                rdf = archive.read("META-INF/container.rdf")
                self.assertTrue(
                    rdf.startswith(b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>')
                )
                rdf_root = rdf.split(b">", 2)[1]
                self.assertNotIn(b"xmlns:pkg=", rdf_root)
                self.assertNotIn(b"xmlns:ns0=", rdf_root)
                self.assertEqual(rdf.count(b"<ns0:hasPart xmlns:ns0="), 2)
                section = ET.fromstring(archive.read("Contents/section0.xml"))
                sec_pr = next(
                    element for element in section.iter() if element.tag.rsplit("}", 1)[-1] == "secPr"
                )
                children = {child.tag.rsplit("}", 1)[-1] for child in sec_pr}
                self.assertTrue(required_secpr_children.issubset(children))

    def test_validator_rejects_package_missing_hancom_required_part(self) -> None:
        spec = {"metadata": {"title": "Corruption test", "author": "Codex"}, "blocks": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            broken = root / "broken.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as source, ZipFile(broken, "w") as target:
                for info in source.infolist():
                    if info.filename == "version.xml":
                        continue
                    compression = ZIP_STORED if info.filename == "mimetype" else ZIP_DEFLATED
                    target.writestr(info.filename, source.read(info.filename), compress_type=compression)
            result = validate_document(broken)
            self.assertFalse(result["valid"])
            self.assertTrue(any("version.xml" in error for error in result["errors"]))

    def test_validator_rejects_legacy_content_hpf_relative_paths(self) -> None:
        spec = {"metadata": {"title": "Path test", "author": "Codex"}, "blocks": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            broken = root / "broken.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as source, ZipFile(broken, "w") as target:
                for info in source.infolist():
                    payload = source.read(info.filename)
                    if info.filename == "Contents/content.hpf":
                        payload = payload.replace(b'href="Contents/header.xml"', b'href="header.xml"')
                    compression = ZIP_STORED if info.filename == "mimetype" else ZIP_DEFLATED
                    target.writestr(info.filename, payload, compress_type=compression)
            result = validate_document(broken)
            self.assertFalse(result["valid"])
            self.assertTrue(any("header" in error for error in result["errors"]))

    def test_validator_rejects_elementtree_style_rdf_serialization(self) -> None:
        spec = {"metadata": {"title": "RDF test", "author": "Codex"}, "blocks": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            broken = root / "broken.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as source, ZipFile(broken, "w") as target:
                for info in source.infolist():
                    payload = source.read(info.filename)
                    if info.filename == "META-INF/container.rdf":
                        payload = payload.replace(
                            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
                            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:pkg="http://www.hancom.co.kr/hwpml/2016/meta/pkg#">',
                        )
                    compression = ZIP_STORED if info.filename == "mimetype" else ZIP_DEFLATED
                    target.writestr(info.filename, payload, compress_type=compression)
            result = validate_document(broken)
            self.assertFalse(result["valid"])
            self.assertTrue(any("package namespace" in error for error in result["errors"]))

    def test_validator_rejects_incomplete_section_properties(self) -> None:
        spec = {"metadata": {"title": "Section test", "author": "Codex"}, "blocks": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            broken = root / "broken.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as source, ZipFile(broken, "w") as target:
                for info in source.infolist():
                    payload = source.read(info.filename)
                    if info.filename == "Contents/section0.xml":
                        payload = payload.replace(
                            b'<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0" />',
                            b"",
                            1,
                        )
                    compression = ZIP_STORED if info.filename == "mimetype" else ZIP_DEFLATED
                    target.writestr(info.filename, payload, compress_type=compression)
            result = validate_document(broken)
            self.assertFalse(result["valid"])
            self.assertTrue(any("secPr" in error and "grid" in error for error in result["errors"]))

    def test_all_generated_text_colors_are_black(self) -> None:
        spec = {
            "metadata": {"title": "Black text", "author": "Codex"},
            "blocks": [
                {"type": "paragraph", "runs": [{"text": "Link", "hyperlink": "https://example.com"}]},
                {"type": "equation", "script": "x+1=2"},
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            build_document(spec_path, output)
            with ZipFile(output) as archive:
                for name in ("Contents/header.xml", "Contents/section0.xml"):
                    xml = ET.fromstring(archive.read(name))
                    colors = [element.get("textColor") for element in xml.iter() if element.get("textColor")]
                    self.assertTrue(colors)
                    self.assertEqual(set(colors), {"#000000"})

    def test_p03_spans_shading_and_split_are_native_hwpml(self) -> None:
        spec = {
            "metadata": {"title": "P03", "author": "Codex"},
            "blocks": [{
                "type": "table",
                "header_rows": 1,
                "shading": "#EAF2F8",
                "split": "none",
                "rows": [
                    [{"value": "Merged", "span": {"rows": 2, "cols": 2}}, {"value": "Value", "shading": "#FFF2CC"}],
                    ["Detail"],
                    ["A", 10, 20],
                    ["Total", {"formula": "SUM(B3:C3)+5"}],
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            build_document(spec_path, output)
            self.assertTrue(validate_document(output)["valid"])
            with ZipFile(output) as archive:
                header = ET.fromstring(archive.read("Contents/header.xml"))
                section = ET.fromstring(archive.read("Contents/section0.xml"))
                border_fills = [element for element in header.iter() if element.tag.rsplit("}", 1)[-1] == "borderFill"]
                self.assertTrue(any((brush := element.find(".//{*}winBrush")) is not None and brush.get("faceColor") == "#EAF2F8" for element in border_fills))
                self.assertTrue(any((brush := element.find(".//{*}winBrush")) is not None and brush.get("faceColor") == "#FFF2CC" for element in border_fills))
                table = next(element for element in section.iter() if element.tag.rsplit("}", 1)[-1] == "tbl")
                self.assertEqual(table.get("pageBreak"), "NONE")
                spans = [element.find("{*}cellSpan") for element in table.iter() if element.tag.rsplit("}", 1)[-1] == "tc"]
                self.assertIn({"colSpan": "2", "rowSpan": "2"}, [span.attrib for span in spans])
                text = "".join(element.text or "" for element in section.iter() if element.tag.rsplit("}", 1)[-1] == "t")
                self.assertIn("35", text)


class P01Tests(unittest.TestCase):
    def test_cli_rejects_non_json_integer_and_leaves_no_output(self) -> None:
        invalid_specs = [
            {"blocks": [{"type": "paragraph", "numbering": {"level": True}, "text": "x"}]},
            {"blocks": [{"type": "paragraph", "tabs": [{"position": 1200.5}], "text": "x"}]},
        ]
        tool = Path(__file__).resolve().parents[1] / "scripts" / "hwpx_tool.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, invalid in enumerate(invalid_specs):
                spec_path = root / f"invalid-{index}.json"
                output = root / f"invalid-{index}.hwpx"
                spec_path.write_text(json.dumps(invalid), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(tool), "build", str(spec_path), "-o", str(output)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("JSON integer", result.stderr)
                self.assertFalse(output.exists())

    def test_tabs_indents_bullets_and_numbering_are_semantic_hwpml(self) -> None:
        spec = {
            "metadata": {"title": "P01", "author": "Codex"},
            "blocks": [
                {"type": "paragraph", "tabs": [{"position": 2400, "type": "LEFT"}], "indent": {"left": 1200, "first_line": -600}, "text": "Tabbed\tbody"},
                {"type": "paragraph", "bullet": {"level": 2, "char": "▪"}, "text": "Bullet item"},
                {"type": "paragraph", "numbering": {"level": 1, "start": 1, "format": "DIGIT"}, "text": "Number item"},
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = build_document(spec_path, output)
            self.assertEqual(result["validation"], "passed")
            self.assertTrue(validate_document(output)["valid"])
            inspected = inspect_document(output)
            self.assertEqual(inspected["numberings"], 1)
            self.assertEqual(inspected["bullets"], 1)
            self.assertEqual(inspected["tab_stops"], 1)
            with ZipFile(output) as archive:
                header = ET.fromstring(archive.read("Contents/header.xml"))
                section = ET.fromstring(archive.read("Contents/section0.xml"))
                local = lambda element: element.tag.rsplit("}", 1)[-1]
                numbering = next(element for element in header.iter() if local(element) == "numbering")
                self.assertEqual(len([element for element in numbering if local(element) == "paraHead"]), 10)
                self.assertEqual(next(element for element in header.iter() if local(element) == "bullet").get("char"), "▪")
                tabs = [element for element in header.iter() if local(element) == "tabItem"]
                self.assertEqual(tabs[0].get("pos"), "2400")
                self.assertEqual(len([element for element in section.iter() if local(element) == "tab"]), 1)
                dynamic = [element for element in header.iter() if local(element) == "paraPr" and element.get("id") not in {str(index) for index in range(len(STYLE_SPECS))}]
                self.assertEqual(len(dynamic), 3)
                self.assertTrue(any(element.find("{*}heading").get("type") == "BULLET" for element in dynamic))
                self.assertTrue(any(element.find("{*}heading").get("type") == "NUMBER" for element in dynamic))
                paragraphs = [element for element in section.iter() if local(element) == "p"]
                text = "".join(element.text or "" for element in section.iter() if local(element) == "t")
                self.assertEqual(text, "TabbedbodyBullet itemNumber item")
                self.assertNotIn("• Bullet", text)
                self.assertTrue(all(element.get("paraPrIDRef") != "0" for element in paragraphs[:3]))


class P02Tests(unittest.TestCase):
    def test_headers_footers_page_numbers_and_breaks_are_semantic(self) -> None:
        spec = {
            "metadata": {"title": "P02", "author": "Codex"},
            "sections": [
                {
                    "header": "First header",
                    "footer": {"text": "First footer"},
                    "page_number": {"position": "BOTTOM_CENTER", "format": "DIGIT", "side_char": "-"},
                    "blocks": [{"type": "paragraph", "text": "First"}, {"type": "page_break"}],
                },
                {
                    "header": "Second header",
                    "footer": "Second footer",
                    "page_number": {"position": "TOP_RIGHT", "start": 3},
                    "blocks": [{"type": "paragraph", "text": "Second"}],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec_path = root / "request.json"
            output = root / "result.hwpx"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            build_document(spec_path, output)
            inspected = inspect_document(output)
            self.assertEqual(inspected["sections"], 2)
            self.assertEqual(inspected["headers"], 2)
            self.assertEqual(inspected["footers"], 2)
            self.assertEqual(inspected["page_numbers"], 2)
            self.assertEqual(inspected["page_breaks"], 1)
            self.assertTrue(validate_document(output)["valid"])
            with ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("Contents/section1.xml", names)
                content = archive.read("Contents/content.hpf")
                self.assertIn(b'href="Contents/section1.xml"', content)
                section = ET.fromstring(archive.read("Contents/section1.xml"))
                self.assertTrue(any(element.tag.rsplit("}", 1)[-1] == "pageNum" for element in section.iter()))
                self.assertFalse(any((element.text or "").strip() in {"1", "2", "3"} for element in section.iter() if element.tag.rsplit("}", 1)[-1] == "t"))

    def test_p02_rejects_manual_or_unsupported_page_number_variants(self) -> None:
        with self.assertRaisesRegex(SpecError, "position"):
            parse_document_spec({"sections": [{"page_number": {"position": "CENTER"}, "blocks": []}]})
        with self.assertRaisesRegex(SpecError, "page_number"):
            parse_document_spec({"sections": [{"page_number": "1", "blocks": []}]})
        with self.assertRaisesRegex(SpecError, "section_break"):
            parse_document_spec({"sections": [{"blocks": [{"type": "section_break"}]}]})

    def test_p02_rejects_unknown_control_keys_and_cli_leaves_no_output(self) -> None:
        invalid_specs = [
            {"blocks": [{"type": "page_break", "text": "not allowed"}]},
            {"blocks": [{"type": "section_break", "unexpected": True}]},
            {"sections": [{"page_number": {"position": "BOTTOM_CENTER", "unknown": True}, "blocks": []}]},
            {"sections": [{"header": {"text": "Header", "unknown": True}, "blocks": []}]},
        ]
        tool = Path(__file__).resolve().parents[1] / "scripts" / "hwpx_tool.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, invalid in enumerate(invalid_specs):
                spec_path = root / f"invalid-{index}.json"
                output = root / f"invalid-{index}.hwpx"
                spec_path.write_text(json.dumps(invalid), encoding="utf-8")
                with self.subTest(spec=invalid):
                    with self.assertRaisesRegex(SpecError, "unsupported"):
                        parse_document_spec(invalid)
                    result = subprocess.run(
                        [sys.executable, str(tool), "build", str(spec_path), "-o", str(output)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("unsupported", result.stderr)
                    self.assertFalse(output.exists())


class TemplateTests(unittest.TestCase):
    def test_template_data_populates_document_metadata(self) -> None:
        spec = starter_spec("official-letter")
        spec["data"]["subject"] = "Bound title"
        document, _ = parse_document_spec(spec)
        self.assertEqual(document.title, "Bound title")

    def test_all_approved_templates_build_and_validate(self) -> None:
        templates = list_templates()
        self.assertEqual(len(templates), 8)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for item in templates:
                template_id = item["id"]
                spec_path = root / f"{template_id}.json"
                output = root / f"{template_id}.hwpx"
                spec_path.write_text(json.dumps(starter_spec(template_id), ensure_ascii=False), encoding="utf-8")
                result = build_document(spec_path, output)
                self.assertEqual(result["template"], template_id)
                self.assertTrue(validate_document(output)["valid"])
                with ZipFile(output) as archive:
                    preview = archive.read("Preview/PrvText.txt").decode("utf-8")
                    self.assertNotIn("{{", preview)

    def test_two_column_templates_emit_two_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for template_id in ("kice-exam", "academic-stem"):
                spec_path = root / f"{template_id}.json"
                output = root / f"{template_id}.hwpx"
                spec_path.write_text(json.dumps(starter_spec(template_id)), encoding="utf-8")
                build_document(spec_path, output)
                with ZipFile(output) as archive:
                    section = archive.read("Contents/section0.xml").decode("utf-8")
                    self.assertIn('colCount="2"', section)


class ExportTests(unittest.TestCase):
    def test_export_is_valid_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first.zip"
            second = Path(temp) / "second.zip"
            one = export_skill(first)
            two = export_skill(second)
            self.assertEqual(one["sha256"], two["sha256"])
            with ZipFile(first) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("hwp-hwpx-document-automation/SKILL.md", archive.namelist())


if __name__ == "__main__":
    unittest.main()
