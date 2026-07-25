# GH-004 Plan: Identify The Room Endpoint

# What

- Add a small ThinkPad-hosted coordinator for the single allowed
  `endpoint.identify` action.
- Serve the real full-screen iMac client from the coordinator and connect it
  through a live event stream.
- Build the client with the accepted React, Vite, Tailwind CSS, pnpm, class
  composition, and Biome toolchain.
- Correlate caller requests, endpoint feedback, completion, failure, and timeout
  with one caller-provided request ID.
- Replace the local qualification page with the network client while preserving
  unattended startup and recovery.
- Prove visual feedback and browser-generated sound through the Sonos, then
  record the real-client resource and interaction baseline.

## Out Of Scope

- Real channels, navigation, Home Assistant, Hue, Spotify, or general media
  playback.
- An AI agent, speech input or output, microphones, cameras, gestures, or
  physical controls.
- Public internet access, authentication, user accounts, TLS, or remote access
  outside the home network.
- A database, durable action history, message broker, plugin system, generic
  action schema, or multiple room endpoints.
- A backend framework, frontend router, data framework, component library, or
  permanent channel architecture.

## Deferred

- A second real action must exist before the request and event shapes become an
  accepted reusable pattern.
- Authentication and broader action policy remain deferred because this
  coordinator is local-only and exposes one harmless allow-listed action.
- General audio routing, mixing, and Spotify playback remain in Planpoint 2;
  this issue proves only the identify sound through the existing Sonos line-in.
- Long-term channel presentation and device authority remain in Planpoint 3.

## Acceptance Criteria

- [ ] The repository contains one understandable coordinator entry point, its
  static client, focused tests, and the fixed service files needed for
  unattended ThinkPad startup.
- [ ] The coordinator uses only the Python standard library, keeps state in
  memory, and serves the built React client and local-network API without a
  backend framework or database.
- [ ] The client uses React, Vite, Tailwind CSS, pnpm, `clsx`, CVA,
  `tailwind-merge`, and Biome without adding a router, data framework, component
  library, or server-side rendering.
- [ ] `endpoint.identify` is the only accepted action; malformed JSON, oversized
  bodies, missing or duplicate request IDs, unknown actions, and invalid
  endpoint callbacks fail explicitly.
- [ ] One caller request is acknowledged, delivered to the connected endpoint,
  and resolved with a correlated completion or failure carrying the original
  request ID.
- [ ] A missing endpoint, dropped endpoint, playback failure, and action timeout
  produce explicit correlated failures rather than false success.
- [ ] The 1920 x 1200 client makes connecting, ready, identifying, completed,
  failed, and disconnected states obvious from across the room.
- [ ] The client reports completion only after its visual response and identify
  sound finish, and end-to-end playback is confirmed through the Sonos rather
  than the iMac speakers.
- [ ] Restarting Chromium or the coordinator visibly disconnects and reconnects
  the client without local login; a controlled reboot restores both the
  coordinator and full-screen endpoint.
- [ ] The recovery-terminal shortcut opens above the real client, and closing
  the terminal returns to the full-screen endpoint.
- [ ] Automated tests cover request validation, correlation, success, endpoint
  failure, disconnection, duplicate IDs, and timeout without requiring the
  physical hosts.
- [ ] The pnpm build and Biome checks pass, and the coordinator serves only the
  generated production client rather than source files or a development server.
- [ ] A sustained real-client sample records CPU, memory, temperatures, fan
  readings, subjective noise, identify latency, and power draw when a measuring
  method is available.
- [ ] Hostnames, addresses, machine identifiers, credentials, and raw host logs
  remain outside Git and committed evidence.
- [ ] `docs/project/IDEA.md` records the completed identify baseline and leaves
  only genuinely unresolved facts under Open Facts.
- [ ] `docs/wip/GH-004.md` records implementation decisions, summarized results,
  automated checks, and explicit manual confirmations for every user-facing
  state.

# Tasks

## 1. GH-004: Define The Identify Coordinator

- Confirm the documented Ubuntu ThinkPad target and its remote administration
  path without committing host-specific identifiers.
- Add the dependency-free coordinator, one in-memory request lifecycle, the
  local-network HTTP boundary, and focused protocol tests.
