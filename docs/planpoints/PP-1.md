# PP-1: Connected Room Endpoint

## Slice

A caller on the home network can identify the room endpoint and receive
correlated completion or failure feedback after the iMac visibly responds and
plays a sound through the Sonos.

- The ThinkPad hosts the coordinator and all durable project state.
- The iMac boots unattended into a full-screen network client.
- An `endpoint.identify` action travels from caller to coordinator to iMac.
- The iMac gives unmistakable visual and audible feedback, then reports
  completion.
- Restart and disconnection behavior is visible and recoverable without using a
  normal desktop session.
- Idle CPU, memory, temperature, fan noise, and relevant audio behavior are
  measured rather than assumed.

This is the smallest useful proof of the screen, audio, network, and shared
control seam that later channels and controls need.

## Out Of Scope

- Spotify Connect and general iPhone audio.
- Today, Music, Hue, or other real channels.
- Home Assistant installation or device-authority selection.
- An AI agent, agent adapter, language model, speech recognition, or TTS.
- Microphone, camera, gesture, and presence input.
- General-purpose remote desktop, video streaming, or casting.
- A permanent channel framework, visual design system, or plugin system.
- Public internet access or remote control from outside the home network.

## Deferred To Later Planpoints

- Spotify playback and now-playing state move to Planpoint 2 because they should
  build on a qualified audio endpoint.
- Home Assistant, Hue actions, the Today channel, and the long-term channel
  architecture move to Planpoint 3 because the endpoint seam must work first.
- Agent runtime, speech, memory, and tool-adapter choices move to Planpoint 4
  because they can be compared against a real action and feedback path.
- Repository extraction moves to Planpoint 5 or later because no independently
  deployed feature boundary exists yet.

## Crossroads

### C1 - Parent Repository Boundary

- Decision: How Cortex Home is versioned while its first system boundaries are still
  being discovered.
- Options: One integration repository; nested repositories or submodules from
  the start; a non-repository parent directory containing sibling repositories.
- Impact if wrong: Early repository splits create version coordination and
  duplicated workflow; a later split requires history and CI work.
- Proposed choice: Initialize this folder as one Cortex Home integration repository
  and keep the first three Planpoints in it. Extract only a component with an
  independently useful deployment and maintenance lifecycle.
- Why: The first slices are deliberately discovering the boundaries that a
  repository split would otherwise guess.
- Status: decided

### C2 - First-Slice iMac Presentation Path

- Decision: How ThinkPad-hosted output reaches the `iMac8,1`.
- Options: A full-screen local web client; whole-desktop streaming from the
  ThinkPad; a local shell with on-demand streaming.
- Impact if wrong: Endpoint compute, recovery, video quality, and operating
  system requirements all depend on this path.
- Proposed choice: Use a lightweight full-screen web client for this provisional
  identify slice and measure its real idle and active cost. If it causes
  swapping, sustained fan load, or unacceptable interaction latency, stop before
  real channels inherit it and compare Sunshine/Moonlight.
- Why: The installed system identifies itself as an Early 2008-family
  `iMac8,1`, which does not support using the panel as a general external
  display. A web client is sufficient for this slice and avoids continuous
  desktop-video decoding.
- Status: decided

### C3 - Shared Control Boundary

- Decision: Where display state, allowed actions, and correlated feedback live.
- Options: Each client integrates directly with underlying services; Home
  Assistant becomes the whole application contract; a small Cortex Home coordinator
  sits between controls and narrow adapters.
- Impact if wrong: Web, physical, and future agent controls could inherit
  different permissions, behavior, and feedback.
- Proposed choice: Run one small Cortex Home coordinator on the ThinkPad. It owns the
  endpoint state, allowed action, and live feedback for this slice.
- Why: This proves a shared control seam without choosing an agent runtime or
  forcing product-specific display state into a future device authority.
- Status: decided

## Plumbing

- Threaded now: `endpoint.identify` carries a caller-provided request ID through
  the coordinator to the iMac. The endpoint displays an obvious temporary state,
  plays a test sound through the Sonos, and reports completion or failure tied
  to that request ID.
- Pattern set: Controls request semantic actions from the coordinator; endpoint
  and service adapters report observed completion or failure; subscribed
  interfaces render that feedback. The exact schema remains intentionally small
  and may change until a second real action proves which fields repeat.

## Issues

1. **GH-001 - Bootstrap The Cortex Home Repository**: remove copied Crossroads
   project artifacts, initialize the single repository, and make the accepted
   project documents its entry point.
2. **GH-002 - Qualify The iMac Endpoint**: inventory the exact hardware, record
   the idle baseline, and validate the installed Ubuntu LTS.
3. **GH-003 - Provision The Room Endpoint**: install the accepted minimal Linux
   endpoint and configure unattended full-screen startup, audio, networking, and
   remote recovery.
4. **GH-004 - Identify The Room Endpoint**: implement the smallest coordinator
   and web client that complete the visual, audio, and correlated feedback path.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: parent repository boundary; see Crossroads section.
- C2: iMac presentation path; see Crossroads section.
- C3: shared control boundary; see Crossroads section.

### Hot

#### H1 - Install A Minimal Ubuntu Endpoint

- Decision: Continue from the installed Ubuntu 24.04.4 LTS base and add only the
  packages required by the endpoint after qualifying the available hardware.
- Why: macOS and its data do not need preserving. Reinstalling or trying another
  Linux distribution is cheap, while matching the homelab reduces normal
  administration and deployment variation.
- Alternatives: Debian stable for a leaner traditional-package base; Arch for a
  minimal rolling base; keep macOS; install a full desktop.

#### H2 - Keep Audio At The Room Endpoint

- Decision: Keep the Sonos line-in attached to the iMac and run only the
  playback needed for endpoint feedback there.
- Why: The Sonos and iMac are colocated, and the route avoids a long analog
  cable while leaving expensive audio processing on the ThinkPad.
- Alternatives: Connect the Sonos directly to the ThinkPad; implement a general
  network-audio system in this slice.

#### H3 - Keep The Proof Stack Provisional

- Decision: Use one small coordinator process and one static web client for the
  identify path without declaring a permanent backend or frontend framework.
- Why: This slice needs to qualify the seam, not make Planpoint 3's long-term
  channel-stack decision indirectly.
- Alternatives: Start the complete React application now; use Home Assistant as
  the whole frontend; introduce a broker or plugin framework.
