# Cortex Home Documentation

Documentation follows the product modules. Start with a module's `IDEA.md` to
understand what it should be, then read `ROADMAP.md` for what exists now and
what may happen next. Completed work lives in `issues/`; active work lives in
`wip/`.

| Module | Prefix | Documents | Responsibility |
|---|---|---|---|
| General | `GEN` | [Idea](general/IDEA.md) · [Roadmap](general/ROADMAP.md) | Product-wide intent, workflow, and cross-module work |
| Platform | `PLT` | [Idea](platform/IDEA.md) · [Roadmap](platform/ROADMAP.md) | ThinkPad coordinator, iMac endpoint, deployment, and hardware |
| Shell | `SHL` | [Idea](shell/IDEA.md) · [Roadmap](shell/ROADMAP.md) | Home composition, deliberate modes, shared feedback, and diagnostics |
| Today | `TOD` | [Idea](today/IDEA.md) · [Roadmap](today/ROADMAP.md) | Clock, date, weather state, and the Home weather region |
| Music | `MUS` | [Idea](music/IDEA.md) · [Roadmap](music/ROADMAP.md) | Spotify receiver, playback state, and Music presentation |
| Lighting | `LGT` | [Idea](lighting/IDEA.md) · [Roadmap](lighting/ROADMAP.md) | Hue connection, observed scenes, and room-light actions |
| Voice | `VOI` | [Idea](voice/IDEA.md) · [Roadmap](voice/ROADMAP.md) | Speech capture, agent turns, tools, synthesis, and interruption |
| Camera | `CAM` | [Idea](camera/IDEA.md) · [Roadmap](camera/ROADMAP.md) | Deliberate local feed-only camera mirror |
| AirPlay | `AIR` | [Idea](airplay/IDEA.md) · [Roadmap](airplay/ROADMAP.md) | Always-ready iPhone screen mirroring and native composition |
| Alarm | `ALA` | [Idea](alarm/IDEA.md) · [Roadmap](alarm/ROADMAP.md) | Scheduling, endpoint sleep and wake, alarm audio, and dismissal |

The lightweight issue process and naming rules live in
[WORKFLOW.md](general/WORKFLOW.md).

## Design Guidelines

The design language is deliberately minimal while it is still evolving.

- Show as little information as the interaction needs.
- Do not explain controls the sole user already knows.
- Treat Home as one calm surface. Temporary modes and summoned tools should
  reveal themselves through their content instead of permanent labels.
