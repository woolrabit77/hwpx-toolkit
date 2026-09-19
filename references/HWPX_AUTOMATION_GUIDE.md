# HWPX automation invariants

## Package rules

- The first ZIP entry is `mimetype`, stored without compression, with exact value `application/hwp+zip`.
- The required package core is `version.xml`, `settings.xml`, `Contents/header.xml`, `Contents/section0.xml`, `Contents/content.hpf`, `META-INF/container.xml`, `META-INF/manifest.xml`, `META-INF/container.rdf`, and `Preview/PrvText.txt`.
- `Contents/content.hpf` uses the exact OPF namespace `http://www.idpf.org/2007/opf/` and package-root paths: `Contents/header.xml`, `Contents/section0.xml`, and `settings.xml`, all with `application/xml` media type.
- The content spine declares both `header` and `section0`.
- `META-INF/container.xml` declares the content package, preview text, and RDF roots with the Hancom media types.
- `META-INF/container.rdf` links the header and every section as Hancom package parts.
- Every container, RDF, and content-manifest target exists.
- Every XML and HPF part parses.
- No duplicate ZIP entries, unsafe paths, duplicate object IDs, duplicate bookmarks, or unbalanced fields are allowed.
- Write to a temporary package, validate it, and atomically replace the destination.

## Authoring rules

- Model semantic paragraphs, tables, equations, notes, and references before serialization.
- Use named styles rather than reproducing layout with repeated spaces.
- Use table structure for forms and metadata bands; do not rely on floating shapes for critical information.
- Keep official-letter identity, press-release contacts, form labels, exam numbering, academic metadata, and report hierarchy as editable text.
- Do not embed source-document content, seals, logos, or branding in reusable templates without permission.
- Use black (`#000000`) for every generated character style and equation unless the request explicitly requires another color. Hyperlink fields must inherit a black run style rather than creating Hancom's conventional blue hyperlink style.

## Equations

- Use `hp:equation` plus `hp:script`, never a Unicode or image imitation when editability is required.
- Normalize independent operators and number/identifier boundaries.
- Preserve decimals, commands, function names, groups, and quoted text.
- Calculate the box from structure. Do not ask the caller to guess width or height.
- Keep inline equations in the surrounding paragraph and avoid synthetic blank paragraphs.

## Validation checklist

- Build succeeds and reports `validation: passed`.
- Full validator returns no errors.
- Removing any required Hancom package part or changing a root-relative `content.hpf` path makes validation fail.
- Every generated `hh:charPr` and `hp:equation` text color is `#000000` by default.
- Inspector counts match the request.
- Golden templates build from starter specs without unresolved `{{...}}` placeholders.
- Temporary files are absent after success and deliberate failure.
- Locked features fail before output creation.
