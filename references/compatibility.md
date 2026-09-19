# Compatibility

## Formats

- Standalone output: HWPX
- Legacy binary HWP: no standalone writer
- HWP conversion: optional compatibility workflow only when an external trusted renderer is available

## Validation levels

1. ZIP entry safety, order, CRC, and uncompressed `mimetype`
2. Complete Hancom package core (`version.xml`, `settings.xml`, ODF manifest, RDF container, content package, header, sections, and preview)
3. Hancom namespaces, package-root content paths, media types, container/RDF targets, and spine references
4. XML parsing and declared object/style references
5. Object IDs, bookmark uniqueness, and balanced fields
6. Native-compatible RDF byte serialization and complete first-section `secPr` children
7. Template fixture build, black-default style checks, and semantic object-count checks

These checks prevent common corruption errors but cannot prove pixel-identical rendering in every Hancom Office version.

## Hancom package compatibility

Hangul applies stricter rules than a general XML or RDF parser. The RDF package namespace must be declared locally on each `hasPart` element rather than on the `rdf:RDF` root. The first section must also carry the full section-definition group: grid, start numbering, visibility, line-number shape, page properties, footnote and endnote properties, and page-border settings. A document with only `pagePr` and `colPr` can pass XML parsing while Hangul still reports a read or save error.

## Fonts and pagination

The writer uses Hamchorom Batang for serif body text and Hamchorom Dotum for sans-serif display text. Font substitution can change line breaks and page counts. Static page-number TOCs remain disabled until a template has a renderer-backed pagination fixture.

## Equations

Equations are editable HWP equation objects. Width, height, and baseline are estimated from normalized structure. Complex matrices, cases, or version-specific commands should receive renderer-backed visual review when available.
