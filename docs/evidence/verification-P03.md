# P03 independent verification (Terra)

## Candidate

- Candidate SHA verified: `37cd767f2cc3e37ca2c0bd47e4cefebc719bc570`
- Candidate lineage inspected: `7e056ca` (feature), `639a693` (incomplete-grid refusal), and `37cd767` (candidate evidence refresh).
- Verification worktree branch: `terra/p03-verification-37cd767`.
- Central checklist was deliberately not edited.

## Commands and results

All commands used the bundled standalone runtime:

```powershell
$py='C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m unittest discover -s tests
```

Passed: `Ran 33 tests in 1.580s`, `OK`.

```powershell
$out=Join-Path $env:TEMP 'p03-terra-semantics-37cd767.hwpx'
& $py scripts\hwpx_tool.py build tests\fixtures\p03-table-semantics.json -o $out
& $py scripts\hwpx_tool.py validate $out
& $py scripts\hwpx_tool.py inspect $out
& $py scripts\check_hwpx_package.py $out
```

All four commands exited `0`. Build validation passed; `validate` returned `valid: true` with no errors; `inspect` reported `tables: 1`, `fields: 1`, `sections: 1`, and `paragraphs: 11`; package checker printed `HWPX package validation passed.`

I also independently opened the ZIP and asserted: `ZipFile.testzip()` passed; `mimetype` was first and stored; all ten core parts were present; `content.hpf` manifest IDs, root-relative paths, and `header`/`section0` spine references were correct; all `borderFillIDRef` values resolved; formula field begin/end IDs paired; RDF retained the required Hancom declaration and local `hasPart` namespaces. The semantic fixture contained nine physical cells (not covered-cell fakes), a native `hp:cellSpan colSpan="2" rowSpan="2"`, `pageBreak="CELL"`, all three native shading brushes (`#EAF2F8`, `#D9EAF7`, `#FFF2CC`), black solid default grid edges, and only black character styles at 10 pt or above.

```powershell
& $py scripts\hwpx_tool.py build p03-terra-split-modes.json -o (Join-Path $env:TEMP 'p03-terra-split-modes-37cd767.hwpx')
& $py scripts\hwpx_tool.py build p03-terra-extended-formulas.json -o (Join-Path $env:TEMP 'p03-terra-extended-formulas-37cd767.hwpx')
```

These temporary verifier inputs were discarded after the run. The split build/validate/inspect checks exited `0`, contained three tables, and XML inspection found exactly `CELL`, `TABLE`, and `NONE`. The formula build/validate/inspect checks exited `0`, contained six formula fields, and verified `SUM`, `AVERAGE`, `PRODUCT`, `MIN`, `MAX`, parentheses/arithmetic, and a formula dependency (computed values included `5`, `2.5`, `6`, `2`, and `45`).

```powershell
& $py scripts\hwpx_tool.py build <invalid-grid.json> -o <temp-output>
& $py scripts\hwpx_tool.py build <invalid-span.json> -o <temp-output>
& $py scripts\hwpx_tool.py build <invalid-shading.json> -o <temp-output>
& $py scripts\hwpx_tool.py build <invalid-formula.json> -o <temp-output>
& $py scripts\hwpx_tool.py build tests\fixtures\p03-table-formula-failure.json -o <temp-output>
```

Each exited `2` and left no output file. The independently supplied invalid inputs respectively produced: incomplete logical grid; row span outside the table; non-hex shading; circular formula; and unsupported `UNKNOWN` function. The errors were explicit and fail-closed.

```powershell
rg -n -i "subprocess|win32com|comtypes|libreoffice|soffice|requests|urllib\.request|http\.client|socket|webbrowser|selenium|playwright" scripts\hwpx_tool.py scripts\hwpkit --glob '*.py'
```

No matches: the public build/validate/inspect path has no COM, Hancom/LibreOffice renderer, subprocess, or network-client import.

The semantic fixture was rebuilt to a second temporary path. Both outputs had this SHA-256:

`DBF82FC290F1BC08D5D2235BB2C0AED628EE70D74CA6F0868A8F3DCA46CA3DE1`

## P03 gate verdict

| Requirement | Result |
|---|---|
| Public Spec spans, shading, safe split modes, and extended formulas | PASS |
| Native spanned-cell grid and native shading XML | PASS |
| Valid CLI build, validate, inspect, package validation | PASS |
| CRC, manifests, RDF, spine, IDs, and references | PASS |
| Invalid grids, spans, shading, and formulas refuse with no output | PASS |
| Black grid defaults and 10 pt minimum / black text styles | PASS |
| Standalone path (no Hancom/COM/LibreOffice/network/external renderer) | PASS |
| Full repository suite | PASS |

**Verdict: PASS — P03 is ready for coordinator integration.**

Known limits remain intentionally bounded: no explicit-coordinate/overlap declarations, gradients, patterns, transparency, cross-table/volatile/string formulas, or external pagination rendering.
