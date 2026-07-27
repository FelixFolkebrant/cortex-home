# PP-6: iPhone AirPlay Receiver Exploration

## Slice

Establish whether the iMac can show an iPhone AirPlay screen mirror through
UxPlay while Chromium remains the visible Cortex Home shell, and record the
evidence needed to choose a later implementation slice.

- The investigation starts and stops UxPlay on the real iMac and confirms
  discovery, pairing, screen mirroring, audio routing, and recovery behavior.
- It determines whether the native UxPlay output can sit below Chromium while
  Chromium fades its channel background and retains Cortex Home overlays.
- It documents the compositor, window-stack, focus, keyboard, kiosk, and
  notification constraints that affect a seamless handoff.
- It proposes the smallest implementation issue only after observing the real
  endpoint; it does not make a receiver permanent during this slice.

This is the right next step because AirPlay receiving is a native display and
audio capability, not a Chromium API, and the proposed layered composition
needs evidence on the actual endpoint before it shapes the client architecture.

## Out Of Scope

- A permanent AirPlay receiver service, unattended startup, deployment, or
  production iMac configuration changes.
- Replacing Chromium, adding a window manager or compositor, or rewriting the
  React shell into a native application.
- AirPlay audio-only support, arbitrary desktop streaming, remote access,
  recording, screen capture, relay streaming, or persistence.
- Coordinator, agent, Hue, Spotify, microphone, camera, or channel-contract
  changes.
- Designing general notification, overlay, or window-management frameworks.

## Deferred To Later Planpoints

- A user-facing AirPlay channel and its activation control wait for the
  measured receiver and composition choice.
- Any permanent native-window policy waits until the investigation establishes
  that Chromium overlays can remain reliable above UxPlay.
- General iPhone audio, additional casting protocols, and remote casting wait
  until one deliberate local screen-mirror flow proves useful.

## Crossroads

### C1 - Receiver And Composition Boundary

- Decision: Whether UxPlay can provide a reliable native AirPlay surface below
  the existing Chromium kiosk, with Chromium selectively revealing that
  surface while retaining Cortex Home overlays.
- Options: UxPlay below transparent or translucent Chromium; a UxPlay window
  above or beside Chromium; temporarily hiding Chromium; replacing the kiosk;
  a browser-only approach; defer the capability.
- Impact if wrong: A premature composition choice could replace the accepted
  web shell, prevent reliable room controls, or leave native media windows
  stranded above essential feedback.
- Proposed choice: Run a bounded real-endpoint investigation with UxPlay and
  test the proposed lower-native-window/upper-Chromium model before selecting
  an implementation architecture.
- Why: AirPlay cannot be assumed to fit the browser client, while the existing
  client already owns room state, fixed shortcuts, and feedback that should not
  disappear without evidence.
- Status: decided

### C2 - Discovery And Receiver Lifecycle

- Decision: What native dependencies, network advertisement, pairing behavior,
  audio route, startup model, and recovery behavior an iPhone mirror needs on
  the iMac.
- Options: UxPlay with its documented dependencies; an alternative native
  receiver; a dedicated appliance; no receiver.
- Impact if wrong: A receiver could be unavailable after reboot, disrupt the
  Sonos route, or require broad network or desktop privileges that do not fit
  the endpoint.
- Proposed choice: Measure UxPlay on the provisioned iMac and record only
  observed requirements and failures before proposing installation or service
  ownership.
- Why: The endpoint's older graphics, existing PulseAudio/Sonos route, and
  Chromium kiosk are product constraints that package documentation cannot
  answer.
- Status: decided

## Plumbing

- Existing lower layer: the native UxPlay process may own only the received
  iPhone mirror and its ephemeral audio while it runs.
- Existing upper layer: Chromium remains responsible for Cortex Home channel
  rendering, connection feedback, keyboard controls, and any retained
  notification overlays.
- Evidence boundary: the issue records commands, configuration prerequisites,
  measured behavior, and screenshots or observations without retaining iPhone
  screen content.
- Pattern set: validate a native escape hatch against the live web shell before
  introducing a channel, protocol, or permanent service boundary.

## Issues

1. **GH-019 - Explore Native AirPlay Composition**: evaluate UxPlay discovery,
   mirroring, audio, lifecycle, and the proposed UxPlay-below-Chromium layering
   on the iMac; record a recommendation and follow-up implementation scope.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: receiver and composition boundary; see Crossroads section.
- C2: discovery and receiver lifecycle; see Crossroads section.

### Hot

#### H1 - Preserve Visible Room Controls During Mirroring

- Decision: Test whether Chromium can make only its channel surface transparent
  or translucent while keeping existing feedback and keyboard behavior visible
  above UxPlay.
- Why: The proposed seamless transition is useful only if the display retains
  the controls and feedback users already rely on.
- Alternatives: Hide Chromium entirely; put UxPlay above it; add a native
  overlay; leave casting as a separate application.

#### H2 - Do Not Promote Experiment Setup To Production

- Decision: Keep all receiver installation, startup, and compositor changes
  reversible and documented as experiment evidence until a later issue is
  accepted.
- Why: Native desktop and media changes can affect the shared iMac kiosk and
  Sonos route beyond a single channel.
- Alternatives: Install and autostart UxPlay immediately; replace the kiosk;
  accept a separate manual application as the product flow.
