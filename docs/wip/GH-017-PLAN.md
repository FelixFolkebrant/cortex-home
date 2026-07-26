# GH-017 Plan: Present The Camera Mirror

# What

- Add `camera` as the third explicit coordinator channel and
  `Ctrl`+`Alt`+`3` as its fixed keyboard shortcut.
- Add a Camera component that requests the iMac's built-in front camera only
  after Camera becomes the observed active channel.
- Show a mirrored full-screen, video-only local preview with a visible Camera
  and local-only indicator.
- Stop every media track whenever Camera is no longer active, capture ends,
  permission fails, the component cleans up, or Chromium reloads.
- Rebase GH-014's exact-origin Chromium media policy and add only video capture
  permission for that same configured coordinator origin.
- Show explicit unsupported, unavailable, denied, ended-stream, and retry-on-
  reentry states without affecting other channels or room feedback.

## Out Of Scope

- Camera audio, microphone behavior, agent input, computer vision, presence,
  gestures, recognition, or automation.
- Photographs, recording, buffering, frame extraction, canvas processing,
  remote access, network streaming, coordinator frame payloads, or durable
  media.
- Camera selection, zoom, filters, rotation controls, mouse controls, or
  on-screen channel navigation.
- A router, registry, plugin system, camera service, native application, or new
  frontend dependency.
- Today, Music, Spotify, Hue, voice presentation, or agent context changes.

## Deferred

- Endpoint policy integration and physical iSight confirmation wait until
  GH-014 merges and this branch rebases its shared media-origin boundary.
- Agent behavior while Camera is active is reviewed only after both Planpoints
  merge; frames remain unavailable to the agent.
- Presence, gestures, snapshots, recording, and remote viewing require new
  accepted user flows and privacy decisions.

## Acceptance Criteria

- [ ] The coordinator accepts exactly `today`, `music`, and `camera` for
  `channel.select`; invalid values still fail without changing active state.
- [ ] `Ctrl`+`Alt`+`3` submits Camera through the existing action lifecycle,
  while repeat or extra modifiers remain ignored.
- [ ] Camera capture starts only after an observed `channel.active` snapshot
  reports `camera`, never merely because a request was submitted or accepted.
- [ ] The request is video-only and the selected iMac camera appears mirrored,
  full-screen, correctly cropped, and without captured audio.
- [ ] Camera remains unmistakably labeled as a local mirror while active, and
  shared connection, lighting, identify, scene, and channel feedback remains
  visible above it.
- [ ] Selecting Today or Music stops every Camera `MediaStreamTrack` before the
  other channel remains visible.
- [ ] Cleanup, capture rejection, ended tracks, reload, and error paths release
  owned media and cannot attach a stale stream after reentry.
- [ ] Unsupported API, missing camera, exact-origin policy failure, permission
  denial, and ended-stream states show clear local failure rather than a blank
  or frozen full-screen view.
- [ ] Re-entering Camera makes one fresh bounded capture attempt and can recover
  after a transient failure.
- [ ] Chromium grants video capture only to the configured coordinator origin;
  no wildcard, global all-media flag, stored deployment hostname, or unrelated
  page receives permission.
- [ ] No frame, image, device label, or stream metadata is posted to the
  coordinator, added to SSE, persisted, logged, or included in agent context.
- [ ] Component tests use owned fake streams to prove start, stop, stale-result,
  failure, and reentry behavior without requiring real camera hardware.
- [ ] Biome, frontend tests, production build, production audit, Python suites,
  endpoint provisioning checks, and whitespace checks pass.

# Tasks

## 1. Add The Explicit Camera Channel

- Extend coordinator validation, frontend keyboard classification, reducer
  expectations, and the hard-coded application switch with `camera`.
- Preserve the existing `channel.select` request and observed-completion
  semantics without a registry or configuration layer.

## 2. Own The Local Camera Lifecycle

- Add one Camera component that requests `getUserMedia({ audio: false, video:
  true })` only while active.
- Attach only the current request's stream, mirror the visible video, and stop
  every owned track on exit, error, cleanup, or replacement.
- Keep the full-screen channel itself as the primary sensing indicator and add
  concise local-only labeling that remains visible over live video.

## 3. Make Camera Failure Recoverable

- Render explicit unsupported, unavailable, denied, and ended-stream states.
- Retry only after the user deliberately leaves and re-enters Camera; do not
  add automatic background retries.
- Test async stale-stream and cleanup behavior with fake media tracks.

## 4. Extend The Exact-Origin Kiosk Policy

- Fetch and rebase merged GH-014 before touching the shared Chromium policy.
- Add only `VideoCaptureAllowedUrls` for the same generated coordinator origin
  and keep the existing audio and secure-context entries intact.
- Reprovision the iMac, inspect effective policies, restart the kiosk, and
  confirm unattended video access without a prompt.

## 5. Confirm The Physical Mirror

- Verify the built-in iSight device, local full-screen framing, orientation,
  stop indicator, reentry, reboot recovery, resource use, and independent room
  feedback on the actual iMac.
- Create `docs/wip/GH-017.md` with exact deployment commands, lifecycle
  walkthrough, problems, automated checks, and reviewer-owned visual/privacy
  confirmation.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Let Observed Channel State Authorize Capture

- Decision: Start camera access only from the observed active channel and stop
  it on every transition away.
- Proposed approach: Make Camera component mount or active state own one
  request generation and its tracks; stale resolutions stop themselves.
- Why: An accepted shortcut request is not proof that the display changed, and
  camera lifetime must match what the user can see.
- Alternatives: Start on keydown; start at application boot; retain a shared
  background stream; trust optimistic local state.
- Review focus: Request races, rapid channel changes, failures, and cleanup.

### H2 - Keep A Mirror From Becoming A Camera Platform

- Decision: Render the browser stream directly and expose no frame boundary.
- Proposed approach: Use one muted inline video element with mirrored
  presentation and no canvas, recorder, upload, or coordinator event.
- Why: The accepted flow needs only a local reflection.
- Alternatives: Endpoint stream service; snapshots; recording; image analysis;
  agent vision.
- Review focus: Network requests, logs, state payloads, dependencies, and media
  lifecycle.

### H3 - Extend Rather Than Duplicate Media Permission

- Decision: Rebase GH-014 and add video permission to its exact-origin policy.
- Proposed approach: Preserve the shared secure-context and audio entries, add
  only the video allowlist, and verify effective Chromium policy after
  provisioning.
- Why: Competing policy files or wildcard launch flags would make permission
  ownership unclear and could broaden sensor access.
- Alternatives: Independent Camera policy; global auto-approval flag; TLS
  migration in this issue; interactive kiosk prompt.
- Review focus: Rebase dependency, exact origin, idempotent provisioning, and
  absence of wildcard grants.

## Stylistic

### S1 - Make The Preview Feel Like A Mirror

- Choice: Fill the display with a horizontally mirrored live image, preserve
  aspect ratio through intentional cropping, and keep only a restrained
  Camera/local-only label plus shared room feedback above it.
- Alternative: Letterboxed video player; dashboard card; controls and chrome;
  unmirrored capture.
- When to apply: Live Camera presentation only; failure states retain the
  established room typography and feedback language.
