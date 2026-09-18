# Architecture context

- **Document Spec**: compact JSON supplied by the agent or user.
- **Template registry**: approved document-family presets and data fields.
- **Document model**: semantic paragraphs, tables, equations, notes, and references.
- **ID registry**: deterministic allocation and validation for objects, fields, bookmarks, and targets.
- **Writer**: emits the minimum HWPX XML package from the semantic model.
- **Conformance Gate**: blocks unsafe or unverified feature generation.
- **Validator**: checks ZIP structure, CRC, XML, manifest, spine, page settings, IDs, and field balance.
- **Atomic pipeline**: validates a temporary package before replacing the final output and always removes the temporary file.

Public entry point: `scripts/hwpx_tool.py`.
