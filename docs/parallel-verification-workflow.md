# Parallel implementation and verification workflow

## Roles

| Role | Custom agent | Model | Authority |
|---|---|---|---|
| Coordinator | Main Codex thread | Chosen for the task | Splits work, creates worktrees, integrates verified changes, updates the central checklist |
| Implementer | `luna-hwpx-implementer` | GPT-5.6 Luna, high | Implements one bounded feature and records candidate evidence |
| Verifier | `terra-hwpx-verifier` | GPT-5.6 Terra, high | Independently reruns acceptance checks and issues PASS or REWORK |

## State machine

```text
NOT_STARTED -> IMPLEMENTING -> CANDIDATE -> VERIFYING -> VERIFIED -> MERGED
                                      ^          |            |
                                      |          v            v
                                      +------- REWORK      BLOCKED
```

`VERIFIED` means every required acceptance check passed at one immutable commit SHA. `MERGED` means the coordinator integrated that verified SHA and reran the full repository suite. Do not treat a Luna implementation report as verification.

## Worktree protocol

1. The coordinator creates one implementation worktree and one verification worktree from the same base commit.
2. Luna changes only the implementation worktree and commits the feature.
3. Terra checks out Luna's exact commit in its own verification worktree, then reruns every acceptance command independently.
4. Terra writes a PASS or REWORK report under `docs/evidence/` and commits only that report if the evidence must be retained.
5. On PASS, the coordinator cherry-picks or merges Luna's feature commit, then updates the central checklist with the verified SHA and report path.
6. On REWORK, the coordinator sends Terra's report back to the same Luna agent. Luna must fix the failure in a new commit; Terra verifies the new SHA from scratch.
7. After three failed verification cycles, change the item to `BLOCKED` and state the smallest decision or missing conformance fixture required to proceed.

Never let multiple agents edit `docs/feature-verification-checklist.md` concurrently. The coordinator owns that file.

## Required evidence

Every feature must have both reports:

- `docs/evidence/implementation-<feature-id>.md` from Luna
- `docs/evidence/verification-<feature-id>.md` from Terra

Each report must state the commit SHA, changed files, exact commands, concise command results, fixture paths, artifact SHA-256 values, and known limitations. Terra must also state the acceptance result for every checklist item.

## Minimum acceptance gates

1. Public Document Spec accepts valid input and rejects invalid input with a clear error.
2. Generated HWPX passes `python scripts/hwpx_tool.py validate <file>`.
3. `inspect` reports the expected semantic object count.
4. ZIP CRC, required package parts, manifest entries, XML namespaces, IDs, and references are valid.
5. A regression test demonstrates the requested behavior; a negative test protects its main failure mode.
6. The change does not use Hancom Office, COM, LibreOffice, external rendering, or network access in the standalone generation path.
7. The full test suite passes after integration.

Feature-specific gates in the central checklist are additional, not replacements.

## Coordinator prompt template

```text
Use the parallel verification workflow in AGENTS.md.

Create a Luna High implementation agent in a dedicated worktree for feature <ID>.
After it commits, create a Terra High verification agent in a separate worktree,
checked out at Luna's exact commit. Terra must use the assigned checklist gates,
write an evidence report, and return PASS or REWORK.

If Terra returns REWORK, send its exact report to the same Luna agent and repeat.
Do not merge or check off the central checklist until Terra returns PASS.
```
