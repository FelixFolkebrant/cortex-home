# Voice

## Purpose

Voice provides private, natural spoken dialogue with Cortex Home. Once a person
explicitly activates a session, Cortex Home listens continuously, responds
promptly, and yields immediately when the person starts speaking again. The
ThinkPad remains authoritative for room state and future actions.

## Experience

- A clearly visible, explicitly activated voice session keeps listening until
  the person ends it, the endpoint disconnects, or a bounded idle policy ends
  it. There is no wake word or background listening outside that session.
- Local turn detection separates speech, short pauses, and an end of turn
  without requiring the person to hold a key for each utterance.
- The assistant retains only the active session's bounded conversation context,
  so a follow-up can refer naturally to the immediately preceding exchange.
- Assistant speech begins as soon as a useful response segment is available.
  When the person speaks over it, Cortex Home stops the current response and
  playback, then listens to the interruption as the next turn.
- The display dims Home during a session. A small red/orange sun bobs calmly
  while a centered bar expresses microphone level; a larger yellow sun follows
  synthesized playback level while the agent speaks. After an answer it returns
  to listening, with subtitles retained for ephemeral turn content.
- The same dialogue core can run through the iMac room endpoint and a local
  IdeaPad development workbench.

## Current Components

- Harness: Pi Agent Core in a coordinator-supervised Node dialogue process.
- Speech-to-text: local Vosk, selected through qualification against
  `whisper.cpp` for the former one-turn path.
- Text-to-speech: local Pocket TTS, selected through qualification against
  Piper for the former one-turn path.
- Language model: one pinned OpenRouter model and provider route behind a
  repository-owned adapter.

## Boundaries

- Microphone capture is visible and allowed only for an explicit active voice
  session. No wake word or inactive background capture is allowed.
- Raw and synthesized audio remain on local hardware and the home network.
  Only bounded text and the active session's normalized context may reach the
  selected model provider.
- Do not persist or log recordings, partial or final transcripts, answers,
  conversation history, tool arguments, or provider content. Active-session
  state exists in memory only and is discarded when its session ends.
- Models receive no credentials, provider objects, camera frames, shell access,
  browser control, or direct device access.
- Tool calls and other room authority remain deferred until natural dialogue,
  interruption, privacy, and recovery are trustworthy.
- Natural dialogue continues to use the Pi Agent Core harness. Its active
  session, streaming, and cancellation lifecycle remains coordinator-supervised
  rather than becoming a separate agent service.
- The IdeaPad workbench runs the same voice path: browser capture, selected
  local speech engines, Pi dialogue child, and selected real provider. It may
  use deterministic room observations where no room hardware is present, but
  it must never replace voice behavior or provider responses with canned,
  simulated output. An unavailable required dependency fails clearly instead.
- Keep speech engines, turn detection, model selection, context projection,
  and future tool authority replaceable without coupling Home presentation to
  a provider.

## Relevant Code

- `coordinator/speech.py`
- `coordinator/context.py`
- `coordinator/agent/`
- `coordinator/local_voice.py`
- `coordinator/client/src/voice/`
