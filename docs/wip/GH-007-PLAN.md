# GH-007 Plan: Present The Music Channel

## What

- Replace the provisional endpoint-ready screen with a full-screen Music view
  driven by the coordinator's current `music.playback` snapshot.
- Present artwork, title, creators, collection, playback state, and projected
  progress clearly on the 1920 × 1200 room display.
- Preserve coordinator connection, identify, completion, and failure feedback
  as temporary states layered over the Music view.
- Deploy the production client and qualify its live playback, recovery, and
  full-screen behavior on the iMac.

## Out Of Scope

- Starting, pausing, seeking, skipping, changing volume, or selecting Spotify
  content from Cortex Home.
- Spotify Web API access, OAuth, polling, browsing, queues, lyrics, or playback
  history.
- Automatic channel switching, navigation, routing, or a permanent channel
  shell.
- Artwork downloading, proxying, caching, palette extraction, or persistence.
- A reusable media component system before another channel proves a shared
  presentation need.

## Deferred

- Today, room control, and channel navigation remain in Planpoint 3, where the
  long-term channel architecture will be accepted.
- Playback controls remain deferred until a later slice defines their action
  authority and failure feedback.
- Other providers and local media remain provider-specific until a second
  source proves which Music-view behavior should become reusable.

## Acceptance Criteria

- [ ] The endpoint consumes the initial and subsequent `music.playback`
  snapshots without polling or calling Spotify.
- [ ] A loaded track or episode shows its artwork, title, creators, collection,
  playback state, elapsed time, duration, and progress at room-viewing scale.
- [ ] Playing progress advances from `positionMs` and `observedAt`, never moves
  below zero or beyond the item duration, and is replaced by newer snapshots.
- [ ] Paused progress remains fixed, while stopped and unavailable snapshots
  remove stale item metadata, artwork, and progress.
- [ ] Missing, unreachable, or malformed artwork produces an intentional
  fallback without a broken-image icon or unreadable text.
- [ ] Connecting and disconnected states are unmistakable and recover
  automatically without discarding a valid playback snapshot unnecessarily.
- [ ] `endpoint.identify` still produces its existing display pulse and
  three-note sound, and completion or failure is visible without permanently
  replacing the Music view.
- [ ] The composition fits the real 1920 × 1200 kiosk without scrolling, stays
  legible at a smaller desktop viewport, and respects reduced-motion
  preferences.
- [ ] Remote artwork is permitted only as an image resource; the client gains
  no new script, style, media, or connection origin.
- [ ] Focused automated tests cover event-state replacement, projected
  progress bounds, terminal states, and artwork fallback selection.
- [ ] Existing coordinator and endpoint tests continue to pass, and frontend
  formatting, production build, dependency audit, and whitespace checks pass.
- [ ] The issue record contains exact automated and reviewer-owned manual
  confirmation steps for every visible state.

## Tasks

### 1. Model The Music View State

- Separate connection, playback, and temporary identify state so one event
  cannot accidentally erase another.
- Add dependency-free tests for snapshot replacement, progress projection, and
  terminal-state behavior.

### 2. Render The Full-Screen Music Channel

- Build the loaded, stopped, unavailable, connecting, disconnected, identify,
  completion, and failure presentations with the accepted React and Tailwind
  stack.
- Load the snapshot's HTTPS artwork directly, provide a local visual fallback,
  and narrow the Content Security Policy change to image loading.

### 3. Qualify The Real Endpoint

- Run the repository checks, deploy the fixed production client, and exercise
  play, pause, seek, track change, stop, coordinator loss, artwork failure, and
  identify behavior.
- Record exact reconstruction, deployment, recovery, and reviewer confirmation
  steps in the durable issue record.

## Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep Playback And Interaction State Separate

- Decision: Treat playback as the persistent room view and connection or
  identify feedback as independent presentation state.
- Proposed approach: Retain the latest accepted playback snapshot while
  temporary identify feedback appears as a prominent overlay; show connection
  loss without inventing a playback transition.
- Why: An identify request or brief coordinator reconnect should not erase the
  track the receiver last reported, while stale playback must still disappear
  when the coordinator publishes a terminal snapshot.
- Alternatives: Replace the whole view for every event; reduce all events into
  one status enum; hide connection and identify state.
- Review focus: Event ordering, reconnect behavior, failure recovery, and
  preserving the existing identify contract.

### H2 - Project Progress Only In The Client

- Decision: Animate playing progress from the accepted snapshot rather than
  increasing receiver or coordinator event frequency.
- Proposed approach: Compute elapsed position from `positionMs` plus the
  non-negative time since `observedAt`, update the display once per second, and
  clamp it to `durationMs`.
- Why: The coordinator already supplies the stable inputs needed for a useful
  progress display. Polling or high-frequency events would add work without a
  more authoritative source.
- Alternatives: Show a static position; request position every second; use an
  unbounded CSS animation.
- Review focus: Pause and seek replacement, clock skew, duration bounds,
  reduced motion, and timer cleanup.

### H3 - Load Artwork Directly From HTTPS

- Decision: Let the endpoint browser fetch the normalized HTTPS artwork URL.
- Proposed approach: Add `https:` only to the Content Security Policy's
  `img-src`, keep the URL out of CSS and logs, and fall back locally on load
  failure.
- Why: Artwork is already part of the accepted snapshot, while proxying or
  caching it would add storage, request validation, and lifecycle machinery
  for no offline requirement.
- Alternatives: Proxy or cache artwork through the coordinator; omit artwork;
  allow a fixed CDN hostname that Spotify may change.
- Review focus: CSP scope, failed loads, stale images during track changes, and
  avoiding any broader remote-resource permission.

## Stylistic

### S1 - Warm Hi-Fi Sleeve Composition

- Choice: Use the artwork as a large square sleeve beside oversized editorial
  type on warm charcoal, with restrained amber status accents, an ivory
  progress line, and subtle depth rather than a dashboard of cards.
- Alternative: Preserve the centered diagnostic orb; imitate Spotify's player;
  use a dense metadata dashboard or neon sci-fi control panel.
- When to apply: Apply this only to the provisional Music view. Planpoint 3
  will decide whether its visual language becomes part of a reusable channel
  shell.
