# HWPX automation invariants

## Package rules

- The first ZIP entry is `mimetype`, stored without compression, with exact value `application/hwp+zip`.
- Every container and manifest target exists.
- Every XML and HPF part parses.
- No duplicate ZIP entries, unsafe paths, duplicate object IDs, duplicate bookmarks, or unbalanced fields are allowed.
- Write to a temporary package, validate it, and atomically replace the destination.

## Authoring rules

- Model semantic paragraphs, tables, equations, notes, and references before serialization.
- Use named styles rather than reproducing layout with repeated spaces.
- Use table structure for forms and metadata bands; do not rely on floating shapes for critical information.
- Keep official-letter identity, press-release contacts, form labels, exam numbering, academic metadata, and report hierarchy as editable text.
- Do not embed source-document content, seals, logos, or branding in reusable templates without permission.

## Equations

- Use `hp:equation` plus `hp:script`, never a Unicode or image imitation when editability is required.
- Normalize independent operators and number/identifier boundaries.
- Preserve decimals, commands, function names, groups, and quoted text.
- Calculate the box from structure. Do not ask the caller to guess width or height.
- Keep inline equations in the surrounding paragraph and avoid synthetic blank paragraphs.

## Validation checklist

- Build succeeds and reports `validation: passed`.
- Full validator returns no errors.
- Inspector counts match the request.
- Golden templates build from starter specs without unresolved `{{...}}` placeholders.
- Temporary files are absent after success and deliberate failure.
- Locked features fail before output creation.
