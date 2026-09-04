# Shell

## Purpose

Shell is the stable room interface around one persistent Home surface. It owns
Home composition, entry into deliberate Camera and Music modes, keyboard
navigation, shared connection and action feedback, voice overlays, and
optional diagnostics.

## Experience

- Home should fill the display without browser or desktop chrome and stay
  useful without interaction.
- Temporary modes should have exact, trustworthy entry and exit behavior on
  the iMac.
- Shared connection, lighting, action, and voice feedback should remain visible
  without making each feature reimplement it.
- Keyboard actions should be exact, predictable, and scoped to the visible
  surface or mode.

## Boundaries

- Keep one explicit application shell and direct feature imports.
- Add no router, dynamic registry, plugin system, or generic widget framework
  until real summoned or draggable behavior requires it.
- Feature-owned presentation, logic, styles, and tests belong to the feature's
  source directory and documentation module.
- Shared overlays must not retain or expose provider content, speech content,
  camera frames, or host identity.

## Relevant Code

- `coordinator/client/src/app/`
- `coordinator/client/src/shared/`
- `coordinator/client/src/diagnostics/`
- `coordinator/client/src/voice/RoomFeedback.tsx`
