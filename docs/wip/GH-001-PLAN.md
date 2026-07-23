# GH-001 Plan: Bootstrap The Cortex Home Repository

## Template Guidance

Use this document to agree on issue scope before code starts. Keep prose short.
Put durable heatmap definitions in `../project/HEATMAP.md`; this file should only
list the issue-specific decisions.

# What

- Initialize this folder as the single Cortex Home Git repository.
- Preserve the accepted idea, roadmap, and Planpoint as the planning baseline.
- Replace the copied Crossroads README with a Cortex Home project entry point.
- Replace the copied Crossroads `GH-001` record with the Cortex Home issue
  record.

## Out Of Scope

- Pushing project history or opening a pull request.
- Installing Ubuntu or changing the iMac.
- Application, endpoint, deployment, or CI scaffolding.
- Creating child repositories or submodules.

## Deferred

- Hardware work moves to GH-002 because it requires the physical iMac and should
  not be mixed with repository initialization.
- Publishing waits until the local repository identity and first issue history
  exist.
- Ignore rules wait until real generated or secret files exist.

## Acceptance Criteria

- [ ] This folder is a Git repository with `main` as its default branch.
- [ ] Accepted project planning is captured as the initial baseline.
- [ ] Issue work occurs on a correctly named `GH-001` branch.
- [ ] `README.md` introduces Cortex Home and links to the idea, roadmap, and
  current Planpoint.
- [ ] The copied Crossroads `docs/wip/GH-001.md` content is replaced with the
  current Cortex Home issue record.
- [ ] The folder and empty GitHub repository use the `cortex-home` slug.
- [ ] No application stack, remote host, CI system, child repository, or
  speculative ignore rules are introduced.

# Tasks

## 1. Record The Accepted Planning Baseline

- Initialize the Git repository on `main`.
- Commit the accepted planning and workflow documents before issue
  implementation begins.

## 2. Bootstrap The Cortex Home Project Entry Point

- Check out the correctly named issue branch.
- Replace the generic README and stale copied issue record with Cortex
  Home-specific content.
- Rename the existing empty GitHub repository and local remote from `abode` to
  `cortex-home`.
- Keep this as one atomic commit because both changes remove copied Crossroads
  project identity from the new repository.

# Heatmap

Reference: `../project/HEATMAP.md`.

Only include Hot and major Stylistic choices that need attention before
implementation.

## Hot

None. Repository initialization follows the accepted Planpoint.

## Stylistic

### S1 - Keep The README As An Entry Point

- Choice: Introduce Cortex Home briefly, then link to the accepted Crossroads
  documents.
- Alternative: Duplicate the idea and roadmap in the README.
- When to apply: Keep durable project detail in its canonical document rather
  than maintaining it in two places.
