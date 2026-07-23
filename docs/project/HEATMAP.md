# Heatmap

Use heatmaps to focus human attention where taste or judgment matters.

Heat is not severity. Heat describes how much judgment or taste is involved in a change. Severity describes how important a problem is to fix.

A large mechanical migration can be Cold. A one-line naming convention can be Stylistic. A small implementation choice can be Hot if there are real alternatives and future work will inherit it.

## Levels

### Crossroad

A hard-to-reverse product, architecture, or workflow decision that needs human acceptance before work proceeds.

Use for:
- Stack choice.
- Storage or source-of-truth choice.
- Third-party provider choice.
- Auth, data ownership, or destructive behavior.
- Decisions that would cause meaningful rewrite cost if wrong.

Do not use for:
- Local implementation details inside one issue.
- Choices that can be reversed cheaply.
- "Nice to decide" questions that can safely wait.

Format:

```text
### C1 - <decision>

- Decision:
- Options:
- Impact if wrong:
- Proposed choice:
- Why:
- Status: open | decided
```

### Hot

An opinionated implementation decision with real alternatives. Hot items deserve careful review, but they do not block planning unless they become hard to reverse.

Use for:
- A new internal abstraction.
- Error handling strategy with trade-offs.
- Prompt or validation shape that future code may copy.
- Splitting or combining modules when both are defensible.
- A UI workflow choice that affects user trust or destructive behavior.

Do not use for:
- Routine code that follows an accepted pattern.
- A decision already settled in `PATTERNS.md` or an accepted Planpoint.
- Pure style choices unless they affect maintainability.

Format:

```text
### H1 - <decision>

- Decision:
- Proposed approach:
- Why:
- Alternatives:
- Review focus:
```

### Warm

Ordinary business logic that follows accepted patterns but still deserves a quick look.

Use for:
- Feature code following an established module shape.
- Basic parsing or transformation where edge cases exist.
- Normal UI state handling.
- Tests that mirror a known testing style.

Do not over-explain Warm items. If the pattern is accepted and the change is straightforward, keep the review light.

### Cold

Routine, mechanical, or obvious work. Cold does not mean unimportant; it means the reviewer should not spend much taste or architecture attention there.

Use for:
- Renames.
- File moves.
- Wiring a route or command that follows an existing pattern.
- Adding a standard dependency config after the stack is accepted.
- Updating snapshots or generated artifacts when expected.

### Stylistic

A choice about naming, organization, presentation, or expression where multiple choices are acceptable.

Use for:
- Component split preferences.
- Naming conventions.
- Ordering of helper functions.
- UI copy tone when not product-critical.

If a Stylistic choice should be reused, record it in `docs/project/STYLE.md`.

## Placement

- Roadmap: Crossroads and broad conceptual Hot items.
- Planpoint: Crossroads required before the slice starts.
- Issue plan: issue-level Hot and notable Stylistic decisions.
- Review: problems ranked by severity and tagged with heat level.
- Final issue record: decisions that should persist after WIP docs are removed.

## Review Usage

Review findings should include both severity and heat:

```text
### 1. <finding title>

- Severity: 4
- Heat: Hot
- Status: open
```

Examples:
- Severity 5, Cold: build is broken because an import path is wrong. The fix is obvious.
- Severity 4, Hot: frontmatter writing can delete user metadata, and there are multiple valid ways to preserve it.
- Severity 2, Stylistic: a helper name is vague but behavior is correct.
- Severity 3, Warm: hash comparison misses line-ending normalization and needs a focused test.

## Cooling The Map

The goal is not to make every decision Cold immediately. The goal is to turn repeated decisions into accepted patterns.

- If a Hot implementation choice repeats, either move it into `PATTERNS.md` or keep treating each instance as Hot until the pattern is accepted.
- If a Stylistic choice repeats, move it into `STYLE.md`.
- If a Warm pattern starts causing bugs, raise the next instance to Hot and review the pattern.
- If a Crossroad was missed and discovered during issue work, stop and update the Planpoint before continuing.
