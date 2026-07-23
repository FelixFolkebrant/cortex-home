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
