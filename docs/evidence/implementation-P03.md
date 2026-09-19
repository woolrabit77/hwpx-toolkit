# P03 implementation evidence (Luna candidate)

Status: `CANDIDATE`

Final candidate feature commit: `PENDING_COMMIT_SHA`

Scope: public Document Spec support for native table cell spans, safe table split modes, table/cell shading, and the extended safe formula grammar. The central feature-verification checklist was not edited.

## Changed files

- `scripts/hwpkit/model.py`: span, shading, split, and logical-grid model fields.
- `scripts/hwpkit/spec.py`: span-aware placement, strict color/split validation, formula dependency preparation, and fail-closed ambiguity checks.
- `scripts/hwpkit/writer.py`: native `hp:cellSpan`, `pageBreak`, and `hh:fillBrush`/`hc:winBrush` border-fill emission.
- `scripts/hwpkit/formulas.py`: tokenized aggregate/arithmetic formula parser with range, dependency, cycle, and division checks.
- `assets/schemas/document-spec.schema.json`, `references/document-spec.md`, `references/HWP_FEATURE_COVERAGE.md`, `references/feature-status.md`.
- `tests/test_hwpkit.py` and `tests/fixtures/p03-table-semantics.{json,hwpx}`, `tests/fixtures/p03-table-formula-failure.json`.

## Reproducible checks

All commands were run from this worktree with the bundled standalone Python runtime:

```powershell
$py='C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m unittest discover -s tests
& $py scripts\hwpx_tool.py build tests\fixtures\p03-table-semantics.json -o tests\fixtures\p03-table-semantics.hwpx
& $py scripts\hwpx_tool.py validate tests\fixtures\p03-table-semantics.hwpx
& $py scripts\hwpx_tool.py inspect tests\fixtures\p03-table-semantics.hwpx
& $py scripts\check_hwpx_package.py tests\fixtures\p03-table-semantics.hwpx
& $py scripts\hwpx_tool.py build tests\fixtures\p03-table-formula-failure.json -o tests\fixtures\p03-table-formula-failure.hwpx
```

Results:

- Full suite: `33 tests`, `OK`.
- Fixture build: passed; output validation: passed.
- Fixture `validate`: `valid: true`, no errors.
- Fixture `inspect`: `tables: 1`, `fields: 1`, `sections: 1`.
- Package checker: `HWPX package validation passed.`
- Formula-failure fixture: rejected with `Unsupported table formula function: UNKNOWN`, exit code `2`, and no output file.
- Determinism: rebuilding the fixture produced the same SHA-256.

## Artifact identity

`tests/fixtures/p03-table-semantics.hwpx` SHA-256:

`67D81575C37F6E200928267936A29FFEC9AF1B995A6CFD992FEEF1D0F119D86F`

## Known limits

- Spans use the sequential logical-grid form; explicit coordinate placement and ambiguous/overlapping declarations are rejected.
- Shading accepts opaque six-digit `#RRGGBB` colors and uses native HWP border-fill brushes; gradients, patterns, transparency, and renderer-dependent colors are unsupported.
- `split` is limited to HWPML `CELL`, `TABLE`, and `NONE`; pagination is not externally rendered in the standalone path.
- Formulas are intentionally bounded to cell references, rectangular ranges, numeric constants, parentheses, `+ - * /`, and `SUM`, `AVERAGE`, `PRODUCT`, `MIN`, `MAX`. Cross-table references, volatile functions, strings, and covered merged cells fail closed.
- No Hancom Office, COM, LibreOffice, web/network access, or external renderer is used by the authoring or validation path.
