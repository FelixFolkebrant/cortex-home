## Project Overview

Cortex Home is a local-first room interface. A ThinkPad owns coordination and
durable state while an old iMac provides the visible channels and nearby media
hardware.

## Read When Needed

All documents inside `docs/` are local by design.

- Module index and issue prefixes: `docs/README.md`
- Product-wide intent: `docs/general/IDEA.md`
- Current project direction: `docs/general/ROADMAP.md`
- Workflow details: `docs/general/WORKFLOW.md`
- Shared issue template: `docs/general/templates/ISSUE.md`
- Module intent and direction: `docs/<module>/IDEA.md` and
  `docs/<module>/ROADMAP.md`

## Design Philosophy

*These guidelines bias toward caution over speed. For trivial tasks, use
judgment.*

**Self-documenting code**

- Code should be understandable over smart.
- Do not comment unless the reason is not obvious from reading the code.

**Simplicity**

- Build simple over premature optimization. Major optimization suggestions
  belong in review and issue notes.
- No flexibility or configuration unless asked for.
- YAGNI.

> Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes,
> simplify.

**Fail loudly**

- Do not create rollbacks or backups. If something fails, it should fail.

## Measurements

- Limit any sampling or monitoring window to 60 seconds unless the user
  explicitly confirms a longer duration first.

## Documentation

- Choose the module that owns the outcome and use its three-letter prefix.
- Keep one living `<PREFIX>-<n>.md` issue record in the module's `wip/`
  directory. Planning, implementation, useful review findings, and confirmation
  belong in that record.
- Move the same record to the module's `issues/` directory after completion.
- Update the module ROADMAP when current behavior, direction, dependencies, or
  a lasting decision changes.
- Use General only for work that has no meaningful primary module.

## Git Conventions

- **Branch format:** `<name>/<PREFIX>-<n>/<revision>`; for example,
  `felixf/ALA-002/0`.
- **Commit format:**
  ```text
  ALA-002: Summary title

  Previously we <did something>, which <caused bug | "smelled bad" | did not let us do feature>.

  This change <explain how this change fixes the issue>.
  ```
  The subject line is the issue prefix plus a short imperative title. The body
  is mandatory: one sentence on what existed before and why it was a problem,
  one sentence on how this commit resolves it.
- **Coherent commits:** keep changes understandable and avoid unrelated bundles.
  Closely related code, tests, and documentation may stay together.
- **History cleanup:** fixups and squashing are optional. Do not spend work
  manufacturing a perfect commit history.

### Completing Issue Work

1. Ensure the module issue record in `docs/<module>/wip/` contains current **What**,
   **Acceptance Criteria**, **Implementation Walkthrough**, **Problems
   Encountered**, **Confirmation**, and **Notes** sections.
   - The implementation walkthrough must explain the completed work in a useful
     order and include the repository scripts, configuration paths, and exact
     operator commands needed to reconstruct or redeploy it.
   - Problems encountered must record the symptom, diagnosis or root cause,
     resolution, and any remaining caveat. Keep useful failed approaches, but
     omit raw transcripts, credentials, and host-specific identifiers.
   - Confirmation must separate automated checks from manual testing.
   - Manual testing must tell the reviewer how to start the feature, what
     changed from the previous behavior or appearance, which actions to
     perform, and exactly what should be visible or happen after each action.
   - Cover every user-facing acceptance criterion, including relevant loading,
     empty, error, responsive, and keyboard states. Do not use vague
     instructions such as "run the app and inspect it."
   - Use unchecked task boxes for judgments only the user can make so approval
     remains with the reviewer.
2. Update the owning module ROADMAP when the completed work changes current
   behavior, direction, or lasting decisions.
3. Run the repository's relevant checks and ensure the worktree is clean.
4. Fetch and integrate current `main` according to
   `docs/general/WORKFLOW.md`. Resolve conflicts carefully and rerun affected
   checks. Never rebase the default branch.
5. Move the living issue record from the module's `wip/` directory to its
   `issues/` directory after integration.
6. Push the issue branch with upstream tracking. Use a normal push when history
   is unchanged and `--force-with-lease` only when the rebase rewrote a branch
   that already exists remotely. Never use `--force`.
