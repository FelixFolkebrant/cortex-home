# General Roadmap

## Current

Cortex Home runs as one integration repository with an always-on ThinkPad
coordinator, a provisioned iMac room endpoint, one explicit React Home shell,
local room integrations, and module-owned documentation.

[GEN-002](issues/GEN-002.md) replaced the former project-wide planning hierarchy
with this module-owned documentation and issue system.
[GEN-003](issues/GEN-003.md) makes the shared issue record shorter and restores an
optional heatmap for decisions that need focused review.
[GEN-004](issues/GEN-004.md) converted the coordinator agent and client source
tree, including React `.tsx` components, from JavaScript to TypeScript while
preserving the existing runtime boundaries.

| Module | Current state |
|---|---|
| [Platform](../platform/ROADMAP.md) | Coordinator and reproducible iMac endpoint are deployed |
| [Shell](../shell/ROADMAP.md) | Persistent Home, deliberate Music and Camera modes, shared feedback, and diagnostics |
| [Today](../today/ROADMAP.md) | Local clock and current Linköping weather on Home |
| [Music](../music/ROADMAP.md) | Spotify Connect playback, Home summary, and full-screen presentation |
| [Lighting](../lighting/ROADMAP.md) | Observed Hue scene catalog and exact scene actions |
| [Voice](../voice/ROADMAP.md) | One-turn local and room baseline; natural duplex dialogue is the active priority |
| [Camera](../camera/ROADMAP.md) | Endpoint-local feed-only full-screen mirror |
| [AirPlay](../airplay/ROADMAP.md) | Always-ready native iPhone screen receiver |
| [Alarm](../alarm/ROADMAP.md) | One-shot wake alarm, Home summary, endpoint sleep, and local audio |

## Current Direction

- Establish natural Voice dialogue with continuous active-session listening and
  barge-in before adding any room-agent permissions.
- Finish reviewer-owned physical confirmation recorded in active Shell and
  Alarm issues, including the Home redesign.
- Let Home regions and deliberate modes evolve through their owning roadmaps
  without introducing a generic widget registry or separate repository.
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
- Keep one explicit React Home shell with direct feature composition. Add no
  router, plugin registry, or dynamic discovery without a demonstrated need.
- Use a small coordinator as the shared boundary for product state and exact
  actions; integrations keep provider credentials and identifiers private.
- Keep AI interaction subordinate to explicit sensing, normalized context,
  allow-listed tools, and observed product state.
