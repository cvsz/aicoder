---
name: add-audit-documentation
description: Workflow command scaffold for add-audit-documentation in aicoder.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-audit-documentation

Use this workflow when working on **add-audit-documentation** in `aicoder`.

## Goal

Adds a new audit or assessment documentation file to the project, typically under docs/implementation/, to record various aspects of repository status, boundaries, coverage, or plans.

## Common Files

- `docs/implementation/repository-assessment.md`
- `docs/implementation/dependency-map.md`
- `docs/implementation/feature-matrix.md`
- `docs/implementation/api-gap-analysis.md`
- `docs/implementation/security-audit.md`
- `docs/implementation/test-coverage-map.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create a new markdown file under docs/implementation/ with the relevant audit or assessment content.
- Commit the new file with a docs(audit): message describing the documentation addition.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.