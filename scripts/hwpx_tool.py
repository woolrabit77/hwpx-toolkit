from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hwpkit import build_document, inspect_document, validate_document
from hwpkit.equations import estimate_equation_box, normalize_equation
from hwpkit.errors import HwpxError
from hwpkit.features import status_report
from hwpkit.templates import list_templates, starter_spec


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(prog="hwpx_tool", description="Standalone HWPX authoring and validation tool")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build an HWPX file from a JSON Document Spec")
    build.add_argument("spec", type=Path)
    build.add_argument("-o", "--output", type=Path, required=True)

    validate = sub.add_parser("validate", help="Validate the HWPX package and internal references")
    validate.add_argument("hwpx", type=Path)
    validate.add_argument("--fast", action="store_true")

    inspect = sub.add_parser("inspect", help="Inspect HWPX features and object counts")
    inspect.add_argument("hwpx", type=Path)

    sub.add_parser("features", help="Show implementation and conformance status")

    sub.add_parser("templates", help="List approved document templates")

    template = sub.add_parser("template", help="Write a starter JSON spec for an approved template")
    template.add_argument("template_id")
    template.add_argument("-o", "--output", type=Path, required=True)

    equation = sub.add_parser("equation", help="Normalize an equation and calculate its automatic box")
    equation.add_argument("script")

    args = parser.parse_args()
    try:
        if args.command == "build":
            _print(build_document(args.spec, args.output))
        elif args.command == "validate":
            result = validate_document(args.hwpx, full=not args.fast)
            _print(result)
            return 0 if result["valid"] else 1
        elif args.command == "inspect":
            _print(inspect_document(args.hwpx))
        elif args.command == "features":
            _print(status_report())
        elif args.command == "templates":
            _print({"templates": list_templates()})
        elif args.command == "template":
            value = starter_spec(args.template_id)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            _print({"output": str(args.output.resolve()), "template": args.template_id})
        else:
            normalized = normalize_equation(args.script)
            width, height, baseline = estimate_equation_box(normalized)
            _print({"normalized": normalized, "width": width, "height": height, "baseline": baseline})
    except (HwpxError, OSError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, HwpxError):
            payload = exc.as_dict()
        else:
            payload = {"code": type(exc).__name__.upper(), "message": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
