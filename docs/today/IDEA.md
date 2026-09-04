# Today

## Purpose

Today supplies the quiet time, date, and current-weather regions of Home.

## Experience

- Show the current local time and date at room-viewing scale.
- Show current conditions without forecast, location detail, or provider text
  competing with the room-scale clock.
- Keep unavailable state honest without replacing the rest of Home.
- Remain useful without requiring interaction.

## Boundaries

- Only the ThinkPad contacts the weather provider.
- The browser receives normalized conditions rather than provider payloads,
  cache metadata, or unnecessary location detail.
- Weather failure must not affect other Home regions, lighting, voice, or
  service health.
- The module owns weather semantics and its Home region, not shell composition.

## Relevant Code

- `coordinator/today.py`
- `coordinator/client/src/app/HomeSurface.tsx`
