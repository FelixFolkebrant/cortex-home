# Shell

## Purpose

Shell is the stable room interface surrounding every channel. It owns which
view is active, direct channel composition, keyboard navigation, shared
connection and action feedback, voice overlays, and optional diagnostics.

## Experience

- The selected channel should fill the display without browser or desktop
  chrome.
- Channel changes should be immediate and trustworthy on the iMac rather than
  visually ambitious but laggy.
- Shared connection, lighting, action, and voice feedback should remain visible
  without making each channel reimplement it.
- Keyboard actions should be exact, predictable, and scoped to the active view.

## Boundaries

- Keep one explicit application shell and direct channel imports.
- Add no router, dynamic registry, plugin system, configurable channel order,
  or generic widget framework until real behavior requires it.
- Channel-owned presentation, logic, styles, and tests belong to the channel's
  source directory and documentation module.
- Shared overlays must not retain or expose provider content, speech content,
  camera frames, or host identity.

## Relevant Code

- `coordinator/client/src/app/`
- `coordinator/client/src/shared/`
- `coordinator/client/src/diagnostics/`
- `coordinator/client/src/voice/RoomFeedback.jsx`
