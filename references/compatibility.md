# Compatibility

## Formats

- Standalone output: HWPX
- Legacy binary HWP: no standalone writer
- HWP conversion: optional compatibility workflow only when an external trusted renderer is available

## Validation levels

1. ZIP entry safety, order, CRC, and uncompressed `mimetype`
2. Required parts, container targets, manifest items, and spine references
3. XML parsing and declared object/style references
4. Object IDs, bookmark uniqueness, and balanced fields
5. Template fixture build and semantic object-count checks

These checks prevent common corruption errors but cannot prove pixel-identical rendering in every Hancom Office version.

## Fonts and pagination

The writer uses Hamchorom Batang for serif body text and Hamchorom Dotum for sans-serif display text. Font substitution can change line breaks and page counts. Static page-number TOCs remain disabled until a template has a renderer-backed pagination fixture.

## Equations

Equations are editable HWP equation objects. Width, height, and baseline are estimated from normalized structure. Complex matrices, cases, or version-specific commands should receive renderer-backed visual review when available.
