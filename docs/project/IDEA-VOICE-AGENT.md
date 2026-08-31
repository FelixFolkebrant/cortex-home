# Voice Agent

This document is the highest source of truth for voice-agent development.

The goal is to replicate ChatGPT voice mode or a similar voice agent. Its core
components are speech-to-text, text-to-speech, and an agent harness.

- Harness: Pi.
- Speech-to-text: Vosk.
- Text-to-speech: selectable Pocket TTS and Piper TTS. Piper provides the
  lower-hardware option with lower voice quality.
- Language model: hot-swappable through the OpenRouter API.

The agent must support two deployment modes:

- Room mode records and plays speech through the iMac while the ThinkPad
  homelab performs speech and agent processing.
- Laptop mode runs microphone capture, playback, speech processing, and the
  agent on the IdeaPad.

Build a general harness that can later gain skills and control homelab features
such as music and lighting. Those integrations come only after the core
speech-to-text, text-to-speech, and interruption loop works fluently.
