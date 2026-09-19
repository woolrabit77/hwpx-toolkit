# P01 independent Terra verification — rework cycle 1

**Result: PASS**

Candidate verified: `58c36cbe428d52d2dc6e2f0144444f2c01f5279a`.
P01 semantic generation is from `95e8656`; the rework that this verification
tested is `e3ef3101505eca4aadafba41dc2c01ca699e2e23`.

## Commands independently run

All commands used the bundled runtime
`C:\Users\woolr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
in the isolated Terra worktree.

| Command | Result |
|---|---|
| `-c "import sys; sys.path.insert(0, 'scripts'); exec(compile(open('work/terra_parser_audit.py', encoding='utf-8').read(), 'work/terra_parser_audit.py', 'exec'))"` | PASS — parser rejected `numbering.level: true` and `tabs[0].position: 1200.5`, each with `JSON integer` error. |
| `-m unittest discover -s tests -v` | PASS — 27 tests, 0 failures (0.930 s), including parser and CLI coercion regressions. |
| `scripts/hwpx_tool.py build tests/fixtures/p01-tabs-lists.json -o work/p01-terra-verified.hwpx` | PASS — 5 blocks; build validation passed. |
| `scripts/hwpx_tool.py validate work/p01-terra-verified.hwpx` | PASS — `valid: true`, no errors. |
| `scripts/hwpx_tool.py inspect work/p01-terra-verified.hwpx` | PASS — 10 entries, 5 paragraphs, 1 numbering, 2 bullets, 2 tab stops, 5 formatted paragraph properties. |
| `scripts/check_hwpx_package.py work/p01-terra-verified.hwpx` | PASS — strict package validation passed. |
| `work/terra_zip_audit.py` | PASS — standard-library ZIP/XML audit passed CRC, stored mimetype, required parts, namespaces, `content.hpf` manifest entries, IDs/references, semantic list objects, real tab, and indent. |
| `scripts/hwpx_tool.py build work/terra-invalid-level.json -o work/must-not-exist-level.hwpx` | PASS negative — exit 2, out-of-range level error, no output. |
| `scripts/hwpx_tool.py build work/terra-invalid-tabs.json -o work/must-not-exist-tabs.hwpx` | PASS negative — exit 2, non-increasing tab-position error, no output. |
| `scripts/hwpx_tool.py build work/terra-invalid-boolean-level.json -o work/must-not-exist-boolean-level.hwpx` | PASS negative — exit 2, `List level must be a JSON integer.`, no output. |
| `scripts/hwpx_tool.py build work/terra-invalid-fractional-tab.json -o work/must-not-exist-fractional-tab.hwpx` | PASS negative — exit 2, tab position must be a JSON integer, no output. |
| `rg -n "win32com|comtypes|LibreOffice|soffice|requests|urllib\\.request|socket|subprocess|http\\.client|renderer" scripts/hwpx_tool.py scripts/hwpkit` | PASS — no matches in the standalone public path. |

## Artifact and semantic evidence

Both independently hashed positive artifacts are SHA-256
`D367E2F5CEE793C0659829CC8179F6AC87C513AC8CFED2518543D4EE725B4D93`:

- `work/p01-terra-verified.hwpx`
- `tests/fixtures/p01-tabs-lists.hwpx`

The audit confirmed all ten package entries, stored
`application/hwp+zip` mimetype, and passing ZIP CRC.  It parsed the expected
version, application, head, section, OPF, OCF, ODF-manifest, and RDF
namespaces.  `Contents/content.hpf` declares `header`, `section0`, and
`settings` with the expected root-relative paths and media types.

The five section paragraphs reference existing dynamic `hh:paraPr` IDs
25–29.  Their heading references are `NONE/0/0`, `BULLET/1/1`,
`BULLET/2/2`, `NUMBER/1/1`, and `NUMBER/1/2`.  The header has two bullet
definitions and one numbering definition with ten `hh:paraHead` levels.  The
first paragraph uses a real `hp:tab`, with 2400 LEFT/NONE and 7200
RIGHT/DOTTED tab properties, plus `left=1200` and `intent=-600` margins.  The
section text contains neither a bullet nor numeric text prefix.  P01 is thus
represented with semantic HWPX list/tab/indent structures.

## Gate verdicts

| Gate | Verdict | Evidence |
|---|---|---|
| Valid Document Spec and fail-closed invalid input | PASS | Valid fixture builds; invalid level, duplicate tabs, boolean level, and fractional tab all reject. |
| Prior malformed inputs via parser and CLI/no output | PASS | Both prior repros reject with exit 2; `Test-Path` returns false. |
| Build, validate, and inspect | PASS | Positive fixture passes and reports expected counts. |
| ZIP CRC, parts, manifests, namespaces, IDs, references | PASS | Strict checker plus independent ZIP/XML audit pass. |
| Semantic lists/tabs/indents rather than text prefixes | PASS | Header/section audit confirms semantic objects and prefix-free text. |
| Regression and full suite | PASS | 27/27 tests pass. |
| Standalone-path prohibited dependencies | PASS | Public path static audit found no COM, Hancom executable, LibreOffice, renderer, network client, or subprocess integration. |

## Limitations

No Hancom, COM, LibreOffice, network service, or external renderer was used.
This is standalone structural verification; it does not substitute for visual
review in a renderer.
