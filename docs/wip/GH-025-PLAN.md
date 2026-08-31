# GH-025 Plan: Interruptible Voice Turns

# What

- Turn the existing IdeaPad-only local voice workbench into a repeated,
  terminal-first conversation loop: start one deliberate utterance, hear one
  local answer, interrupt recording, thinking, or playback, then immediately
  begin the next utterance without restarting the program.
- Keep every turn independent. There is no retained conversation history,
  automatic turn detection, wake word, continuous listening, scene tool, or
  other room action in this issue.
- Keep every dependency local to the IdeaPad except the existing text-only
  OpenRouter request. Do not start or contact the Cortex Home coordinator,
  iMac, ThinkPad, Sonos, Hue bridge, browser, or deployment configuration.

## Acceptance Criteria

- [ ] One documented IdeaPad command stays open for repeated deliberate turns;
  it starts no home service and retains no audio, transcript, answer, or
  conversation state between turns.
- [ ] Enter starts the next bounded capture only while the terminal is ready.
  `Ctrl`+`C` during capture, transcription, thinking, synthesis, or playback
  cancels only that turn, releases local resources, and returns to readiness.
- [ ] A fresh turn after every cancellation receives a new request ID, ignores
  all late local results, and can complete with intelligible local playback.
- [ ] The terminal shows only ready and lifecycle phases plus content-free
  terminal errors; it never prints recognized or provider content.
- [ ] The answer-only Pi route, local speech processing, privacy routing, and
  no-persistence boundary remain unchanged.
- [ ] Automated tests cover repeated turns, interruption during every local
  phase, late-result rejection, device release, and recovery without
  credentials, network, or hardware.
- [ ] A manual IdeaPad pass proves normal response, interruption during
  thinking and playback, immediate next-turn recovery, and intelligible local
  playback in samples no longer than 60 seconds.

# Tasks

## 1. GH-025: Add A Persistent Local Turn Loop

- Refactor `local_voice.py` around a small terminal runner that waits for Enter
  before each turn and returns to readiness after every terminal outcome.
- Keep one active local turn. `Ctrl`+`C` cancels it in place; EOF exits cleanly.
  No turn is queued, resumed, or allowed to overlap its successor.

## 2. GH-025: Prove Phase-Correct Local Interruption

- Add focused runner tests around input waiting, cancellation during every
  component phase, resource release, late results, and a successful next turn.
  Preserve the existing local process-group aborts and request-ID checks.

## 3. GH-025: Qualify The IdeaPad Conversation Loop

- Run the local command on the IdeaPad. Record only phase outcomes,
  device-selection facts, and content-free errors. A later issue will port this
  proven interaction model to the room path.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - One Local Turn Owns The Next Turn

- Decision: Do not overlap, queue, or resume local voice turns.
- Why: Interruption must never allow stale audio or an older answer to take over
  after the user begins the next utterance.
- Alternatives: Parallel turns; queued utterances; hands-free barge-in; keeping
  a microphone open between turns.

### H2 - Local Deliberate Sensing Stays Intact

- Decision: Keep explicit terminal start and cancellation controls.
- Why: A conversational local workbench does not require ambient capture, and
  the microphone remains owned by one visible foreground turn.
- Alternatives: Wake word; voice activity detection; automatic silence timeout;
  always-on microphone.
