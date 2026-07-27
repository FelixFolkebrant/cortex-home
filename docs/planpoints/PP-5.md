# PP-5: Independent Channel Evolution

## Slice

Today and Music become explicit channel modules, Music receives one focused
visual polish pass, and a deliberate Camera channel turns the iMac's built-in
front camera into a full-screen local mirror without blocking or depending on
the concurrent voice-agent behavior.

- The full-screen React shell retains one coordinator connection, shared room
  feedback, and explicit channel selection.
- Today and Music live in separate components without changing their state
  contracts or behavior.
- Shared room state, keyboard classification, and feedback use names that no
  longer imply they belong only to Music.
- Music receives one visual and narrow-screen polish pass while preserving
  every current playback state and the existing Spotify integration.
- `Ctrl`+`Alt`+`3` selects Camera through the same `channel.select` action.
- Camera starts only after Camera becomes the observed active channel and stops
  every local media track when another channel becomes active.
- Camera frames remain inside Chromium on the iMac and are never sent to the
  coordinator, retained, recorded, or exposed to the voice agent.
- Channel work uses issue worktrees with independent documentation checkouts;
  deployment to the shared physical room remains serialized.

This is the smallest useful channel-expansion slice because a third real
channel proves which presentation seams repeat while direct, bounded endpoint
hardware access proves a genuinely different view without inventing a plugin
framework or a camera service.

## Out Of Scope

- A router, browser history, deep links, dynamic channel discovery, a plugin
  API, configurable dashboards, widgets, or user-managed channel ordering.
- Mouse, touchscreen, on-screen channel controls, configurable shortcuts, or
  more than the three fixed channel shortcuts.
- Changing Today's presentation or weather provider, Spotify playback
  integration, Hue state, or existing coordinator action semantics.
- Camera photographs, recording, remote viewing, network streaming, filters,
  zoom, device selection, surveillance, presence detection, gestures, face
  recognition, computer vision, or agent camera context.
- Camera audio or general microphone behavior; deliberate microphone capture
  remains owned by Planpoint 4.
- Making Camera answerable by the voice agent in this slice.
- Sharing a mutable `docs/`, dependency, build, or deployment directory across
  worktrees.

## Deferred To Later Planpoints

- Agent behavior while Camera is active remains deferred until the voice and
  camera slices are merged. No camera frame will enter normalized room context.
- Camera-assisted presence, gestures, and visual agent input remain deferred
  because a deliberately selected local mirror does not justify ambient
  sensing.
- Additional channels remain one useful slice at a time so Photos, stocks,
  local media, and TV do not force a common interface before their data and
  interaction needs are known.
- A channel registry or plugin protocol remains deferred until explicit wiring
  for at least three channels produces repeated code that a smaller local
  abstraction cannot remove.

## Crossroads

### C1 - Channel Module Boundary

- Decision: How independent channel work avoids repeatedly editing the complete
  application shell.
- Options: Keep every view in `App.jsx`; extract explicit channel components;
  add a router; build a dynamic registry or plugin API; split channels into
  separate applications.
- Impact if wrong: Parallel channel work could create permanent merge hotspots,
  while a premature extension framework would define contracts before channel
  needs are known.
- Proposed choice: Keep explicit Today and Music components plus shared room
  state and feedback modules. Retain one small hard-coded channel switch and
  add Camera explicitly when its real lifecycle exists.
- Why: Three known channels justify file ownership and accurate names, but not
  runtime discovery, routing, configuration, or separate deployments.
- Status: decided

### C2 - Camera Capture Boundary

- Decision: Whether a full-screen mirror reads the iMac camera in Chromium,
  streams frames through a new endpoint service, or sends them through the
  ThinkPad coordinator.
- Options: Direct browser `getUserMedia`; local camera daemon and browser
  stream; coordinator-hosted stream; native camera application.
- Impact if wrong: A mirror could create a hidden network video path, retain
  frames accidentally, or add an endpoint service that outlives the visible
  channel.
- Proposed choice: Let the Camera component request video-only
  `getUserMedia` directly in Chromium after `camera` is the observed active
  channel. Render the stream mirrored and full-screen, retain no frames, and
  stop every track on channel change, component cleanup, failure, or reload.
- Why: The camera and display are on the same endpoint. Direct browser preview
  is the shortest path that keeps pixels local and makes the React component
  own the exact visible lifetime.
- Status: decided

### C3 - Kiosk Media Permission Boundary

- Decision: How the unattended Chromium kiosk receives media permission on the
  existing local HTTP coordinator origin.
- Options: Move the complete coordinator to HTTPS; show interactive permission
  prompts; grant all origins or all media; use exact-origin Chromium policies;
  add an endpoint camera service.
- Impact if wrong: Camera or microphone capture could fail after reboot, or a
  broad unattended grant could let unrelated pages activate private sensors.
- Proposed choice: Provision only the configured coordinator origin as an
  allowed secure-context exception. GH-014 owns that shared origin boundary and
  the audio allowlist; GH-017 rebases it and adds only the exact-origin video
  allowlist. Neither issue grants wildcard origins or uses a global
  auto-approve media flag.
