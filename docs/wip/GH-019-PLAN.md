# GH-019 Plan: Explore Native AirPlay Composition

# What

- Evaluate UxPlay on the real iMac as a local iPhone AirPlay screen-mirroring
  receiver.
- Test whether its native output can remain beneath the Chromium kiosk while
  Chromium reveals it through a transparent or translucent channel surface and
  retains existing room feedback, fixed shortcuts, and future notifications.
- Record the evidence, constraints, and a recommendation for the smallest
  follow-up implementation issue; do not ship a permanent receiver.

## Out Of Scope

- Production installation, autostart, service ownership, or changes to the
  standard endpoint provisioning flow.
- A new coordinator action, permanent AirPlay channel, Chromium or React
  implementation, desktop compositor/window manager, or notification system.
- Recording, streaming, remote access, general iPhone audio, or any receiver
  beyond deliberate local screen mirroring.

## Deferred

- The exact activation experience and any browser fade or overlay code wait
  until physical layering evidence shows that Chromium can remain above UxPlay.
- Audio policy waits for observed routing behavior through the existing iMac and
  Sonos path; it is not assumed to be part of screen mirroring.
- An alternative receiver or a native overlay waits unless UxPlay evidence
  rules out the proposed composition.

## Acceptance Criteria

- [ ] The issue record identifies the exact UxPlay version, packages or build
  requirements, launch command, and cleanup command used for the real-iMac
  experiment without storing host identity, pairing secrets, or mirrored
  screen content.
- [ ] An iPhone can discover, pair with, start, stop, and reconnect a UxPlay
  screen mirror, or the precise stage and visible failure are recorded.
- [ ] The investigation records whether the UxPlay window is fullscreen,
  borderless, above/below Chromium, and controllable through the installed
  desktop session; it includes focus and recovery behavior.
- [ ] Chromium is tested above the receiver with an opaque baseline and a
  transparent or translucent surface experiment. The record states whether
  existing room feedback and keyboard shortcuts remain usable and visible.
- [ ] The experiment records audio route, Sonos impact, CPU/memory/graphics
  behavior, and startup/stop/recovery observations using windows no longer than
  60 seconds each.
- [ ] UxPlay is stopped and the existing Chromium kiosk behavior is restored at
  the end of every physical test.
- [ ] The issue concludes with a clear recommendation: pursue the layered
  Chromium approach, choose a different composition, or defer AirPlay, plus
  the smallest credible follow-up scope.

# Tasks

## 1. GH-019: Establish The Receiver Baseline

- Inspect the iMac’s existing desktop, kiosk, graphics, network discovery, and
  audio constraints; install or run UxPlay only as a documented experiment.
- This is atomic because it establishes whether a native receiver can run
  without changing Cortex Home’s normal deployment.

## 2. GH-019: Test iPhone Mirroring And Recovery

- Exercise discovery, pairing, start, stop, reconnection, display behavior,
  and audio with the physical iPhone and record content-free observations.
- This is atomic because it evaluates the receiver before any Chromium
  composition hypothesis.

## 3. GH-019: Test The Layered Chromium Hypothesis

- Compare UxPlay beneath Chromium with opaque and transparent/translucent
  Chromium surfaces, preserving an easy return to the kiosk baseline.
- This is atomic because it directly answers whether the proposed seamless
  fade-and-overlay experience is technically credible.

## 4. GH-019: Record The Decision

- Add the durable issue record with evidence, caveats, teardown commands, and
  a recommended follow-up issue or deferral.
- This is atomic because discovery is complete only when it supports a later
  human decision.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Native Receiver Below The Web Shell

- Decision: Verify window stacking and transparency on the actual iMac instead
  of assuming the browser can receive or compose AirPlay video itself.
- Proposed approach: Keep UxPlay ephemeral; test its native window beneath the
  unchanged Chromium kiosk, then run a narrowly reversible Chromium visual
  experiment only if the window stack permits it.
- Why: The desired product experience relies on native-window behavior and
  hardware compositing that cannot be established from a browser prototype.
- Alternatives: Replace or hide Chromium; put UxPlay above it; use a native
  overlay; abandon the layer model.
- Review focus: visibility, z-order, focus, fixed shortcuts, feedback overlays,
  failure recovery, and return to the original kiosk.

### H2 - Preserve The Shared Endpoint

- Decision: Treat every UxPlay run as a bounded experiment that leaves no
  autostart service, policy, media route, or compositor change behind.
- Proposed approach: Use explicit start and stop commands, measure only
  short windows, and restore the existing kiosk and audio route after each
  test.
- Why: The iMac and Sonos are shared physical infrastructure for active issue
  work, so discovery must not silently alter their steady state.
- Alternatives: Install an always-on receiver; modify provisioning now; test
  against a separate endpoint.
- Review focus: changed files, processes, audio state, boot behavior, and the
  documented teardown path.
