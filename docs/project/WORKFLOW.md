# Crossroads Workflow

This file is the operational version of `docs/CROSSROADS_MANIFESTO.md`. The manifesto is the highest-level source of truth when changing the workflow itself.

## File Roles

- `docs/project/IDEA.md`: product intent, user flows, and constraints.
- `docs/project/ROADMAP.md`: current direction and upcoming Planpoints.
- `docs/planpoints/PP-<n>.md`: accepted vertical slice plan.
- `docs/wip/GH-<n>-PLAN.md`: accepted issue plan before code.
- `docs/wip/GH-<n>-REVIEW.md`: review findings and fix status.
- `docs/wip/GH-<n>.md`: final issue record before merge.
- `docs/issues/GH-<n>.md`: final issue record after merge.
- `docs/project/HEATMAP.md`: canonical heatmap definitions.
- `docs/project/PATTERNS.md`: accepted reusable implementation patterns.
- `docs/project/STYLE.md`: accepted stylistic choices.

## Planning

1. Create or update `docs/project/IDEA.md`.
2. Create or update `docs/project/ROADMAP.md`.
3. Wait for roadmap acceptance.
4. Create `docs/planpoints/PP-<n>.md`.
5. Wait for Planpoint acceptance.

Roadmaps set direction. Planpoints decide only the hard-to-reverse choices needed before issue work starts.

## Issue Work

1. Create `docs/wip/GH-<n>-PLAN.md` from the template.
2. Check out `<name>/GH-<n>/<revision>`.
3. Implement the accepted plan with atomic commits.
4. Keep `docs/wip/GH-<n>.md` updated with what changed, plan diffs, decisions, and verification.

Issue plans contain issue-level Hot decisions. Crossroads belong in the roadmap or Planpoint unless discovered late.

## Review Loop

1. Review the branch into `docs/wip/GH-<n>-REVIEW.md`.
2. User accepts the review.
3. Fix each accepted finding with `git commit --fixup=<target-hash>`.
4. User reviews the fixup commits.
5. Update `docs/wip/GH-<n>.md` and check off `docs/wip/GH-<n>-REVIEW.md`.
6. Rebase the branch after accepted fixes.
7. Repeat until accepted.

## Finish

1. Push the branch and create the PR.
2. Run CI and manual review if requested.
3. After approval and merge, remove WIP docs.
4. Move the final issue record to `docs/issues/GH-<n>.md`.
