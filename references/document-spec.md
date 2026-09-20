# Document Spec

The public authoring input is UTF-8 JSON.

The default authoring path is untemplated. Before writing the spec, give the user one concise checkpoint describing the intended document structure and get confirmation. Then omit `template` or set it to `null` and include only the metadata and blocks the document needs.

Use a template request only when the user explicitly names a specific template or explicitly asks to use the skill's preset templates. A document type or purpose alone is not permission to select a template.

## Template request (explicit opt-in only)

```json
{
  "template": "official-letter",
  "metadata": {"title": "Meeting notice", "author": "Policy Division"},
  "data": {
    "agency_name": "Sample Agency",
    "recipient": "Department heads",
    "subject": "Meeting notice",
    "body": "The meeting will be held at 10:00."
  }
}
```

Generate a starter request with:

```powershell
python scripts/hwpx_tool.py template official-letter -o request.json
```

Additional `blocks` are appended after the template. Set `replace_template_blocks` to `true` only when the request intentionally replaces the preset structure.

## Sections, headers, footers, and breaks

Use `sections` when a document needs independent page layout or semantic running content. Each section owns its blocks and may define a text-only `header`, text-only `footer`, and an editable `page_number` control. Page numbers are emitted as HWPML `hp:pageNum` controls; they are never rendered as literal digits.

```json
{
  "metadata": {"title": "Two sections", "author": "Author"},
  "sections": [
    {
      "header": "First section",
      "footer": {"text": "Confidential"},
      "page_number": {"position": "BOTTOM_CENTER", "format": "DIGIT", "side_char": "-"},
      "blocks": [{"type": "paragraph", "text": "First page"}, {"type": "page_break"}]
    },
    {
      "header": "Second section",
      "page_number": {"position": "TOP_RIGHT", "start": 3},
      "blocks": [{"type": "paragraph", "text": "Second section starts here"}]
    }
  ]
}
```

`page_break` is a genuine paragraph page break. Multiple `sections` produce `Contents/section0.xml`, `Contents/section1.xml`, and corresponding manifest/spine/RDF entries. For a single block stream, a `section_break` block begins the next section and may carry that section's `header`, `footer`, `page_number`, and `metadata`. Header/footer tables, images, manual page-number text, unsupported page-number positions/formats, and other approximations are rejected.

## Untemplated request

```json
{
  "template": null,
  "metadata": {
    "title": "Document title",
    "author": "Author",
    "layout": {"profile": "standard-a4", "columns": 1}
  },
  "blocks": [
    {"type": "heading", "level": 1, "text": "Overview", "bookmark": "overview"},
    {"type": "paragraph", "style": "body", "text": "Body text"},
    {"type": "equation", "script": "12.5+2x=0"},
    {
      "type": "table",
      "caption": "Table 1. Cost",
      "border_style": "grid",
      "header_rows": 1,
      "column_widths": [2, 1],
      "rows": [["Item", "Amount"], ["A", 100], ["Total", {"formula": "SUM(B2:B2)"}]]
    },
    {"type": "footnote", "text": "Footnote text"},
    {"type": "toc", "levels": [1, 2]}
  ]
}
```

## Blocks

- `paragraph`: `text` or `runs`; optional `style`, `bookmark`, and `index_terms`
- `heading`: `level` from 1 to 9, text, and optional bookmark
- `equation`: editable HWP equation `script`; box size is automatic
- `table`: logical rows with semantic cell spans, optional caption, bookmark, column widths, row heights in millimetres, header-row count, formulas, images, shading, and border style. Omit `border_style` to use visible black `grid` borders. Logical columns are inferred from the span-aware grid; `column_widths` must match that inferred count.

### Table semantics

Cell spans are real HWPML `hp:cellSpan` values. A cell consumes the next available grid slot in its row; a row-spanning cell occupies the same columns in following rows. The canonical form is `{"span": {"rows": 2, "cols": 2}}` (the equivalent `row_span`/`col_span` fields are accepted). Covered cells are omitted from the row rather than faked with text. Overlaps, spans outside the table, and ambiguous span declarations fail with `SpecError`.
Every physical row must still cover the complete inferred logical grid; use an empty cell for an intentionally blank unspanned slot.

```json
{
  "type": "table",
  "header_rows": 1,
  "shading": "#EAF2F8",
  "split": "cell",
  "rows": [
    [{"value": "Merged heading", "span": {"cols": 2}}, "Amount"],
    [{"value": "A", "shading": "#FFF2CC"}, 10, 20],
    ["Total", {"formula": "SUM(B2:C2)"}, ""]
  ]
}
```

