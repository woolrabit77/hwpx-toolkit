# ADR-0002: Unverified features fail closed

## Decision

A feature without a conformance fixture is rejected before output generation. The writer does not create visual imitations and report them as native features.

## Reason

Silent approximation is a primary cause of corrupted, misleading, or non-editable office documents.
