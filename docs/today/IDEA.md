# Today

## Purpose

Today is the default room dashboard: a quiet, readable glance at local time,
date, and near-term weather for Linköping.

## Experience

- Show the current local time and date at room-viewing scale.
- Show current conditions and a three-day forecast without turning the view
  into a dense weather application.
- Keep provider attribution visible and the unavailable state honest.
- Remain useful as the default screen without requiring interaction.

## Boundaries

- Only the ThinkPad contacts the weather provider.
- The browser receives normalized conditions rather than provider payloads,
  cache metadata, or unnecessary location detail.
- Weather failure must not affect other channels, lighting, voice, or service
  health.
- The module owns presentation and weather semantics, not shell navigation.

## Relevant Code

- `coordinator/today.py`
- `coordinator/client/src/channels/today/`
