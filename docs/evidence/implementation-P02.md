# P02 Luna implementation evidence

## Candidate

- Feature: P02 — semantic headers, footers, editable page-number fields, explicit page breaks, and multi-section documents.
- Initial candidate commit: `2f1598ea37d1223802302de591ad8defd4ff6684`
- Rework candidate commit (current): `17de789a3f71f46cbf2979d0a64510861be2fd6e`
- Worktree: `C:\Users\woolr\Documents\Codex\2026-09-18\new-chat\work\hwpx-toolkit-p02-luna`
- Standalone path: Python HWPX generation and validation only; no Hancom Office, COM, LibreOffice, renderer, network, or web dependency.

## Changed files

- `assets/schemas/document-spec.schema.json`
- `references/document-spec.md`
- `references/HWP_FEATURE_COVERAGE.md`
- `scripts/hwpkit/model.py`
- `scripts/hwpkit/package.py`
- `scripts/hwpkit/spec.py`
- `scripts/hwpkit/validate.py`
- `scripts/hwpkit/writer.py`
- `tests/test_hwpkit.py`
- `tests/fixtures/p02-headers-breaks.json`
- `tests/fixtures/p02-headers-breaks.hwpx`

## Fixture

- JSON: `tests/fixtures/p02-headers-breaks.json`
- HWPX: `tests/fixtures/p02-headers-breaks.hwpx`
- Fixture SHA-256: `0DF499E408264302941A631573457475FD0B616D03014ABBDD624B09A38B9302`
- Expected inspection: 2 sections, 2 headers, 2 footers, 2 native `hp:pageNum` controls, and 1 paragraph-level page break.

## Commands and outcomes

All commands were run from the candidate worktree with the bundled Python runtime:

```powershell
$py='C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m unittest discover -s tests
# Ran 30 tests ... OK

& $py scripts/hwpx_tool.py build tests/fixtures/p02-headers-breaks.json -o work/p02-cli.hwpx
# validation: passed; blocks: 4; sections are emitted as section0 and section1

& $py scripts/hwpx_tool.py validate work/p02-cli.hwpx
# {"valid": true, "errors": []}

& $py scripts/hwpx_tool.py inspect work/p02-cli.hwpx
# entries=11, sections=2, page_numbers=2, headers=2, footers=2, page_breaks=1

& $py scripts/check_hwpx_package.py work/p02-cli.hwpx
# HWPX package validation passed.

Get-FileHash tests/fixtures/p02-headers-breaks.hwpx -Algorithm SHA256
# 0DF499E408264302941A631573457475FD0B616D03014ABBDD624B09A38B9302
```

The positive test checks manifest declaration of `Contents/section1.xml`, semantic header/footer nodes, native page-number controls, and absence of manual page-number text. Negative tests reject unsupported page-number positions, string/manual page-number values, and section-break blocks nested in the `sections` API.

The first Terra cycle identified a fail-open parser defect: ignored keys such as `text` on `page_break` and arbitrary keys alongside header/footer or page-number controls were silently accepted. Rework commit `17de789a3f71f46cbf2979d0a64510861be2fd6e` adds allowlists for all P02 control wrappers and a parser-plus-CLI regression test. Each malformed request now exits with code 2 and leaves no output file.

## Limitations

- Header/footer content is intentionally limited to semantic paragraph/heading text and runs; tables, images, and unsupported objects fail closed.
- Page numbers use native `hp:pageNum` controls with validated positions and formats. No standalone renderer or pagination engine is included.
- Multi-section layout overrides are supported through each section's `metadata`; existing-document round-trip editing remains outside this feature.
