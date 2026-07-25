# GH-006 Plan: Publish Spotify Playback State

## What

- Capture local librespot playback events on the iMac and normalize them into
  one provider-independent `music.playback` snapshot.
- Let the ThinkPad coordinator own the latest snapshot in memory and publish it
  through the existing event stream.
- Prove live track, pause, resume, seek, stop, unavailability, and recovery
  behavior without adding Spotify control or display work.

## Out Of Scope

- The Music channel UI, artwork presentation, or progress animation.
- Starting, pausing, seeking, skipping, or changing volume from Cortex Home.
- Spotify Web API access, OAuth, polling, browsing, search, queues, or lyrics.
- Durable playback history, analytics, a database, or a general media model.
- Downloading, proxying, or caching Spotify artwork.

## Deferred

- GH-007 will render the accepted snapshot after its live path is qualified.
- A reusable adapter framework remains deferred until another observed service
  proves which behavior repeats.
- Authentication beyond the existing home-LAN boundary remains deferred until
  a control or private-data flow makes it necessary; this issue accepts only
  bounded playback observations and exposes no new action.

## Acceptance Criteria

- [ ] Raspotify invokes a repository-owned event adapter through `--onevent`
  without affecting audio when reporting fails.
- [ ] The adapter maps only the required librespot environment fields into a
  normalized snapshot; account, client, host, and raw provider event data are
  neither forwarded nor logged.
- [ ] A `music.playback` snapshot contains `status`, `item`, `positionMs`, and
  `observedAt`; status is `unavailable`, `stopped`, `paused`, or `playing`, and
  `item` is `null` when nothing is loaded.
- [ ] `positionMs` is a bounded non-negative integer and `observedAt` is a UTC
  timestamp assigned by the coordinator after accepting the observation.
- [ ] Loaded tracks and episodes include a Spotify URI, item type, title,
  creators, collection, artwork URL, and duration without requiring Spotify
  Web API credentials.
- [ ] The coordinator validates exact fields and bounded values, retains only
  the latest snapshot in memory, and immediately sends it to each newly
  connected endpoint.
- [ ] Playing, paused, stopped, and unavailable states cannot leave a stale
  `playing` snapshot after a terminal event or tested service failure.
- [ ] Play, pause, resume, seek, track change, and unavailable events produce
  correct snapshots on the real receiver.
- [ ] Restarting the coordinator or Raspotify recovers reporting after the next
  receiver event without local login or manual state repair.
- [ ] Existing `endpoint.identify` behavior and tests continue to pass.
- [ ] Automated tests cover normalization, validation, state replacement,
  initial publication, malformed input, reporting failure, and recovery.
- [ ] Repository Python, shell, frontend, systemd, build, and whitespace checks
  pass where affected.
- [ ] The issue record contains exact automated and reviewer-owned manual
  confirmation steps.

## Tasks

### 1. Capture Normalized Receiver State

- Add the smallest standard-library adapter that translates supported
  librespot event variables into the accepted snapshot.
- Configure the existing Raspotify service to invoke it without giving the
  adapter privileges or durable provider credentials.

### 2. Own And Publish The Latest Snapshot

- Add a bounded observation endpoint and an in-memory playback snapshot to the
  coordinator.
- Publish `music.playback` on changes and when the full-screen endpoint first
  connects.

### 3. Prove The State Path

- Add focused adapter and coordinator tests, deploy both fixed runtime
  snapshots, and exercise the supported events against real playback.
- Record recovery behavior and only the normalized evidence needed for review.

## Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Normalize Before The Client Boundary

- Decision: Keep librespot event names and environment variables inside the
  iMac adapter.
- Proposed approach: Merge each relevant event into a small runtime snapshot
  and send the complete normalized state to the coordinator.
- Why: The coordinator and GH-007 should not depend on provider-specific event
  ordering or expose account and client metadata that the room view does not
  need.
- Alternatives: Forward every raw event; let the React client reduce provider
  events; poll Spotify's Web API.
- Review focus: Event ordering, missing fields, track-to-track transitions, and
  stale state after stop or failure.

### H2 - Keep Playback State Ephemeral

- Decision: Retain only the newest playback snapshot in coordinator memory.
- Proposed approach: Replace the current snapshot after exact validation,
  broadcast it through the existing server-sent event connection, and send it
  immediately after endpoint connection.
- Why: Now-playing feedback needs current observed state, not history or
  cross-restart durability. A later receiver event can restore state after a
  coordinator restart.
- Alternatives: Add a database; append an event log; make the browser the
  authoritative store.
- Review focus: Locking, initial state, reconnect behavior, and ensuring one
  malformed report cannot replace valid state.

### H3 - Accept Observations At The Existing LAN Boundary

- Decision: Do not add a credential exchange for this read-only state report.
- Proposed approach: Reuse the coordinator's LAN-scoped HTTP boundary, accept
  only the exact bounded snapshot schema, and add no playback action.
- Why: GH-006 carries non-sensitive now-playing observations on the same local
  network that already accepts `endpoint.identify`. Provisioning and rotating a
  secret would add machinery without protecting a control or durable-data path.
- Alternatives: Provision a shared secret; bind a second private interface;
  tunnel reports through the browser connection.
- Review focus: Request-size limits, strict field validation, log contents, and
  keeping the endpoint unavailable outside the directly connected LAN.
