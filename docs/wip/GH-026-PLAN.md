# GH-026 Plan: Separate Frontend Channels

# What

- Reorganize the browser client around explicit channel directories for Today,
  Music, Camera, AirPlay, and Alarm.
- Keep application-shell, voice-interaction, diagnostics, and genuinely shared
  code outside the channel directories.
- Move each channel's focused logic, styles, and tests with its presentation
  component while preserving current behavior and the explicit channel switch.

## Out Of Scope

- No visual, interaction, API, coordinator, endpoint, or deployment behavior
  changes.
- No router, dynamic channel registry, plugin system, shared component library,
  or new frontend dependency.
- No Python coordinator or iMac provisioning reorganization.

## Deferred

- Reducing the responsibilities of `App.jsx` and `room-state.js` is deferred
  until the file moves make channel ownership explicit; behavioral extraction
  should be planned and reviewed independently.
- Packaging the Python runtime and normalizing deployment payloads remain
  separate issues because they change installation boundaries rather than
  browser source ownership.

## Acceptance Criteria

- [ ] Today, Music, Camera, AirPlay, and Alarm each have a named directory under
  `coordinator/client/src/channels/` containing their owned browser files.
- [ ] The application shell, voice interaction, diagnostics, and shared endpoint
  control have distinct directories outside `channels/`.
- [ ] `App.jsx` retains one explicit channel switch with no dynamic registry or
  routing abstraction.
- [ ] Existing frontend checks, tests, and production build pass without
  changing behavior.
- [ ] The coordinator installer still builds and stages the client from its
  repository-owned package path.

# Tasks

## 1. GH-026: Organize Frontend Files By Channel

- Move channel components, helpers, tests, and channel-specific styles into
  named channel directories.
- Move shell, voice, diagnostics, and shared files into directories that state
  their existing responsibilities.
- Update imports, test discovery, CSS imports, and documentation paths, then run
  the existing frontend and installer checks.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep Channel Composition Explicit

- Decision: Organize source by channel without introducing a runtime registry.
- Proposed approach: Keep the hard-coded switch in the application shell and
  import each channel directly from its named directory.
- Why: Directory ownership should improve navigation without changing the
  accepted fixed-channel architecture or adding indirection.
- Alternatives: A route table, plugin registry, metadata-driven channel loader,
  or leaving all files flat.
- Review focus: Imports remain direct and the resulting directories own only
  channel-specific behavior.

## Stylistic

### S1 - Name Directories After Product Concepts

- Choice: Use `app`, `channels`, `voice`, `diagnostics`, and `shared` rather than
  generic `components`, `utils`, or `lib` directories.
- Alternative: Organize primarily by technical file type.
- When to apply: Place a file with the product concept that owns it; use
  `shared` only when multiple concepts actually consume it.
