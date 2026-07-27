# GH-020 Plan: Transition Between Channels

# What

- Add a short, deliberate visual transition when an observed channel change
  replaces one browser-rendered view with another.
- Use the browser View Transition API when it is available, with an immediate
  behavior-preserving fallback and a no-motion path for reduced-motion users.
- Preserve synchronous Camera cleanup, AirPlay's native composition boundary,
  shared room feedback, and the coordinator as the sole source of active
  channel state.

## Out Of Scope

- Changing channel shortcuts, action acknowledgement, coordinator contracts,
  channel content, Camera capture, AirPlay process control, or Music's internal
  track transition.
- A router, browser history, gesture navigation, configurable animation,
  transition libraries, or a general animation framework.
- Holding a live Camera stream behind another view or capturing Camera frames
  for animation.
- Redesigning channel content or the Home/Today screen.

## Deferred

- Cross-document navigation transitions remain deferred because Cortex Home is
  one application shell with no router.
- Channel-specific transition choreography waits until one shared transition
  proves timing, readability, and iMac rendering cost.
- Animated Camera and native AirPlay handoffs remain deferred unless a later
  issue can preserve their privacy and compositor boundaries without retained
  snapshots.

## Acceptance Criteria

- [ ] A transition starts only when a new `channel.active` snapshot changes the
  observed channel, never on keydown, request submission, acknowledgement,
  reconnect replay, or a rejected action.
- [ ] Supported Chromium uses `document.startViewTransition` for eligible
  browser-rendered channel changes without adding a dependency or router.
- [ ] The outgoing view leaves and the incoming view settles in a short,
  consistent motion that remains readable on the physical iMac and does not
  obscure shared action, connection, lighting, or voice feedback.
- [ ] Camera entry and exit remain immediate privacy cuts: every owned track is
  stopped before another channel paints, and no frozen Camera frame participates
  in a transition snapshot.
- [ ] AirPlay entry and exit preserve the accepted native lower-layer
  composition and do not snapshot, cover, or delay receiver teardown.
- [ ] Music's existing fullscreen and track-change animations remain unchanged
  and do not double-animate during channel selection.
- [ ] Rapid observed channel changes settle on the newest channel without stale
  content, uncaught transition promises, blocked input, or an obsolete
  transition completing over current state.
- [ ] Browsers without the API and users with `prefers-reduced-motion: reduce`
  receive the exact current immediate channel replacement behavior.
- [ ] Initial load, unavailable channels, connection loss, voice phases, and
  failed channel actions remain clear and do not animate as false navigation.
- [ ] Automated tests cover observed-state triggering, unsupported and
  reduced-motion fallbacks, rapid replacement, Camera/AirPlay exclusions, and
  cleanup without depending on real animation timing.
- [ ] A deployed manual pass confirms Today-to-Music motion, reverse motion,
  Music fullscreen exit, Camera and AirPlay privacy cuts, rapid switching,
  feedback layering, and acceptable rendering on the iMac.

# Tasks

## 1. GH-020: Transition Observed Channel Changes

- Isolate the observed channel presentation update behind one small transition
  boundary and add the View Transition API choreography and focused tests.
- This is atomic because it introduces the transition without changing any
  channel contract or content.

## 2. GH-020: Preserve Motion And Media Boundaries

- Add reduced-motion and unsupported fallbacks, exclude Camera and AirPlay
  snapshots, and prove interruption, cleanup, and shared-feedback layering.
- This is atomic because it hardens the visual enhancement around the product's
  existing accessibility, privacy, and native-composition constraints.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Transition Only Safe Browser Views

- Decision: Animate ordinary browser-rendered channel replacements while
  keeping Camera and AirPlay as immediate cuts.
- Proposed approach: Invoke one rootless, named channel-surface transition only
  for eligible observed changes. Do not include Camera video, the native
  AirPlay surface, or persistent shared feedback in a captured transition.
- Why: A frozen Camera frame conflicts with the accepted local-live-view
  boundary, and AirPlay is composed outside Chromium.
- Alternatives: Snapshot every channel; keep outgoing media mounted; animate a
  full-root screenshot; disable transitions everywhere.
- Review focus: exact eligibility, DOM snapshot scope, track teardown,
  AirPlay visibility, and feedback z-order.

### H2 - Prefer A Progressive Browser Primitive

- Decision: Use the native View Transition API as a progressive enhancement
  instead of introducing an animation package or parallel channel stack.
- Proposed approach: Feature-detect the API, keep one current channel DOM, and
  fall back to the existing immediate render when unsupported or reduced motion
  is requested.
- Why: The browser primitive can coordinate old and new rendering without a
  durable abstraction or duplicated live channel state.
- Alternatives: CSS-only enter animation; two mounted React trees; an animation
  dependency; a custom canvas transition.
- Review focus: small ownership boundary, React update timing, interruption,
  rejected promises, and no retained obsolete tree.

## Stylistic

### S1 - Quiet Room-Scale Motion

- Choice: Use one brief easing curve with subtle opacity and displacement,
  keeping the motion subordinate to content and feedback.
- Alternative: Large directional slides, zooms, blur, per-channel effects, or
  long cinematic transitions.
- When to apply: Only to an eligible observed channel replacement.
