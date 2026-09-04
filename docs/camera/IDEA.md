# Camera

## Purpose

Camera turns the iMac's built-in camera into a deliberate full-screen local
mirror. It is a visible endpoint feature, not a network camera or an ambient
sensor.

## Experience

- Entering Camera fades Home to black, then starts one mirrored, video-only
  preview after Camera is the observed display mode.
- Leaving Camera immediately releases every media track.
- Camera shows only the feed. Startup, unsupported, permission, unavailable,
  ended-stream, and recovery states remain black with no text or controls.

## Boundaries

- Frames stay inside Chromium on the iMac and are never recorded, persisted,
  posted to the coordinator, or exposed to Voice.
- Request camera permission only for the configured coordinator origin.
- The component owns capture for exactly its mounted lifetime, including stale
  asynchronous results and failures.
- Keep capture local to this module; Shell owns mode selection and the
  fade-through-black boundary.

## Relevant Code

- `coordinator/client/src/camera/`
- `ops/roles/endpoint/tasks/main.yml`
- `ops/roles/endpoint/tasks/media.yml`
