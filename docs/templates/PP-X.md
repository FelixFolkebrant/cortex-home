# PP-X: <Planpoint Title>

## Template Guidance

A Planpoint sits above issues. It describes one vertical slice of the product, decides the hard-to-reverse choices that must happen before issue work starts, and defers everything else.

Use `PP` when naming the file. Use `Planpoint` when referring to the concept.

# Slice

One sentence: what capability exists after this slice that did not exist before.

- What is delivered end to end.
- Why this is the right next slice.

## Out Of Scope

- Scope explicitly outside this slice.

## Deferred To Later Planpoints

- Bigger scope pushed forward on purpose, with one line explaining why deferring is safe.

# Crossroads

Crossroads are decisions that need human input because getting them wrong would be expensive to reverse. Everything cheaper belongs in a later issue or in the issue-level heatmap.

## C1 - <Decision>

- Decision:
- Options:
- Impact if wrong:
- Proposed choice:
- Why:
- Status: open | decided

# Plumbing

- Threaded now: the one hello-world type or shape carried across the full stack for this slice.
- Pattern set: the convention later types will follow, so widening is cheap and Cold.

# Issues

Loose breakdown into `GH-XXX` issues, in build order. Detail belongs in each issue's `GH-XXX-PLAN.md`.

1. **GH-XXX - <Title>**: one line.
2. **GH-XXX - <Title>**: one line.

# Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

At Planpoint level, include only Crossroads and conceptual Hot choices. Granular Hot, Warm, Cold, and Stylistic choices belong in issue-level docs.

## Crossroads

- C1: <decision>; see Crossroads section.

## Hot

### H1 - <Decision>

- Decision:
- Why:
- Alternatives:
