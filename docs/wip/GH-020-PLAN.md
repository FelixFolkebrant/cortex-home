# GH-020 Plan: Evaluate Channel Transitions

# What

- Evaluate visual transitions between coordinator-observed channel changes on
  the physical low-end iMac.
- Keep immediate channel replacement after the snapshot and fade experiments
  proved slower and less reliable than a direct cut.
- Let `Ctrl`+`Alt`+`Left` and `Ctrl`+`Alt`+`Right` request the previous and next
  channel in the fixed channel order, including loopback.
- Add an on-demand `Ctrl`+`Alt`+`M` overlay with real local CPU, memory,
  temperature, load, and uptime data from the iMac.
- Preserve the findings and rejected alternatives in
  `docs/CHROMIUM_PERFORMANCE.md`.

## Out Of Scope

- Further channel-transition animation, retained outgoing views, snapshots,
  routers, framework migrations, configurable motion, or animation libraries.
- Changing action acknowledgement, coordinator contracts, channel content,
  Camera capture, AirPlay process control, or Music's internal track transition.
- Redesigning the Home/Today screen; GH-021 owns that presentation.

## Deferred

- Animated channel changes remain deferred until different endpoint hardware or
  measured compositor evidence justifies revisiting the accepted instant cut.
- SSR, Astro, Preact, multi-page navigation, and a vanilla rewrite remain
  deferred because they do not address the measured runtime transition path.

## Acceptance Criteria

- [ ] Every changed `channel.active` snapshot replaces the current React channel
  immediately, with no animation, snapshot, retained channel tree, timer,
  transition promise, or delayed state commit.
- [ ] Initial snapshots, reconnect replay, unavailable channels, connection
  loss, voice phases, and failed channel actions remain clear and do not create
  false navigation.
- [ ] Camera cleanup remains synchronous before another channel paints, AirPlay
  retains its native composition boundary, and Music fullscreen and track
  animations remain unchanged.
- [ ] `Ctrl`+`Alt`+`Left` and `Ctrl`+`Alt`+`Right` request the prior and next
  fixed channel respectively, loop from Today to AirPlay and AirPlay to Today,
  and retain the exact-modifier and non-repeating shortcut boundary.
- [ ] Exact non-repeating `Ctrl`+`Alt`+`M` toggles one compact performance
  overview above every Chromium-rendered view; it polls only while visible and
  fails clearly when the loopback endpoint is unavailable.
- [ ] The overview reports bounded real iMac CPU, memory, temperature,
  one-minute load, and uptime without adding a dependency, network listener,
  host identifier, process list, or persistent telemetry.
- [ ] `docs/CHROMIUM_PERFORMANCE.md` explains why View Transition snapshots,
  fade-through-black, SSR, Astro, Preact, vanilla DOM, and multi-page navigation
  were not selected.
- [ ] Automated tests cover loopback navigation, exact shortcuts, metrics
  validation, overlay presentation, endpoint bounds, and the existing immediate
  channel reducer behavior.
- [ ] A deployed manual pass confirms immediate switching across every channel,
  Camera/AirPlay boundaries, rapid switching, and the performance overlay.

# Tasks

## 1. GH-020: Measure And Reject Expensive Motion

- Research and prototype bounded transition approaches, test them on the iMac,
  and preserve the final decision and useful evidence.
- This is atomic because it resolves one presentation decision without changing
  channel content or contracts.

## 2. GH-020: Add Local Performance Visibility

- Extend the existing loopback endpoint bridge with one bounded current stats
  route and add a global on-demand browser overlay.
- This is atomic because it adds diagnostics without retaining telemetry or
  changing coordinator state.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Prefer Reliable Instant Cuts On This Endpoint

- Decision: Commit each observed channel directly with no transition layer.
- Proposed approach: Keep one current channel DOM and dispatch the validated
  `channel.active` snapshot immediately.
- Why: View Transition snapshots lagged on the iMac, and the follow-up black
  fade introduced a state-update failure. Motion is not worth weakening the
  basic channel switch.
- Alternatives: View Transition snapshots; fade-through-black; incoming-only
  CSS animation; two retained view trees; Canvas/WebGL.
- Review focus: absence of transition code, synchronous media cleanup, and
  reliable rapid switching.

## Stylistic

### S1 - No Channel Motion

- Choice: Use an immediate cut between channels.
- Alternative: Slides, fades, zooms, blur, snapshots, or per-channel effects.
- When to apply: Every coordinator-observed channel replacement on the iMac.
