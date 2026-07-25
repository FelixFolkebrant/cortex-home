# GH-XXX: <Title>

## Template Guidance

This is the durable issue record. Keep it current during issue work in `docs/wip/`, then move it to `docs/issues/` after merge. It should summarize what changed, what the reviewer must confirm, and which decisions should survive after WIP docs are deleted.

# What

- What was implemented.

# Acceptance Criteria

- [ ] Criterion from the accepted plan, updated if scope changed.

# Plan Diff

- Any meaningful difference from `GH-XXX-PLAN.md`.
- Write `None` if the implementation followed the plan.

# Implementation Walkthrough

- Explain what was done in the order needed to understand or reconstruct it.
- Name the repository-owned scripts and configuration paths.
- Include exact setup, deployment, migration, or recovery commands when useful.
- Prefer stable entry points over copied shell transcripts. Exclude credentials,
  host identity, and generated or temporary values.

# Problems Encountered

## 1. <Problem>

- Symptom:
- Diagnosis:
- Resolution:
- Remaining caveat:

# Confirmation

## Automated Checks

- Command:
- Result:

## Manual Testing

- Start the feature:
- Action:
- Expected result:

# Heatmap

Reference: `../project/HEATMAP.md`.

Record only decisions that should persist after WIP docs are removed.

## Hot

### H1 - <Decision>

- Decision:
- Where:
- Why:
- Alternatives:

## Warm

- Where:
- What:

## Cold

| Where | What |
|---|---|
| `<file>:<line>` | Routine change following an accepted pattern. |

## Stylistic

### S1 - <Choice>

- Choice:
- Alternative:
- When to apply:

# Notes

- Anything the reviewer or future maintainer should know.