- Add a repository-owned systemd installation path that copies fixed runtime
  files to the ThinkPad and starts the coordinator unattended.

## 2. GH-004: Connect The Live Room Endpoint

- Replace the dependency-free prototype with the accepted React and Tailwind
  client, using CVA for its named room states and the smaller class helpers only
  where their behavior is needed.
- Replace the qualification page with the full-screen network client and keep
  its coordinator URL in endpoint-local configuration rather than Git.
- Render connection and action phases over a server-sent event stream, play the
  identify sound with the browser audio path, and report observed completion or
  failure to the coordinator.
- Preserve browser restart, coordinator reconnect, Xterm recovery, and
  Wi-Fi-only startup behavior.

## 3. GH-004: Record The Identify Baseline

- Invoke `endpoint.identify` from an outside caller and confirm correlated
  acknowledgement, visual response, Sonos playback, completion, and each
  relevant failure state.
- Run the sustained real-client resource, temperature, fan, noise, latency, and
  available power checks.
- Update the product baseline and durable issue record with sanitized results
  and any plan diffs.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Use Plain HTTP And Server-Sent Events

- Decision: How the caller, coordinator, and first endpoint exchange one live
  action without selecting a permanent application framework.
- Proposed approach: Use Python's standard HTTP server, JSON requests, and one
  server-sent event stream to the endpoint. Keep the caller's action request
  open until the endpoint reports a terminal result or the coordinator times
  out.
- Why: The first slice needs one server-to-endpoint event and one correlated
  result. This keeps the backend dependency-free without introducing a general
  messaging layer.
- Alternatives: A WebSocket framework; short polling; a message broker; separate
  submit and status-polling endpoints.
- Review focus: Clear connection ownership, bounded waits, cleanup after
  disconnects, and no path that reports success before endpoint confirmation.

### H2 - Keep One Explicit In-Memory Action Lifecycle

- Decision: Which states and validation rules exist before a second action
  proves a reusable contract.
- Proposed approach: Allow only `endpoint.identify` and track `accepted`,
  `identifying`, `completed`, or `failed` against a unique caller-provided
  request ID. Keep pending requests in memory and reject duplicates.
- Why: These states prove acknowledgement versus observed completion while
  avoiding a generic workflow engine or durable history that this temporary
  action does not need.
- Alternatives: Fire-and-forget actions; coordinator-generated IDs; persistent
  action records; a generic event envelope.
- Review focus: Correlation, terminal-state ownership, timeout behavior, and
  whether every rejection or failure is visible to both caller and endpoint.

### H3 - Let The React Client Own Identify Feedback

- Decision: Where the synchronized visual and audible identify behavior runs.
- Proposed approach: Have the full-screen React client change its CVA state,
  play a short Web Audio signal, wait for both to finish, and then report
  completion. Add an audio service only if the real Chromium session cannot use
  the qualified rear analog device.
- Why: One browser-owned interaction keeps visual timing, sound timing, and
  completion in the component that directly observes them.
- Alternatives: A separate endpoint daemon using ALSA; coordinator-triggered
  audio; preinstalling PipeWire or PulseAudio.
- Review focus: Honest completion timing, autoplay behavior, device routing,
  audible failure, and whether an extra audio process is actually required.

### H4 - Install Fixed Runtime Files

- Decision: How the coordinator starts reliably without making the repository
  checkout itself a production runtime.
- Proposed approach: Use one fail-fast shell installer to copy fixed coordinator
  files under `/opt/cortex-home`, install a systemd service, and start it. Store
  the coordinator URL only in endpoint-local configuration.
- Why: The ThinkPad should boot unattended from a reviewable snapshot, while
  host-specific network identity stays outside Git.
- Alternatives: Run directly from the working tree; use a user service; build a
  container; introduce configuration management.
- Review focus: Rerunnable installation, explicit file ownership, fail-fast
  behavior, and recovery after reboot.

## Stylistic

### S1 - Design For A Room, Not A Desktop

- Choice: Use one high-contrast, warm retro-futuristic screen with large status
  text and unmistakable motion or color changes for connection and identify
  phases; expose no normal on-screen controls.
- Alternative: A conventional application layout with buttons, logs, and
  developer status panels.
- When to apply: Apply to the GH-004 full-screen endpoint only; later channel
  styling remains undecided.
