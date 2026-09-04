# Music Roadmap

## Current

- [MUS-001](issues/MUS-001.md) provisions the pinned Raspotify receiver on the
  shared Sonos audio route.
- [MUS-002](issues/MUS-002.md) normalizes librespot events and publishes current
  playback state through the coordinator.
- [MUS-003](issues/MUS-003.md) presents loaded, paused, stopped, unavailable,
  progress, and artwork-fallback states.
- [MUS-004](issues/MUS-004.md) adds focused room-scale polish, browser-derived
  artwork color, and the Music-only full-screen presentation.
- [SHL-005](../shell/wip/SHL-005.md) replaces the ordinary Music channel with a
  compact live Home card while retaining local `Control`+`M` fullscreen.

## Next

- Address only observed playback-state or presentation gaps. Keep receiver
  operation independent of optional visual polish.

## Later

- Local media, queues, upcoming metadata, playlists, or general video playback
  only when the selected source can provide truthful state.
- Additional playback services only behind the same normalized observation
  boundary.

## Open Decisions

- Whether another source should reuse the same normalized Home card and
  fullscreen presentation.

## Accepted Decisions

- Run Raspotify on the iMac as the unprivileged endpoint user and share its
  PulseAudio session with Chromium.
- Use repository-owned librespot event normalization instead of Spotify Web API
  polling or audio inference.
- Keep reporting best-effort so failures never stop audio.
- Keep fullscreen state local to Music and derive artwork colors in the
  browser without persisting them.
