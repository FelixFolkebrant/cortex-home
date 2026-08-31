# Voice Roadmap

## Current

- [VOI-001](issues/VOI-001.md) publishes fresh provider-free Today, Music, and
  Lighting context for agents.
- [VOI-002](issues/VOI-002.md) qualifies deliberate browser capture, local
  Vosk recognition, local Pocket TTS synthesis, and the shared Sonos route.
- [VOI-003](issues/VOI-003.md) connects one ephemeral room turn to Pi Agent
  Core and a pinned OpenRouter route. Some provider, responsive, and deployed
  reviewer checks remain recorded in that issue.
- [VOI-005](issues/VOI-005.md) extracts the one-turn core and proves it in a
  laptop-only local workbench with one simulated tool.
- [VOI-006](issues/VOI-006.md) makes the local workbench repeatable and rejects
  cancelled or late phase results. Its physical interruption checks remain
  useful input to the next fluency pass.
- [VOI-004](wip/VOI-004.md) is the next room integration: one exact Hue scene
  tool through coordinator-owned validation and observed completion.

## Next

- Complete VOI-004 without expanding beyond zero or one exact scene request.
- Qualify the outstanding physical interruption, latency, provider-policy,
  narrow-layout, and recovery behavior already identified by VOI-003 and
  VOI-006.
- Improve turn fluency only from measured bottlenecks; keep model, speech, and
  playback changes separate enough to compare honestly.

## Later

- Mid-speech interruption and conversational history only after one-turn
  cancellation and privacy behavior are trustworthy.
- Additional allow-listed room actions one concrete user flow at a time.
- Wake words, proactive initiation, or ambient sensing only with a separately
  accepted privacy and feedback model.
- Camera context only through deliberate opt-in work; never infer it from the
  existence of the Camera channel.
- Reconsider a fully local language model after hosted latency, cost, quality,
  and privacy have been measured.

## Open Decisions

- Which measured change most improves perceived room-turn latency.
- Whether future multi-turn interaction can remain useful without durable
  conversation history.
- What user-visible permission model is required before a second room action.

## Accepted Decisions

- Use deliberate hold-to-speak and show every sensing and processing phase.
- Run speech processing locally and keep raw audio off the internet.
- Use Pi Agent Core behind a private request-ID-keyed child protocol and a
  pinned OpenRouter model/provider/privacy payload.
- Send only current normalized context and retain no conversation content.
- Permit at most one strict tool request per turn and route it through the
  coordinator rather than giving the model direct integration access.
- Keep room and laptop modes as compositions of the same replaceable core.
