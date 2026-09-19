# Evidence report format

Create one implementation report and one independent verification report per feature.

```md
# <implementation|verification>-<feature-id>

- Commit SHA:
- Worktree:
- Feature scope:
- Changed files:

## Commands

```text
<exact command>
<concise observed result>
```

## Artifacts

| Artifact | SHA-256 | Inspection result |
|---|---|---|
| `path/to/file.hwpx` | `<hash>` | `validate: passed; tables: 1` |

## Acceptance gates

- [ ] Input validation
- [ ] Positive behavior
- [ ] Negative behavior
- [ ] Package validation
- [ ] Full test suite

## Verdict

`CANDIDATE` for implementation reports, or `PASS` / `REWORK` for Terra reports.

## Known limitations or rework instructions

<concise, reproducible statement>
```
