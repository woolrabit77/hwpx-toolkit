from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.export_skill import export_skill
from scripts.hwpkit.equations import estimate_equation_box, normalize_equation
from scripts.hwpkit.errors import ConformanceError, SpecError
from scripts.hwpkit.formulas import evaluate_formula
from scripts.hwpkit.pipeline import build_document, inspect_document, validate_document
from scripts.hwpkit.spec import parse_document_spec
from scripts.hwpkit.templates import list_templates, starter_spec


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


class PipelineTests(unittest.TestCase):
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


class TemplateTests(unittest.TestCase):
    def test_template_data_populates_document_metadata(self) -> None:
        spec = starter_spec("official-letter")
        spec["data"]["subject"] = "Bound title"
        document, _ = parse_document_spec(spec)
        self.assertEqual(document.title, "Bound title")

    def test_all_approved_templates_build_and_validate(self) -> None:
        templates = list_templates()
        self.assertEqual(len(templates), 7)
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
