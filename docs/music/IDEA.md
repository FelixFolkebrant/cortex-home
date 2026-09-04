# Music

## Purpose

Music makes the existing Sonos line-in feel like part of Cortex Home while
Spotify remains the source and playback controller. The iMac acts as a Spotify
Connect receiver and presents trustworthy now-playing state at room scale.

## Experience

- Spotify on the iPhone discovers one receiver named `Högtalaren`.
- Loaded music contributes a compact artwork, title, creator, and progress card
  to Home.
- Stopped, unavailable, missing-artwork, connecting, and disconnected states
  should never leave stale or broken presentation.
- `Control`+`M` toggles a deliberate Music-only full-screen mode where artwork
  and typography dominate without hiding current voice feedback.

## Boundaries

- Do not require Spotify Web API credentials or browser playback.
- Derive normalized state from local librespot events and keep account, client,
  host, and raw event data private.
- Audio must continue when state reporting fails.
- Spotify remains the playback authority; Cortex Home observes and presents it.

## Relevant Code

- `endpoint/imac/files/cortex_playback_event.py`
- `endpoint/imac/files/cortex-raspotify`
- `coordinator/client/src/music/`
- `coordinator/client/src/app/HomeSurface.tsx`
