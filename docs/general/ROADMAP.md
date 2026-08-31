# General Roadmap

## Current

Cortex Home runs as one integration repository with an always-on ThinkPad
coordinator, a provisioned iMac room endpoint, one explicit React channel shell,
local room integrations, and module-owned documentation.

[GEN-002](issues/GEN-002.md) replaced the former project-wide planning hierarchy
with this module-owned documentation and issue system.

| Module | Current state |
|---|---|
| [Platform](../platform/ROADMAP.md) | Coordinator and reproducible iMac endpoint are deployed |
| [Shell](../shell/ROADMAP.md) | Five explicit channels, shared feedback, and diagnostics |
| [Today](../today/ROADMAP.md) | Local clock and Linköping weather dashboard |
| [Music](../music/ROADMAP.md) | Spotify Connect playback and room-scale presentation |
| [Lighting](../lighting/ROADMAP.md) | Observed Hue scene catalog and exact scene actions |
| [Voice](../voice/ROADMAP.md) | Deliberate local and room speech paths with one-turn agent core |
| [Camera](../camera/ROADMAP.md) | Endpoint-local full-screen mirror |
| [AirPlay](../airplay/ROADMAP.md) | On-demand iPhone screen receiver |
| [Alarm](../alarm/ROADMAP.md) | One-shot wake alarm with endpoint sleep and local audio |

## Current Direction

- Improve the fluent Voice core before adding more room-agent permissions.
- Finish reviewer-owned physical confirmation recorded in active Shell and
  Alarm issues.
- Let each view evolve through its own roadmap without introducing a generic
  view registry or separate repository.
- Keep deployment and shared hardware testing serialized because every module
  uses the same physical room.

## Later

- Camera-assisted presence, deliberate gestures, and opt-in agent vision.
- Physical knobs, buttons, clap input, or wearable-assisted input.
- Photos, quotes, stocks, local media, and general video playback when their
  user flow and data boundary are clear.
- Additional device families if they justify a broader automation authority.

## Open Decisions

- Whether a future module gains an independently useful deployment lifecycle
  that justifies another repository or service boundary.
- Whether broader device support justifies placing Home Assistant behind the
  existing normalized coordinator actions.
- Whether future remote use justifies authentication and exposure beyond the
  home network.

## Accepted Decisions

- Keep one integration repository while the coordinator, client, endpoint, and
  physical room share one release and testing lifecycle.
- Keep the ThinkPad as state and coordination authority and the iMac as a
  replaceable presentation and nearby-media endpoint.
- Keep one explicit React shell with direct channel imports. Add no router,
  plugin registry, or dynamic channel discovery without a demonstrated need.
- Use a small coordinator as the shared boundary for product state and exact
  actions; integrations keep provider credentials and identifiers private.
- Keep AI interaction subordinate to explicit sensing, normalized context,
  allow-listed tools, and observed product state.
