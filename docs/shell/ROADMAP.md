# Shell Roadmap

## Current

- [SHL-001](issues/SHL-001.md) established explicit Today and Music components
  with one concrete shell.
- [SHL-002](wip/SHL-002.md) records the measured rejection of animated channel
  transitions, looped previous/next navigation, and local performance overlay.
  Automated work is complete; final physical reviewer confirmation remains.
- [SHL-003](issues/SHL-003.md) organizes browser source by channel, app, voice,
  diagnostics, and genuinely shared responsibility.
- The fixed channel order is Today, Music, Camera, AirPlay, and Alarm, selected
  by `Control`+`Alt`+`1` through `5` or previous/next arrows.

## Next

- Finish the reviewer-owned SHL-002 physical confirmation and archive it.
- Keep `App.jsx` concrete; extract stateful responsibilities only when one
  focused change has a clear owner and focused tests.

## Later

- Add another channel only after its user flow and data or hardware boundary is
  clear.
- Reconsider a registry or router only if explicit composition creates repeated
  behavior that a smaller local extraction cannot solve.

## Open Decisions

- None required for current work.

## Accepted Decisions

- Use one full-screen React shell with coordinator-owned active-channel state.
- Replace channels immediately after observed state; do not retain outgoing
  view trees or animate global channel changes on the current iMac.
- Keep one hard-coded channel switch and fixed keyboard mapping.
- Keep channel-specific files together while cross-channel feedback remains
  outside channel directories.