- Why: Chromium restricts `getUserMedia` to secure contexts, while its Linux
  policies can grant capture to an exact origin without an unusable kiosk
  prompt. One shared origin boundary prevents the concurrent microphone and
  camera work from inventing separate permission paths.
- Status: decided

### C4 - Parallel Worktree And Documentation Ownership

- Decision: Whether concurrent issue branches share checked-out documentation
  or keep branch-local copies.
- Options: Symlink one shared `docs/`; keep separate worktree checkouts; create
  a documentation repository; let each branch allocate its own issue numbers.
- Impact if wrong: Shared files can change behind another worktree's index, and
  independent number allocation can create colliding issue records.
- Proposed choice: Reserve all issue numbers and accepted issue plans on
  `main`. Give every issue worktree its complete normal `docs/` checkout.
  GH-014 and GH-015 may proceed independently; GH-017 may begin isolated
  frontend work but must rebase merged GH-014 before endpoint permission
  integration and physical camera confirmation.
- Why: Worktrees already share Git objects and refs. The one explicit dependency
  is safer than letting two branches independently change the kiosk media
  security boundary.
- Status: decided

## Plumbing

- Threaded first: the existing `channel.active`, `today.summary`,
  `music.playback`, `room.lighting`, and action feedback contracts live behind
  explicit frontend module boundaries without changing their payloads.
- Threaded next: `channel.select` adds only `camera`, and `Ctrl`+`Alt`+`3`
  submits that exact value through the existing request lifecycle.
- Camera boundary: the active Camera component owns one video-only
  `MediaStream`; no camera state or frame payload is added to coordinator SSE.
- Permission boundary: the kiosk trusts only its configured coordinator origin
  for required secure-context and capture policies. Audio permission belongs to
  GH-014 and video permission belongs to GH-017.
- Recovery boundary: missing hardware, denied permission, unreadable video, or
  ended media tracks produce an explicit local Camera failure without changing
  Today, Music, Hue, voice, or coordinator health.
- Pattern set: each channel owns one explicit view while the application shell
  owns connection, observed selection, and shared room feedback.

## Issues

1. **GH-013 COMPLETE - Separate The Channel Shell**: extracted Today, Music,
   room state, keyboard classification, and shared feedback into accurately
   named frontend modules without visual, contract, dependency, or behavior
   changes.
2. **GH-015 - Polish The Music Channel**: improve Music's hierarchy,
   distance readability, artwork treatment, long-metadata behavior, and narrow
   layout while preserving every existing playback and failure state.
3. **GH-017 - Present The Camera Mirror**: add the explicit Camera view, fixed
   third shortcut, video-only local capture lifecycle, exact-origin kiosk video
   permission, mirrored full-screen preview, and independent failure recovery.

The accepted slice is complete. Two presentation-only follow-ups reuse its
explicit channel ownership without changing the original channel contracts:

4. **GH-020 - Transition Between Channels**: progressively enhance observed
   browser-rendered channel changes with short native view transitions while
   preserving Camera privacy, AirPlay composition, reduced motion, and
   unsupported-browser behavior.
5. **GH-021 - Redesign The Home Screen**: recompose the existing Today channel
   as the calm default Home view using only its current clock and weather data.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: channel module boundary; see Crossroads section.
- C2: camera capture boundary; see Crossroads section.
- C3: kiosk media permission boundary; see Crossroads section.
- C4: parallel worktree and documentation ownership; see Crossroads section.

### Hot

#### H1 - Separate Files Without Inventing Extensions

- Decision: Give real channels independent files and tests while retaining one
  explicit application switch.
- Why: File ownership reduces merge conflicts; a runtime registry would add a
  broader product contract than three channels require.
- Alternatives: Keep the monolith; build a plugin API; split deployments.

#### H2 - Tie Camera Lifetime To The Visible Channel

- Decision: Request video only after Camera is observed active and stop every
  track whenever it is no longer active.
- Why: A local mirror must not leave the camera active behind another channel
  or after an error.
- Alternatives: Start capture at application boot; retain one background
  stream; run a permanent endpoint camera service.

#### H3 - Keep Camera Pixels On The Endpoint

- Decision: Render the `MediaStream` directly without snapshots, recording,
  network transport, analysis, or agent context.
- Why: The user flow needs a mirror, not a sensing or video platform.
- Alternatives: Proxy through the coordinator; expose an MJPEG stream; retain
  stills; publish camera context.

#### H4 - Keep Concurrent Integration Serialized

- Decision: Code and test in issue worktrees, rebase GH-017 over GH-014's shared
  media-origin boundary, and deploy only one integrated branch at a time.
- Why: Git can isolate source work, while the ThinkPad, iMac, camera,
  microphone, Hue bridge, and Sonos are one shared environment.
- Alternatives: Competing media policies; simultaneous deployments; separate
  repositories or duplicated environments.

## References

- Chromium secure-context override policy:
  `https://chromeenterprise.google/policies/override-security-restrictions-on-insecure-origin/`
- Chromium video capture allowlist:
  `https://chromeenterprise.google/policies/video-capture-allowed-urls/`
