---
name: feature-implementation-with-test
description: Workflow command scaffold for feature-implementation-with-test in aicoder.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-implementation-with-test

Use this workflow when working on **feature-implementation-with-test** in `aicoder`.

## Goal

Implements a new feature (e.g., script or tool) and immediately adds test coverage for it.

## Common Files

- `scripts/repository_inventory.py`
- `tests/test_repository_inventory.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Add the new script or feature file (e.g., in scripts/).
- Add a corresponding test file in tests/.
- Commit each with appropriate feat() and test() messages.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.