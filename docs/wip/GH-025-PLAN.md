# GH-025 Plan: Interruptible Voice Turns

# What

- Make the existing deliberate voice interaction feel reliable as a repeated
  conversation: hold `Ctrl`+`Alt`+`Space` to speak, release to send, and press
  the same chord again to cancel any current capture, processing, download, or
  playback before starting the next utterance.
- Keep every turn independent. There is no retained conversation history,
  automatic turn detection, wake word, continuous listening, scene tool, or
  other room action in this issue.
- Qualify the complete iMac-to-ThinkPad-to-Sonos path, including cancellation
  during each active phase and immediate recovery with a new utterance.

## Acceptance Criteria

- [ ] The exact hold-to-speak chord starts capture only once, release ends the
  current capture, and every capture releases its microphone tracks.
- [ ] A fresh press during capture, transcription, thinking, answer download,
  or playback stops only the current request, suppresses late output, and
  starts the new capture once coordinator cancellation has settled.
- [ ] Browser, coordinator, and child-process cancellation use the same request
  ID; stale phases, audio, and terminal responses cannot replace the later
  interaction.
- [ ] Visible feedback distinguishes listening, transcribing, thinking,
  speaking, cancellation, failure, and readiness without showing transcript,
  answer, provider, or audio content.
- [ ] The answer-only Pi route, local speech processing, privacy routing, and
  no-persistence boundary remain unchanged.
- [ ] Automated browser and coordinator tests cover rapid replacement,
  cancellation during every phase, endpoint reconnect, late results, and one
  successful turn after each cancellation.
- [ ] A physical iMac pass proves at most 60-second samples of normal response,
  interruption during thinking and playback, immediate next-turn recovery, and
  intelligible Sonos playback.

# Tasks

## 1. GH-025: Make Replacement Deterministic

- Trace the current `VoiceCapture`, `SpokenInteraction`, and coordinator
  request-ID ownership paths. Tighten only races found between a fresh keydown,
  capture release, HTTP abort, DELETE cancellation, and a late SSE or audio
  response.
- Keep one active interaction globally. A new press is never queued and never
  overlaps an earlier microphone or playback session.

## 2. GH-025: Prove Phase-Correct Interruption

- Add focused tests around the browser replacement sequence and coordinator
  cancellation propagation. Preserve the existing process-group abort in the
  Node runtime and reject all late results by request ID.

## 3. GH-025: Qualify The Room Conversation Loop

- Deploy the focused change and complete the physical iMac/ThinkPad/Sonos pass.
  Record only phase outcomes, device-selection facts, and content-free errors.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - One New Press Owns The Next Turn

- Decision: Do not overlap, queue, or resume voice sessions.
- Why: Immediate interruption must never allow stale audio or an older answer
  to take over after the user starts speaking again.
- Alternatives: Parallel turns; queued utterances; hands-free barge-in; keeping
  the microphone open between turns.

### H2 - Deliberate Sensing Stays Intact

- Decision: Keep the fixed hold-to-speak chord and explicit release boundary.
- Why: A conversational feel does not require ambient capture, and deliberate
  microphone ownership remains the accepted privacy baseline.
- Alternatives: Wake word; voice activity detection; automatic silence timeout;
  always-on microphone.
