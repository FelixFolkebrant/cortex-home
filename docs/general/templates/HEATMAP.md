# Heatmap

Use a heatmap only to focus review attention where judgment matters. Heat is
not severity: heat describes how much choice a change involves, while severity
describes how important a problem is to fix.

An issue with no meaningful choices may leave its Heatmap section empty.

## Levels

### Crossroad

A hard-to-reverse product, architecture, data, or workflow decision that needs
human acceptance before work proceeds.

Use it for stack, source-of-truth, provider, authentication, ownership, or
destructive-behavior choices that would be expensive to reverse. Do not use it
for local implementation details or choices that can safely wait.

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

An implementation decision with real alternatives that deserves careful
review but does not block work unless it becomes hard to reverse.

Use it for abstractions, error handling, prompts, validation, component
boundaries, or user flows where more than one approach is defensible. Do not
use it for routine work that follows an accepted project decision.

```text
### H1 - <decision>

- Decision:
- Proposed approach:
- Why:
- Alternatives:
- Review focus:
```

### Warm

Ordinary logic that follows an accepted shape but has edge cases worth a quick
look, such as parsing, transformations, UI state, or matching tests.

### Cold

Routine or mechanical work with little design choice, such as wiring an
existing route, copying a required artifact, or updating generated output.

### Stylistic

Naming, organization, presentation, or expression where several choices are
equally valid. Record a lasting stylistic decision in the owning module's
roadmap only when future work should inherit it.

## Placement

- Put broad, lasting Crossroads and Hot decisions in the module roadmap.
- Put issue-local Crossroads, Hot choices, and useful shorthand in the issue.
- Put review findings in the issue Notes when a durable record helps.
- Do not create a separate heatmap, review document, or planning layer.

## Review Usage

When a finding needs both importance and judgment labels, keep them separate:

```text
### 1. <finding title>

- Severity: 1-5
- Heat: Crossroad | Hot | Warm | Cold | Stylistic
- Status: open | resolved
```
