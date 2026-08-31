# Lighting

## Purpose

Lighting lets Cortex Home observe and request meaningful room scenes while the
Philips Hue bridge remains the device and automation authority.

## Experience

- Show whether lighting is unavailable, custom, one named scene, or multiple
  matching scenes.
- Let a deliberate caller activate one exact scene name and report success only
  after Hue observes it active.
- Preserve the Hue app, existing Hue remote, switches, and ordinary lighting
  behavior when Cortex Home is unavailable.

## Boundaries

- Keep Hue credentials, bridge identity, resource IDs, raw events, and library
  objects inside the adapter.
- Expose normalized scene names and state rather than provider identifiers.
- Keep exact scene actions independent of endpoint availability.
- Do not add broad light controls, arbitrary device access, or duplicate Hue
  remote behavior without a concrete flow.

## Relevant Code

- `coordinator/hue.py`
- `coordinator/hue_pair.py`
- `coordinator/context.py`
