# HWPX feature completion checklist

## Usage

- The coordinator owns this file. Luna and Terra write per-feature evidence under `docs/evidence/`.
- A checkbox is checked only after Terra reports `PASS` for the exact commit SHA and the coordinator completes integration testing.
- `REWORK` means Luna must revise the feature; `BLOCKED` requires an explicit design or fixture decision.

| Status | Meaning |
|---|---|
| `NOT_STARTED` | No worktree or implementation yet |
| `IMPLEMENTING` | Luna is working |
| `CANDIDATE` | Luna committed a feature and implementation evidence |
| `VERIFYING` | Terra is independently testing the exact commit |
| `REWORK` | Terra found a reproducible failure |
| `VERIFIED` | Terra passed all gates |
| `MERGED` | Coordinator integrated and reran the full suite |
| `BLOCKED` | Three verification cycles failed or a required fixture is unavailable |

## Backlog

| ID | Feature | Acceptance evidence required | Status | Verified commit | Terra report |
|---|---|---|---|---|---|
| P01 | Tabs, indents, bullets, and numbering | Numbering XML, tab/indent fixture, invalid-level rejection | MERGED | 58c36cb | docs/evidence/verification-P01.md @ 6f66459 |
| P02 | Headers, footers, page numbers, page/section breaks | Multi-section fixture, page-number field inspection, package validation | REWORK | — | docs/evidence/verification-P02.md @ 23504b8 |
| P03 | Table merge, split, shading, and extended formulas | Spanned-cell grid fixture, shading fixture, formula success/failure tests | IMPLEMENTING | — | — |
| P04 | Captions, equation numbering, cross-references, TOC page references | Numbered target fixture, update/rebuild test, broken-target rejection | NOT_STARTED | — | — |
| P05 | Footnote/endnote continuation and existing-document round trip | Multi-section note fixture, parse/write equality or explicit safe refusal | NOT_STARTED | — | — |
| P06 | PNG/JPEG image expansion | Floating image, image sizing/cropping fixture, manifest/reference checks | NOT_STARTED | — | — |
| N01 | Shapes and text boxes | Editable HWPX drawing fixture, IDs/references, malformed-object rejection | NOT_STARTED | — | — |
| N02 | Charts | Editable chart parts, data/series fixture, relationship and malformed-chart checks | NOT_STARTED | — | — |
| N03 | Comments and memos | Comment anchor, author/date metadata, round-trip and invalid-anchor tests | NOT_STARTED | — | — |
| N04 | PDF rendering and export | Deterministic PDF fixture, page/image/text assertions, no external renderer | NOT_STARTED | — | — |
| N05 | Binary HWP output | Independent feasibility gate, minimal valid HWP fixture, parser/open-safety evidence | NOT_STARTED | — | — |
| R01 | Whole-skill conformance suite | All templates, all feature fixtures, corruption tests, deterministic export hash | NOT_STARTED | — | — |

## Per-feature completion record

Copy this record into the coordinator's merge note for each verified item.

```text
Feature ID:
Luna candidate commit:
Terra verified commit:
Implementation evidence:
Verification evidence:
Commands independently rerun by Terra:
Artifact SHA-256:
Checklist result: VERIFIED / REWORK / BLOCKED
Known limitation:
```
