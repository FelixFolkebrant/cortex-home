# Camera

## Purpose

Camera turns the iMac's built-in camera into a deliberate full-screen local
mirror. It is a visible endpoint feature, not a network camera or an ambient
sensor.

## Experience

- Entering Camera starts one mirrored, video-only preview after Camera is the
  observed active channel.
- Leaving Camera immediately releases every media track.
- Clear unsupported, permission, unavailable, ended-stream, and recovery states
  replace blank or frozen output.
- A Camera-local screen ring light offers off, warm, white, and cold modes with
  a small set of useful widths.

## Boundaries

- Frames stay inside Chromium on the iMac and are never recorded, persisted,
  posted to the coordinator, or exposed to Voice.
- Request camera permission only for the configured coordinator origin.
- The component owns capture for exactly its mounted lifetime, including stale
  asynchronous results and failures.
- Keep camera presentation and controls local to this module; Shell owns only
  selection and shared feedback.

## Relevant Code

- `coordinator/client/src/channels/camera/`
- `ops/roles/endpoint/tasks/main.yml`
- `ops/roles/endpoint/tasks/media.yml`
