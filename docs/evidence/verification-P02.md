# P02 independent Terra verification — rework cycle 2

## Candidate and scope

- Reviewed candidate SHA: `96de7e99cbcccab3900407a1fe483a80e94487ad`.
- P02 fail-closed implementation SHA: `17de789a3f71f46cbf2979d0a64510861be2fd6e`;
  the reviewed tip additionally updates Luna's evidence.
- This verifier branch is `terra/p02-verification-96de7e9`. Only this report
  is added here; the central checklist was not changed.

## Independently rerun commands and results

All commands ran in this verification worktree with
`C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
Temporary artifacts were created under the system temporary directory and were
removed at command exit.

```powershell
& $py -m unittest discover -s tests
```

**PASS:** 30 tests ran, `OK`.

```powershell
& $py scripts/hwpx_tool.py build tests/fixtures/p02-headers-breaks.json -o $temp\p02-cli.hwpx
& $py scripts/hwpx_tool.py validate $temp\p02-cli.hwpx
& $py scripts/hwpx_tool.py inspect $temp\p02-cli.hwpx
& $py scripts/check_hwpx_package.py $temp\p02-cli.hwpx
Get-FileHash $temp\p02-cli.hwpx -Algorithm SHA256
Get-FileHash tests/fixtures/p02-headers-breaks.hwpx -Algorithm SHA256
```

**PASS:** build returned `validation: passed`; full validate returned
`{"valid": true, "errors": []}`; the package checker passed. `inspect`
reported 11 entries, 2 sections, 2 headers, 2 footers, 2 page-number controls,
and 1 page break. Both generated and committed fixture SHA-256 values are
`0DF499E408264302941A631573457475FD0B616D03014ABBDD624B09A38B9302`.

An independent Python `zipfile`/`ElementTree` inspection rebuilt the fixture
and a valid top-level `section_break` request. It asserted CRC, no duplicate
entries, stored first `mimetype`, all required parts, XML parsing/namespaces,
OPF manifest IDs/hrefs/media types, spine, RDF links, and section controls.
**PASS:** the fixture has package-root manifest paths and spine
`header, section0, section1`; RDF links header and both sections with local
Hancom namespace declarations; both section roots have one semantic
`hp:header`/`hp:footer` with `hp:subList`, one native `hp:pageNum`, and a full
section definition. Section 0 has `pageBreak="1"`; section 1 represents start
page 3 with `hp:startNum page="2"`; no literal page-number text was found.
The explicit `section_break` request also built as 2 sections with 2 headers,
2 footers, 2 native page numbers, and 1 page break.

## Former malformed-control repros

The following independently supplied malformed specs all returned CLI exit code
2, produced a clear `INVALID_DOCUMENT_SPEC` error, and left no output file:

- page number with an unknown key;
- page number with both `side_char` and `sideChar`;
- header with a valid `text` plus unsupported `image`;
- footer with a valid `text` plus unsupported table key;
- page break with `runs` content or page-number metadata;
- section break with `text` content or an unknown key.

This confirms the prior fail-open parser finding is corrected. The rework's own
parser-plus-CLI regression test also passes in the 30-test suite.

## Standalone-path audit

Reviewed the candidate diff and searched `scripts/hwpkit/` plus
`scripts/hwpx_tool.py` for COM/Hancom/LibreOffice/renderer/network/process
invocations. The public build path is local Python JSON/ZIP/XML generation and
validation; it contains no matching external-office, external-renderer,
network, or subprocess invocation. No Hancom, COM, LibreOffice, external
renderer, or network service was used during this verification.

## Gate assessment

| Gate | Result | Evidence |
|---|---|---|
| Valid public spec; invalid input rejects atomically | PASS | Former malformed page-number/header/footer/page-break/section-break cases return 2 and leave no output. |
| Fixture build and full validator | PASS | CLI build and full `validate` passed. |
| Expected semantic inspection counts | PASS | Inspector: 2 sections, 2 headers, 2 footers, 2 page numbers, 1 page break. |
| CRC, parts, manifests, namespaces, IDs, references | PASS | Package checker, full validator, and independent ZIP/XML assertions passed. |
| Positive and negative regression protection | PASS | Semantic P02 and malformed-control regression tests pass; full suite is 30/30. |
| Standalone path: no Office/COM/LibreOffice/external renderer/network | PASS | Source audit and all invoked paths are local-only. |
| Full repository suite | PASS | `unittest discover -s tests`: 30 passing tests. |
| P02 multi-section fixture, editable page-number inspection, package validation | PASS | Independently rebuilt/inspected and structurally verified. |

## Verdict and limits

**PASS.** Candidate `96de7e99cbcccab3900407a1fe483a80e94487ad` satisfies all
P02 and workflow acceptance gates. It is eligible for coordinator integration
and checklist update.

This is standalone structural verification, not a visual or renderer
compatibility claim. No Hancom/COM/LibreOffice/external renderer was invoked;
existing-document round-trip editing and standalone pagination/rendering remain
outside P02's scope.
