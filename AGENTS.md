# Parallel verification workflow

For feature work in this repository, use the workflow in
`docs/parallel-verification-workflow.md` and track status in
`docs/feature-verification-checklist.md`.

- Use `luna-hwpx-implementer` for implementation and `terra-hwpx-verifier` for independent checklist and evidence review.
- Give every implementation and verification task a separate Git worktree.
- An implementation claim is not completion. Only an independent Terra verification that records reproducible evidence may change an item to `VERIFIED`.
- Do not merge a feature branch or update the central checklist before its verifier report passes every required check.
- If verification fails, return the exact failure report to the original Luna implementer for rework. Repeat until it passes, or mark it `BLOCKED` after three failed verification cycles with a concrete decision request.
- Keep evidence concise, reproducible, and committed under `docs/evidence/`.
