# P01 implementation evidence

Status: `CANDIDATE`

Feature commit: `95e8656` (`feat: add semantic tabs indents bullets and numbering`)

This report is committed separately from the feature commit. The exact evidence-commit SHA is reported with this file by the coordinator handoff.

## Changed files

- `scripts/hwpkit/model.py`: paragraph model fields for tabs, indents, and list semantics.
- `scripts/hwpkit/spec.py`: public Document Spec parsing and fail-closed validation for tab stops, indents, bullet lists, and numbering lists.
- `scripts/hwpkit/writer.py`: HWPML tab controls, tab properties, paragraph margins, `NUMBER`/`BULLET` heading references, numbering/`paraHead`, and bullet definitions.
- `scripts/hwpkit/validate.py`: semantic list/tab counts in `inspect` output.
- `assets/schemas/document-spec.schema.json`: schema vocabulary for P01 fields.
- `references/document-spec.md`, `references/HWP_FEATURE_COVERAGE.md`: public syntax and support status.
- `tests/test_hwpkit.py`: positive semantic XML regression and negative validation tests.
- `tests/fixtures/p01-tabs-lists.json`: reproducible fixture input.
- `tests/fixtures/p01-tabs-lists.hwpx`: validated fixture artifact.

## Exact checks and results

All commands were run in the P01 Luna worktree with no network, Hancom Office, COM, LibreOffice, or external renderer.

```text
C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v
Ran 25 tests in 0.575s — OK

C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/hwpx_tool.py build tests/fixtures/p01-tabs-lists.json -o tests/fixtures/p01-tabs-lists.hwpx
validation: passed

C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/hwpx_tool.py validate tests/fixtures/p01-tabs-lists.hwpx
valid: true; errors: []

C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/hwpx_tool.py inspect tests/fixtures/p01-tabs-lists.hwpx
entries=10; sections=1; paragraphs=5; numberings=1; bullets=2; tab_stops=2; formatted_paragraph_properties=5

C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/check_hwpx_package.py tests/fixtures/p01-tabs-lists.hwpx
HWPX package validation passed.
```

## Fixture artifact

`tests/fixtures/p01-tabs-lists.hwpx` SHA-256:

`D367E2F5CEE793C0659829CC8179F6AC87C513AC8CFED2518543D4EE725B4D93`

The fixture contains a real `<hp:tab/>`, two tab-stop definitions, margin/first-line indentation, two bullet definitions, and one ten-level numbering definition. List glyphs and numbers are not present in paragraph text.

## Known limits

- The public spec supports one-character bullet glyphs and the documented seven numbering formats.
- Numbering definitions are deterministic for a format/start pair; explicit advanced per-list restart/continuation controls are not exposed.
- This candidate has standalone package/structural validation only; renderer-backed visual review is outside the no-Hancom acceptance path.
