# Cortex Home Workflow

The documentation exists to make each module understandable, not to produce a
perfect process or commit history. Keep the current behavior, intended behavior,
important decisions, and useful implementation evidence easy to find.

## Module Documents

Each module owns:

- `IDEA.md`: intended experience, boundaries, and lasting constraints.
- `ROADMAP.md`: current behavior, near-term direction, later ideas, dependencies,
  and accepted or open decisions.
- `wip/<PREFIX>-<n>.md`: one living record for active issue work.
- `issues/<PREFIX>-<n>.md`: the same record after completion.

`docs/README.md` lists the modules and prefixes. General owns this workflow, the
shared issue template, overall product intent, and changes that genuinely span
the whole project.

## Choosing An Owner

Choose the module that owns the user-visible or operational outcome. An issue
has one canonical document even when it changes several modules.

- Voice-controlled lighting is Voice work with a Lighting dependency.
- Alarm-triggered lighting is Alarm work with a Lighting dependency.
- Channel navigation or shared overlays are Shell work.
- Deployment and endpoint provisioning are Platform work.
- Use General only when no module is a meaningful primary owner.

Link related module roadmaps instead of duplicating the issue.

## Roadmap Work

Update a module roadmap when current behavior, direction, dependencies, or a
decision changes. The `Next` section may contain enough detail to replace the
old Planpoint layer:

- Goal and why it matters now.
- Acceptance outline.
- Important boundaries and dependencies.
- Decisions that should be accepted before implementation.

Do not turn the roadmap into a full task breakdown. Exact tasks and verification
belong in the issue record when work starts.

## Issue Work

1. Allocate the next number within the owning module by checking its `issues/`
   and `wip/` directories.
2. Copy `docs/general/templates/ISSUE.md` to the module's `wip/` directory.
3. Record the before-and-after outcome, exclusions, important decisions, and
   manual test path before substantial implementation.
4. Use `<name>/<PREFIX>-<n>/<revision>` for the branch when a branch is useful.
5. Keep the same issue document current with useful implementation notes,
   problems, checks, review findings, and confirmation.

Issues may use worktrees when work is concurrent. Every worktree keeps its own
normal checkout; do not share mutable documentation, dependencies, or build
output between worktrees. Deploy and manually test only one integrated branch
at a time against the shared room hardware.

## Decisions And Reviews

Record a decision in the module roadmap when future work should inherit it.
Keep issue-local choices in the issue record. Use the optional issue heatmap to
direct review attention; it does not replace severity or create a separate
planning artifact. No style catalog, pattern catalog, Planpoint, or mandatory
review document is required.

When a review is substantial, add a `Review Findings` section to the living
issue. Otherwise the code, checks, and issue confirmation are enough.

## Commits

Use the module issue prefix in commit subjects:

```text
ALA-002: Add recurring weekday alarms
```

Prefer coherent commits that make review and recovery understandable. Closely
related code, tests, and documentation may be committed together. Fixups and
history cleanup are optional; do not spend work manufacturing perfect history.

## Completion

1. Ensure the issue record explains what changed, important problems and
   decisions, exact reconstruction or deployment commands, and automated and
   manual confirmation. Keep that detail skimmable under the shared template.
2. Update the module roadmap's `Current`, `Next`, and decision sections where
   needed.
3. Run checks relevant to the affected modules and ensure the worktree is clean.
4. Fetch and integrate current `main` without rebasing the default branch.
5. Move the issue record from the module's `wip/` directory to its `issues/`
   directory after integration.
6. Push with a normal push when history is unchanged. Use
   `--force-with-lease` only for an issue branch whose published history was
   deliberately rewritten; never use `--force`.
