# Lighting Roadmap

## Current

- [LGT-001](issues/LGT-001.md) pairs and supervises the Hue bridge through
  pinned `aiohue` with sanitized operational state.
- [LGT-002](issues/LGT-002.md) proves one exact observed scene action.
- [LGT-003](issues/LGT-003.md) generalizes the boundary to the uniquely named
  room scene catalog, aggregate activity, and deterministic keyboard cycling.
- Manual Hue controls remain bridge-native and independent.

## Next

- Add no new automatic authority until a module has a specific user flow and
  owns the outcome. Voice-controlled lighting is deferred while
  [VOI-004](../voice/issues/VOI-004.md) and its follow-on dialogue work
  establish natural interaction first.

## Later

- Additional device families or richer light controls if exact scenes stop
  covering useful room behavior.
- Home Assistant behind the normalized coordinator boundary if multiple device
  families justify its operational cost.

## Open Decisions

- Whether future modules need semantic lighting actions beyond exact scene
  activation.

## Accepted Decisions

- Keep the Hue bridge as device authority and use pinned `aiohue` behind one
  narrow adapter.
- Resolve the exact room `Rum` and expose only unique human-facing scene names.
- Complete scene actions only after later matching Hue observation.
- Preserve external Hue controls and avoid runtime remote-button ownership.
