# ADR-0003: One public CLI

## Decision

All new authoring workflows use `scripts/hwpx_tool.py`. Legacy helpers remain internal diagnostics.

## Reason

A single interface reduces tool selection, prompt size, inconsistent defaults, and validation omissions.
