# Camera Roadmap

## Current

- [CAM-001](issues/CAM-001.md) adds the endpoint-local full-screen mirror,
  exact-origin unattended video permission, complete stream cleanup, clear
  failure states, and the keyboard-controlled screen ring light.
- [SHL-005](../shell/wip/SHL-005.md) removes those visible failure states and
  ring-light controls. Camera is now a feed-only display mode entered after a
  Home-to-black fade and still contributes no frames or device metadata to
  coordinator or agent context.

## Next

- Add manual exposure controls only if Chromium reports useful modes and ranges
  for the built-in iSight. Detect capability at runtime, preserve a clear
  automatic-exposure reset, and keep settings local to the mounted mode.

## Later

- Deliberate gestures, presence, or agent vision only through a separately
  accepted sensing flow with visible activation and explicit privacy bounds.
- Photographs or recording only if a concrete local-only use earns a durable
  storage and deletion model.

## Open Decisions

- Whether the built-in camera exposes sufficiently stable exposure controls to
  justify an interface.
- Whether any future vision flow belongs to Camera or to the consuming module.

## Accepted Decisions

- Capture directly in Chromium rather than creating an endpoint or coordinator
  video service.
- Start capture from observed display-mode state and stop all tracks on every exit,
  cleanup, failure, reload, and stale result.
- Grant video capture only to the configured coordinator origin.
- Keep frames local and exclude Camera from voice context.
- Keep every non-live Camera state visually black with no labels, instructions,
  diagnostics, or ring-light UI.
