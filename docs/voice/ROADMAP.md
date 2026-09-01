# Voice Roadmap

## Current

- [VOI-001](issues/VOI-001.md) publishes fresh provider-free Today, Music, and
  Lighting context for agents.
- [VOI-002](issues/VOI-002.md) qualifies deliberate browser capture, local
  Vosk recognition, local Pocket TTS synthesis, and the shared Sonos route.
- [VOI-003](issues/VOI-003.md) connects one ephemeral room turn to Pi Agent
  Core and a pinned OpenRouter route. Its answer-only room checks remain useful
  baseline evidence, not proof of natural dialogue.
- [VOI-005](issues/VOI-005.md) extracts the one-turn core and proves it in a
  laptop-only local workbench with one simulated tool.
- [VOI-006](issues/VOI-006.md) makes the local workbench repeatable and rejects
  cancelled or late one-turn results.
- [VOI-004](issues/VOI-004.md) establishes explicit browser voice sessions,
  provisional local turn detection, and endpoint-bound turn epochs. Its
  IdeaPad path is repeatable through the local development room.

## Next

- Complete VOI-007 (stream Pi dialogue), then VOI-008 (barge-in and room
  qualification), before adding any room-agent tools or other authority.
- Evolve VOI-004's explicit session, local capture, and epoch ownership into
  bounded ephemeral Pi dialogue, streamed response speech, and interruption.
- Measure end-to-end turn and barge-in latency on the actual IdeaPad and room
  hardware. Improve only measured bottlenecks.
- Qualify privacy, recovery, narrow-layout, and keyboard behavior for a live
  session rather than reusing one-turn evidence as a proxy.

## Later

- Additional allow-listed room actions only after natural dialogue and its
  interruption behavior are trustworthy.
- Wake words, proactive initiation, or capture outside an explicitly active
  session only with a separately accepted privacy and feedback model.
- Camera context only through deliberate opt-in work; never infer it from the
  existence of the Camera channel.
- Reconsider a fully local language model after hosted latency, cost, quality,
  and privacy have been measured.

## Open Decisions

- Which detector calibration works reliably against the room's real microphone,
  speakers, and acoustic echo.
- Which measured change most improves perceived response and barge-in latency.
- What bounded active-session context preserves useful follow-ups without
  retaining private conversation after the session ends.

## Accepted Decisions

- Natural dialogue is the Voice module's highest priority; tools and other
  room authority are deferred.
- Listening may be continuous only while the person has explicitly activated a
  visible session. There is no wake word or inactive background listening.
- Barge-in is a first-class interaction: detected user speech cancels current
  model work and assistant playback, and stale output must never resume.
- Continue with Pi Agent Core as the dialogue harness; evolve its current fresh
  child protocol into a coordinator-supervised active-session protocol.
- Run speech processing locally and keep raw audio off the internet.
- Send only bounded text, current normalized context, and bounded ephemeral
  active-session history to the selected model provider.
- Keep room and laptop modes as compositions of the same replaceable dialogue
  core.
