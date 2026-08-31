# Camera Roadmap

## Current

- [CAM-001](issues/CAM-001.md) adds the endpoint-local full-screen mirror,
  exact-origin unattended video permission, complete stream cleanup, clear
  failure states, and the keyboard-controlled screen ring light.
- Camera is the third fixed channel and intentionally contributes no frames or
  device metadata to coordinator or agent context.

## Next

- Add manual exposure controls only if Chromium reports useful modes and ranges
  for the built-in iSight. Detect capability at runtime, preserve a clear
  automatic-exposure reset, and keep settings local to the mounted channel.

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
- Start capture from observed channel state and stop all tracks on every exit,
  cleanup, failure, reload, and stale result.
- Grant video capture only to the configured coordinator origin.
- Keep frames local and exclude Camera from voice context.
