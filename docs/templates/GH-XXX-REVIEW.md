# GH-XXX Review: <Title>

## Template Guidance

Use this document when review is requested. Rank findings by severity, tag each finding with heat, and focus on bugs, risks, regressions, missing tests, and decisions that need human judgment.

Heat definitions live in `../project/HEATMAP.md`.

# Summary

- Overall review result.
- Highest-risk area.

# Findings

## 1. <Finding Title>

- Severity: 5 | 4 | 3 | 2 | 1
- Heat: Crossroad | Hot | Warm | Cold | Stylistic
- Status: open | fixed | deferred | accepted
- Location: `<file>:<line>`

### Problem

What is wrong, why it matters, and what behavior or maintainability risk it creates.

### Fix

The recommended fix and any meaningful alternatives.

### Verification

How to confirm the fix works.

# Severity Scale

| Level | Name | Meaning | Action |
|---|---|---|---|
| 5 | Critical / Blocker | Broken build, severe bug, data loss, or security risk. | Must fix before merge. |
| 4 | Major | Logical flaw, architectural violation, or performance trap. | Must fix before merge. |
| 3 | Moderate | Edge-case risk, missing tests, or hard-to-maintain code. | Should fix unless intentionally deferred. |
| 2 | Minor | Suboptimal approach, duplication, or readability issue. | Optional fix. |
| 1 | Nitpick | Pure style, naming, or formatting. | Informational. |
