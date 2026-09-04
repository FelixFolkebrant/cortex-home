# Shell Roadmap

## Current

- [SHL-001](issues/SHL-001.md) established explicit Today and Music components
  with one concrete shell.
- [SHL-002](wip/SHL-002.md) records the measured rejection of animated channel
  transitions, looped previous/next navigation, and local performance overlay.
  Automated work is complete; final physical reviewer confirmation remains.
- [SHL-003](issues/SHL-003.md) organizes browser source by channel, app, voice,
  diagnostics, and genuinely shared responsibility.
- [SHL-005](wip/SHL-005.md) replaces the fixed-channel model with one Home
  surface, local Music fullscreen, feed-only Camera mode, and Figma-derived
  voice feedback. Automated work is implemented; room review remains.
- `Control`+`Alt`+`1` returns Home, `Control`+`Alt`+`3` toggles Camera, and
  `Control`+`M` toggles Music fullscreen. AirPlay remains always ready without
  a browser screen.

## Next

- Qualify SHL-005 on the physical iMac, then reconcile the superseded SHL-002
  channel-transition review.
- [SHL-004](wip/SHL-004.md) will move client styling into Tailwind utilities
  wherever possible and document the small CSS remainder needed for browser
  primitives and genuinely dynamic presentation.
- Keep `App.jsx` concrete; extract stateful responsibilities only when one
  focused change has a clear owner and focused tests.

## Later

- Add summoned or draggable Home tools only after their invocation, lifetime,
  and data boundaries are clear.
- Reconsider a registry only if real Home composition creates repeated behavior
  that a smaller local extraction cannot solve.

## Open Decisions

- None required for current work.

## Accepted Decisions

- Use one full-screen React Home shell. The coordinator owns only the observed
  `home` or `camera` display mode; Music fullscreen remains local.
- Fade Home to black before Camera capture starts. Do not show Camera status,
  instructions, controls, or failure text over the feed.
- Keep feature-specific files together while shared feedback remains outside
  feature directories.
- Keep Home composition explicit until real summon or drag behavior earns a
  more general abstraction.
