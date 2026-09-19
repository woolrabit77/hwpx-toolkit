# Document Spec

The public authoring input is UTF-8 JSON.

## Template request

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

## Untemplated request

```json
{
  "template": null,
  "metadata": {
    "title": "Document title",
    "author": "Author",
    "layout": {"columns": 1, "left_mm": 25, "right_mm": 25}
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
- `table`: rectangular rows, optional caption, bookmark, column widths, row heights in millimetres, header-row count, formulas, images, and border style
- `footnote`, `endnote`: non-empty note text
- `toc`: linked entries for selected heading levels; static page numbers are not generated
- `index`: sorted unique terms

## Paragraph styles

The stable preset style names include `document-title`, `subtitle`, `meta`, `heading-1`, `heading-2`, `heading-3`, `body`, `body-small`, `centered`, `right`, `question`, `instruction`, `form-label`, `table-cell`, `table-header`, `abstract-title`, `abstract-body`, `references`, and `source-note`.

Generated styles never fall below 10 pt. The default body is 11 pt; compact table, note, reference, and metadata styles use 10 pt.

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
