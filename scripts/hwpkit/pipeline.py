from __future__ import annotations

import json
from pathlib import Path

from .errors import ValidationError
from .package import write_package
from .spec import parse_document_spec
from .validate import inspect_hwpx, validate_hwpx
from .writer import serialize_document


def build_document(spec_path: Path, output: Path) -> dict[str, object]:
    raw = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    document, registry = parse_document_spec(raw)
    parts = serialize_document(document, registry)
    write_package(parts, output)
    errors = validate_hwpx(output, full=True)
    if errors:
        try:
            output.unlink()
        except FileNotFoundError:
            pass
        raise ValidationError("Final validation failed:\n- " + "\n- ".join(errors))
    return {
        "output": str(output.resolve()),
        "title": document.title,
        "template": document.template_id,
        "blocks": len(document.blocks),
        "targets": registry.targets,
        "validation": "passed",
    }


def validate_document(path: Path, *, full: bool = True) -> dict[str, object]:
    errors = validate_hwpx(path, full=full)
    return {"path": str(path.resolve()), "valid": not errors, "errors": errors}


def inspect_document(path: Path) -> dict[str, object]:
    result = inspect_hwpx(path)
    result["path"] = str(path.resolve())
    return result
