# Voice

## Purpose

Voice provides deliberate, private spoken interaction with Cortex Home. It
combines local speech processing with a replaceable language-model boundary
while the coordinator remains authoritative for room state and actions.

## Experience

- A held shortcut records one bounded utterance and visibly reports listening,
  transcribing, thinking, acting, speaking, completion, or failure.
- One turn may answer from fresh normalized room context or request one
  explicitly allowed room action.
- The same core can run as a room interaction through the iMac or as a local
  development workbench on the IdeaPad.
- Cancellation should stop current work promptly, reject late results, and
  leave the next turn clean.

## Current Components

- Harness: Pi Agent Core in a coordinator-supervised Node child.
- Speech-to-text: local Vosk, selected through qualification against
  `whisper.cpp`.
- Text-to-speech: local Pocket TTS, selected through qualification against
  Piper.
- Language model: one pinned OpenRouter model and provider route behind a
  repository-owned adapter.

## Boundaries

- Microphone capture is deliberate, bounded, and visible. There is no wake
  word or continuous listening.
- Raw and synthesized audio remain local. Only bounded text and normalized
  context may reach the selected model provider.
- Do not persist or log recordings, transcripts, answers, conversation state,
  tool arguments, or provider content.
- Models receive no credentials, provider objects, camera frames, shell access,
  browser control, or direct device access.
- Every tool is narrow, validated again by the coordinator, and considered
  successful only from observed product state.
- Keep speech engines, model selection, context projection, and tool authority
  replaceable without coupling channels to a provider.

## Relevant Code

- `coordinator/speech.py`
- `coordinator/context.py`
- `coordinator/agent/`
- `coordinator/local_voice.py`
- `coordinator/client/src/voice/`
