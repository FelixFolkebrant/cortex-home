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
4. Keep `docs/wip/GH-<n>.md` updated with what changed, an implementation
   walkthrough, problems and their resolutions, plan diffs, decisions, and
   verification.

Issue plans contain issue-level Hot decisions. Crossroads belong in the roadmap or Planpoint unless discovered late.

The durable issue record should be sufficient to reconstruct the feature from
the repository without reproducing the original conversation. Include exact
entry-point commands and configuration paths, but exclude credentials, host
identity, raw logs, and long shell transcripts.

## Review Loop

1. Review the branch into `docs/wip/GH-<n>-REVIEW.md`.
2. User accepts the review.
3. Fix each accepted finding with `git commit --fixup=<target-hash>`.
4. User reviews the fixup commits.
5. Update `docs/wip/GH-<n>.md` and check off `docs/wip/GH-<n>-REVIEW.md`.
6. Rebase the branch after accepted fixes.
7. Repeat until accepted.

## Parallel Issue Work

Parallel work uses one Git worktree per active issue, never one shared mutable
checkout and never a permanent worktree per feature.

1. Accept the relevant Planpoints and reserve every `GH-XXX` identifier on
   `main` before creating issue branches.
2. Commit the accepted planning baseline so every local worktree starts from
   the same project, Planpoint, and issue context. Push it before another clone,
   machine, or person starts from it.
3. Create one sibling worktree for each active issue using its required
   `<name>/GH-<n>/<revision>` branch.
4. Keep a complete normal `docs/` checkout in every worktree. Do not symlink or
   otherwise share checked-out documentation, dependencies, build output, or
   indexes between worktrees.
5. Change canonical project and Planpoint decisions through `main` or one
   designated planning issue first. Active issue branches update only their own
   WIP documents unless their accepted plan explicitly changes shared docs.
6. After a shared decision or issue merges, fetch and rebase each remaining
   branch before continuing work that depends on it.
7. Code and automated tests may run concurrently. Deploy and manually test only
   one integrated branch at a time against the shared ThinkPad, iMac, Hue
   bridge, microphone, and Sonos.
8. Remove an issue worktree after its branch merges. A later issue receives a
   new worktree from the updated `main`.

For the first parallel pair:

```sh
git worktree add ../cortex-home-GH-012 -b felixf/GH-012/0 main
git worktree add ../cortex-home-GH-013 -b felixf/GH-013/0 main
```

GH-012 owns coordinator context code and tests. GH-013 owns frontend module
separation. Their accepted scopes deliberately do not overlap.

The first pair is complete. Remove both merged worktrees after confirming they
are clean.

Reserve and plan the next active set on `main`, then create:

```sh
git worktree add ../cortex-home-GH-014 -b felixf/GH-014/0 main
git worktree add ../cortex-home-GH-015 -b felixf/GH-015/0 main
git worktree add ../cortex-home-GH-017 -b felixf/GH-017/0 main
```

Continue work in the following lanes:

| Wave | Voice lane | Channel lane |
|---|---|---|
| 1 | GH-012 agent-safe room context | GH-013 channel shell separation |
| 2 | GH-014 local speech qualification | GH-015 Music visual polish |
| 3 | GH-016 Pi and OpenRouter answer path | GH-017 local Camera mirror |
| 4 | GH-018 exact scene tool | GH-020 channel transitions and GH-021 Home redesign |

Keep each lane sequential: voice issues build on the prior voice boundary,
while channel issues share the explicit shell switch, room state, and
presentation structure. GH-014 and GH-015 may proceed independently. GH-017
may begin its isolated component and channel-contract work in a third worktree,
but it must fetch and rebase after GH-014 merges before adding endpoint camera
permission or performing physical camera confirmation. This is the one accepted
cross-lane dependency because microphone and camera capture share Chromium's
exact-origin secure-context boundary.

GH-014 owns the shared secure-context origin and audio-capture permission.
GH-015 owns `MusicChannel.jsx`, Music-specific styles, and its focused
presentation tests. GH-017 owns the new Camera component, the explicit channel
switch, Camera shortcut and coordinator validation, and—after rebasing
GH-014—the video-capture permission in the shared Chromium policy. Neither
channel issue changes agent interaction presentation.

Creating all three worktrees does not authorize simultaneous deployment.
Deploy and manually test only one integrated branch at a time. Remove each
worktree after its issue branch merges, and rebase any branch that depends on
the merged result before continuing shared integration.

After the first three waves merge, reserve and plan the next active set on
`main`, then create:

```sh
git worktree add ../cortex-home-GH-018 -b felixf/GH-018/0 main
git worktree add ../cortex-home-GH-020 -b felixf/GH-020/0 main
git worktree add ../cortex-home-GH-021 -b felixf/GH-021/0 main
```

GH-018 owns the agent child protocol, the coordinator's agent-to-scene
execution seam, and focused voice-action lifecycle tests. GH-020 owns the
observed channel transition boundary in `App.jsx`, its transition styles, and
focused transition tests. GH-021 owns `TodayChannel.jsx` and its focused
presentation tests. GH-020 must not redesign channel content, and GH-021 must
not change the application shell or shared feedback. If either presentation
issue needs the same stylesheet lines, keep the addition issue-specific and
rebase the later merge rather than broadening ownership.

All three may begin from the same planning baseline. Code and automated tests
may proceed independently, but integrated deployment and physical-room review
remain serialized.

## Finish

1. Push the branch and create the PR.
2. Run CI and manual review if requested.
3. After approval and merge, remove WIP docs.
4. Move the final issue record to `docs/issues/GH-<n>.md`.
