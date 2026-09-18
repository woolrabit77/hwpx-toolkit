from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import SpecError


TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "assets" / "templates"
SPEC_ROOT = TEMPLATE_ROOT / "specs"
_PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


def list_templates() -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    if not SPEC_ROOT.exists():
        return templates
    for path in sorted(SPEC_ROOT.glob("*.json")):
        raw = _read_template(path)
        templates.append(
            {
                "id": raw["id"],
                "name": raw["name"],
                "description": raw.get("description", ""),
                "data_fields": sorted((raw.get("defaults") or {}).keys()),
                "golden": str((TEMPLATE_ROOT / "golden" / f"{raw['id']}.hwpx").resolve()),
            }
        )
    return templates


def starter_spec(template_id: str) -> dict[str, Any]:
    template = get_template(template_id)
    return {
        "template": template_id,
        "data": deepcopy(template.get("defaults") or {}),
    }


def apply_template(raw: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    template_id = raw.get("template")
    if template_id in (None, "", "none"):
        return deepcopy(raw), None
    if not isinstance(template_id, str):
        raise SpecError("template must be a string or null.")
    template = get_template(template_id)
    data = template.get("defaults") or {}
    supplied = raw.get("data") or {}
    if not isinstance(supplied, dict):
        raise SpecError("data must be an object when a template is selected.")
    data = {**data, **supplied}
    expanded = _substitute(deepcopy(template.get("spec") or {}), data)
    if not isinstance(expanded, dict):
        raise SpecError(f"Template '{template_id}' has an invalid spec object.")

    base_metadata = expanded.get("metadata") or {}
    request_metadata = raw.get("metadata") or {}
    if not isinstance(base_metadata, dict) or not isinstance(request_metadata, dict):
        raise SpecError("metadata must be an object.")
    expanded["metadata"] = {**base_metadata, **request_metadata, "template_id": template_id}

    request_blocks = raw.get("blocks")
    if request_blocks is not None:
        if not isinstance(request_blocks, list):
            raise SpecError("blocks must be an array.")
        if raw.get("replace_template_blocks", False):
            expanded["blocks"] = deepcopy(request_blocks)
        else:
            expanded["blocks"] = list(expanded.get("blocks") or []) + deepcopy(request_blocks)
    expanded["template"] = None
    return expanded, template_id


def get_template(template_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]+", template_id):
        raise SpecError(f"Invalid template id: {template_id}")
    path = SPEC_ROOT / f"{template_id}.json"
    if not path.is_file():
        available = ", ".join(item["id"] for item in list_templates()) or "none"
        raise SpecError(f"Unknown template '{template_id}'. Available templates: {available}")
    return _read_template(path)


def _read_template(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"Cannot read template '{path.name}': {exc}") from exc
    if not isinstance(raw, dict) or raw.get("id") != path.stem or not raw.get("name"):
        raise SpecError(f"Template metadata is invalid: {path.name}")
    return raw


def _substitute(value: Any, data: dict[str, Any]) -> Any:
    if isinstance(value, list):
        return [_substitute(item, data) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, data) for key, item in value.items()}
    if not isinstance(value, str):
        return value
    full = _PLACEHOLDER.fullmatch(value)
    if full:
        return deepcopy(_lookup(data, full.group(1)))
    return _PLACEHOLDER.sub(lambda match: str(_lookup(data, match.group(1))), value)


def _lookup(data: dict[str, Any], key: str) -> Any:
    current: Any = data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return ""
        current = current[part]
    return "" if current is None else current