`shading` is a six-digit `#RRGGBB` color on a table or cell and is emitted through native HWP border-fill brushes; it is not text or an image. `split` is one of `cell` (default), `table`, or `none`, mapping to HWPML `pageBreak="CELL|TABLE|NONE"`; unknown modes fail closed. `repeat_header` is an explicit boolean and defaults to true when `header_rows` is non-zero.

Formulas are evaluated deterministically before serialization. The safe grammar supports `SUM`, `AVERAGE`, `PRODUCT`, `MIN`, and `MAX`, rectangular ranges, comma-separated arguments, cell references, numeric constants, parentheses, and `+ - * /`. Formula cells may reference earlier formula cells. Unknown functions, malformed ranges, circular references, text cells, empty direct references, and division by zero fail closed.
- `footnote`, `endnote`: non-empty note text
- `toc`: linked entries for selected heading levels; static page numbers are not generated
- `index`: sorted unique terms

### Paragraph layout and lists

Paragraphs may carry semantic tab stops, indentation, and list properties. Positions and margins are HWPUNIT integers; they are not rendered as spaces or literal list prefixes.

```json
{
  "type": "paragraph",
  "tabs": [
    {"position": 3600, "type": "LEFT", "leader": "NONE"},
    {"position": 7200, "type": "RIGHT", "leader": "DOTTED"}
  ],
  "indent": {"left": 1200, "first_line": -600, "right": 300},
  "text": "A paragraph with a real tab and hanging indent."
}
```

Supported tab types are `LEFT`, `CENTER`, `RIGHT`, and `DECIMAL`; leaders are `NONE`, `SOLID`, `DOTTED`, and `DASHED`. Tab positions must be strictly increasing. Indent values may be negative for a hanging first line.

Use `bullet` or `numbering` for editable list paragraphs. List levels are 1–10. Number formats include `DIGIT`, `CIRCLED_DIGIT`, `HANGUL_SYLLABLE`, `LATIN_SMALL`, `LATIN_CAPITAL`, `ROMAN_SMALL`, and `ROMAN_CAPITAL`.

```json
{
  "type": "paragraph",
  "bullet": {"level": 2, "char": "▪"},
  "text": "A genuine bullet paragraph"
}
```

```json
{
  "type": "paragraph",
  "numbering": {"level": 1, "start": 1, "format": "DIGIT"},
  "text": "A genuine numbered paragraph"
}
```

The writer emits HWPML `hh:tabPr`, `hh:paraPr` margin/heading references, `hh:numbering`/`hh:paraHead`, and `hh:bullet` definitions. It never prepends bullet glyphs or number text to paragraph content. Invalid levels, tab order, tab kinds, list kinds, and number formats are rejected with `SpecError`.

## Paragraph styles

The stable preset style names include `document-title`, `subtitle`, `meta`, `heading-1`, `heading-2`, `heading-3`, `body`, `body-small`, `centered`, `right`, `question`, `instruction`, `form-label`, `table-cell`, `table-header`, `abstract-title`, `abstract-body`, `references`, and `source-note`.

Generated styles never fall below 10 pt. The default body is 11 pt; compact table, note, reference, and metadata styles use 10 pt.

## Page-layout profiles

When `metadata.layout` is omitted, documents use `standard-a4`: A4 portrait with Hancom's standard initial margins (top 20 mm, bottom 15 mm, left/right 30 mm, header/footer 15 mm). Use `compact-a4` only when a form requires more usable area. A layout can override a profile value deliberately.

```json
"layout": {"profile": "standard-a4", "left_mm": 25, "right_mm": 25}
```

Available profiles: `standard-a4`, `compact-a4`.

## Images in table cells

Images are embedded through a table cell object. Paths are resolved relative to the request JSON file. PNG and JPEG are supported.

```json
{
  "type": "table",
  "header_rows": 0,
  "column_widths": [4, 1],
  "row_heights_mm": [42],
  "rows": [[
    "Applicant profile",
    {"image": {"path": "portrait.png", "width_mm": 30, "height_mm": 40, "alt": "Applicant portrait"}}
  ]]
}
```

The writer preserves aspect ratio and scales the image down to fit the cell. It registers the binary in both `BinData/` and `Contents/content.hpf`.

## Links and targets

- Bookmark names must be unique.
- Internal links use `#bookmark-name`.
- External links allow only `http`, `https`, and `mailto`.
- Broken targets fail before package generation.
