# HWP/HWPX feature coverage

This is a practical priority list, not measured usage telemetry. Hancom does not publish a definitive global ranking of feature frequency.

| No. | Common feature | Coverage |
|---:|---|---|
| 1 | Create a new document | Supported for validated HWPX |
| 2 | Open, save, save as | HWPX inspection/build supported; binary HWP excluded |
| 3 | Text entry and editing | Supported in generated semantic blocks |
| 4 | Cut, copy, paste | Not an interactive editor operation |
| 5 | Undo and redo | Not supported |
| 6 | Find and replace | Diagnostic helpers only |
| 7 | Character formatting | Preset styles supported |
| 8 | Paragraph formatting | Alignment, margins, spacing, and keep rules supported |
| 9 | Styles | Named preset paragraph/character styles supported |
| 10 | Tabs and indents | Supported through semantic `tabs` and `indent` paragraph properties |
| 11 | Bullets and numbering | Supported through editable HWPML numbering and bullet definitions |
| 12 | Page setup and margins | Supported per template profile |
| 13 | Headers, footers, page numbers | Supported for semantic text controls and editable `hp:pageNum` fields in each section |
| 14 | Page, column, section breaks | Supported for explicit page-break paragraphs and independently packaged multi-section documents |
| 15 | Tables | Supported for rectangular tables |
| 16 | Merge and split cells | Not yet supported by the public spec |
| 17 | Table borders and shading | Borders supported; shading limited |
| 18 | Table formulas | Beta safe subset |
| 19 | Images | PNG/JPEG images embedded in table cells; floating images and image editing are not supported |
| 20 | Shapes and text boxes | Not in the standalone writer |
| 21 | Table calculations | Beta |
| 22 | Hyperlinks | Supported with scheme and target checks |
| 23 | Special characters | Supported as Unicode text where the font covers them |
| 24 | Fields | Internal hyperlink/formula fields supported |
| 25 | Mail merge and labels | Not supported |
| 26 | Charts | Locked |
| 27 | Equations | Supported as editable equation objects with automatic sizing |
| 28 | Equation numbering | Manual text numbering only |
| 29 | Footnotes and endnotes | Experimental |
| 30 | Captions | Experimental table captions |
| 31 | Bookmarks and hyperlinks | Beta |
| 32 | Cross-references | Beta static targets |
| 33 | TOC and index | Beta linked/static form |
| 34 | Comments and memos | Not supported |
| 35 | Track changes and compare | Locked |
| 36 | Spelling and grammar | External language tooling not bundled |
| 37 | Macros and scripts | Not supported |
| 38 | Document information | Title and creator metadata supported |
| 39 | Print, preview, PDF export | HWPX validation only; rendering is environment-dependent |
| 40 | Password, distribution, digital signature | Locked |

The approved template library adds reliable structure for official letters, press releases, statutory forms, KICE-style exams, academic articles, and policy reports without changing these feature boundaries.
