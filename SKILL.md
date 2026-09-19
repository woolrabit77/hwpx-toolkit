---
name: hwp-hwpx-document-automation
description: Create, edit, inspect, template, and validate Korean HWPX documents without Hancom Office, COM, internet access, or other skills. Use for HWPX, Korean word-processing documents, official letters, press releases, statutory forms, KICE-style exams, academic articles, policy reports, tables, equations, notes, captions, bookmarks, links, cross-references, TOCs, or indexes. Legacy binary HWP output is outside the standalone core.
---

# Standalone HWPX Document Automation

This skill creates and validates `.hwpx` files without Hancom Office, COM, LibreOffice, internet access, or another skill. HWPX is the default output. Do not claim standalone support for the legacy binary `.hwp` format.

## Single interface

Use `scripts/hwpx_tool.py` for every new workflow.

```powershell
python scripts/hwpx_tool.py templates
python scripts/hwpx_tool.py template official-letter -o request.json
python scripts/hwpx_tool.py build request.json -o result.hwpx
python scripts/hwpx_tool.py validate result.hwpx
python scripts/hwpx_tool.py inspect result.hwpx
python scripts/hwpx_tool.py features
python scripts/hwpx_tool.py equation "x^2+3x+2=0"
```

Do not hand-author HWPX XML. Write a small JSON Document Spec and pass it to the tool. The internal modules own packaging, object IDs, references, styles, equation sizing, manifests, validation, and atomic output replacement.

## Workflow

1. Select an approved template when its document family matches the request.
2. Express content as template `data` and optional additional `blocks`.
3. Run `build`; full validation runs automatically.
4. If validation fails, the output is deleted. Fix the reported JSON or content issue and rebuild.
5. Use `inspect` when object counts, bookmarks, fields, tables, or equations matter.

Read [references/document-spec.md](references/document-spec.md) for JSON syntax. Read [references/templates.md](references/templates.md) for template selection and fields. Read [references/feature-status.md](references/feature-status.md) for support boundaries.

## Approved templates

- `official-letter`: Korean public-sector outgoing letter
- `press-release`: government press release
- `statutory-form`: table-driven statutory or civil application form
- `job-application`: one-page, table-driven employment application with an embedded applicant image
- `kice-exam`: two-column KICE-style examination paper
- `academic-humanities`: single-column humanities or social-science article
- `academic-stem`: compact two-column STEM article
- `policy-report`: policy or research report

The source definitions are in `assets/templates/specs/`. Blank validated HWPX files are in `assets/templates/golden/`. Starter requests are in `assets/templates/examples/`.

## Accuracy rules

- The same input must produce the same semantic structure.
- Generate the complete Hancom package core: `version.xml`, `settings.xml`, `Contents/content.hpf`, `META-INF/container.xml`, `META-INF/manifest.xml`, and `META-INF/container.rdf` in addition to the header, sections, preview, and `mimetype`.
- In `Contents/content.hpf`, use package-root paths such as `Contents/header.xml`, `Contents/section0.xml`, and `settings.xml`; never use legacy `header.xml` or `section0.xml` relative paths.
- Serialize `META-INF/container.rdf` in the native Hancom-compatible byte form: keep only the RDF namespace on `rdf:RDF`, declare the package namespace locally on each `hasPart`, and retain the UTF-8 standalone declaration. Semantically equivalent pretty-printed RDF is not sufficient.
- Emit a complete first-section definition. `secPr` must include grid, start numbering, visibility, line-number shape, page properties, footnote properties, endnote properties, and page-border settings before the column definition.
- Write to an atomic temporary ZIP, verify entry order, `mimetype`, CRC, XML namespaces, required parts, container/RDF targets, manifest paths and media types, spine, IDs, bookmarks, fields, and references, then replace the output.
- All generated character styles and editable equations use `#000000` as the default text color. Do not introduce colored hyperlink character styles unless the user explicitly requests colored text.
- All generated character styles are at least 10 pt. Use 11 pt for ordinary body text and 10 pt only for compact metadata, tables, notes, captions, references, and similar secondary text. Never shrink text to force pagination; adjust spacing, row height, margins, or content density instead.
- Embed PNG or JPEG images through the Document Spec table-cell image object. Register every image in `BinData/` and `Contents/content.hpf`, preserve its aspect ratio, and scale it down to the available cell box.
- Do not silently approximate an unsupported feature with lookalike text or images.
- A feature locked by the Conformance Gate must fail explicitly.
- Do not overwrite an input document. Use a new output path.
- Keep required official-document labels, test numbering, academic metadata, captions, and reference structure as document elements rather than free-floating decoration.

## Equations

- Create editable equations as `hp:equation` objects.
- The lexer inserts spacing around independent operators and number/identifier boundaries while preserving decimals, function names, commands, quoted text, and groups.
- The layout module estimates width, height, and baseline from the normalized expression; callers do not manually size equation boxes.
- Use `equation` before building when an expression is complex.

## Optional features

Features 21, 26, 29, 30, 31, 32, 33, 35, and 40 are governed by one status registry.

- `beta`: basic generation and self-validation are available.
- `experimental`: structural generation is available, but compatibility coverage is limited.
- `locked`: generation is blocked until a safe conformance fixture exists.

Charts, tracked-change generation, encryption, distribution documents, and digital signatures must not bypass a `locked` state.

## Temporary files

The build pipeline keeps only the atomic temporary package beside the final output and deletes it on success or failure. Use `cleanup_hwp_job.py` only for legacy analysis jobs that require a separate working directory.

## Existing documents

New-document generation is the reliable standalone path. Lossless editing of an existing complex HWPX is allowed only for features with parser/writer round-trip fixtures. Legacy utilities remain diagnostic or compatibility helpers; they are not the public authoring interface.

## Export

Run the deterministic exporter from the skill root:

```powershell
python scripts/export_skill.py -o hwp-hwpx-document-automation.zip
```

The exporter excludes caches, temporary files, and nested export archives, then verifies the ZIP before returning its SHA-256 digest.

## References

- [references/document-spec.md](references/document-spec.md): JSON blocks and examples
- [references/templates.md](references/templates.md): approved templates and data fields
- [references/feature-status.md](references/feature-status.md): feature states and unlock conditions
- [references/compatibility.md](references/compatibility.md): format, font, pagination, and renderer limitations
- [references/HWP_FEATURE_COVERAGE.md](references/HWP_FEATURE_COVERAGE.md): prioritized feature coverage
- [references/HWPX_AUTOMATION_GUIDE.md](references/HWPX_AUTOMATION_GUIDE.md): package and authoring invariants
