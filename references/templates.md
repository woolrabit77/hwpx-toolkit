# Approved templates

Use `python scripts/hwpx_tool.py templates` for the machine-readable registry and data fields.

| ID | Use | Layout invariants |
|---|---|---|
| `official-letter` | Public-sector outgoing letter | recipient/subject table, body, attachment line, sender identity, contact footer |
| `press-release` | Government press release | release metadata, contact grid, title/subtitle, lead, hierarchical body |
| `statutory-form` | Statutory or civil application | A4 grid, checkboxes, grouped inputs, signature, completion instructions |
| `job-application` | One-page employment application | A4 table grid, applicant photograph, compact profile, experience, skills, statement, signature |
| `kice-exam` | KICE-style question paper | compact A4, two columns, session/subject header, numbered questions and choices |
| `academic-humanities` | Humanities/social-science article | one column, bilingual title, author metadata, abstract, sections, hanging references |
| `academic-stem` | Technical journal article | two columns, compact abstract, numbered sections, captions, result table, references |
| `policy-report` | Policy or research report | cover metadata, executive summary, linked contents, chapters, recommendations, appendix |

Template JSON files are authoritative. Golden HWPX files are blank, validated fixtures and are not source files for editing. Create filled documents by binding `data` through the CLI.

Do not copy government emblems, seals, publication identifiers, journal branding, exam questions, or copyrighted article text into a template unless the user supplies and authorizes them. Preserve structural conventions, not protected content.
