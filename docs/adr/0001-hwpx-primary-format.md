# ADR-0001: HWPX is the primary standalone format

## Decision

Generate HWPX directly. Treat legacy binary HWP as an external compatibility target rather than a guaranteed standalone output.

## Reason

HWPX is an inspectable ZIP/XML package that permits deterministic generation, validation, and repair without Hancom Office.
