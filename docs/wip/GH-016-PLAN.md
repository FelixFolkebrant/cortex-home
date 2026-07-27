# GH-016 Plan: Answer One Contextual Follow-Up

# What

- Connect the existing press-bounded browser capture to one authenticated,
  in-memory coordinator interaction.
- Transcribe with the selected local recognizer, pass only the bounded
  transcript and normalized `agent.context` through a supervised Node Pi Agent
  Core child to one pinned OpenRouter text model, then synthesize and play one
  short answer through the existing endpoint route.
- Publish the exact content-free interaction phases and preserve request-ID
  cancellation from capture through playback.

## Out Of Scope

- Any tool call or Hue action; GH-018 owns exact scene activation.
- Conversation history, persistence, prompt or transcript logging, streaming
  speech, wake words, automatic turns, camera context, and concurrent turns.
- A new LAN service, provider-specific client state in coordinator code, or a
  runtime model-selection UI.

## Deferred

- Scene activation waits for GH-018 so the first answer path can prove the
  model, privacy, cancellation, and spoken-feedback boundaries without action
  authority.
- Interruption of already-started speech and multi-turn history wait until one
  full answer path has measured playback behavior.

## Acceptance Criteria

- [ ] Releasing the exact existing hold-to-speak shortcut sends one bounded WAV
  only to the authenticated coordinator, and raw audio never leaves the LAN or
  request lifetime.
- [ ] One interaction publishes `transcribing`, `thinking`, `speaking`, and
  `completed` or `failed` by request ID without transcript or response content.
- [ ] The coordinator uses the selected local Vosk recognizer and Pocket TTS
  synthesizer through their existing contracts.
- [ ] The supervised Node child uses Pi Agent Core and `pi-ai` with one pinned
  OpenRouter text model and receives only bounded text, normalized provider-free
  context, and its necessary configuration.
- [ ] The configured OpenRouter route enforces the accepted no-prompt-logging,
  no-data-collection, and Zero Data Retention requirements; credentials remain
  outside source control and client payloads.
- [ ] The agent produces at most one short answer; no tool schema or action
  authority is available in this issue.
- [ ] Cancellation, capture replacement, connection loss, child failure,
  invalid audio, transcription failure, provider failure, synthesis failure,
  and endpoint playback failure all become visible failures and cannot play or
  publish stale results.
- [ ] Coordinator, Node-child, frontend lifecycle, and relevant endpoint tests
  cover success and each bounded failure path without real credentials or model
  calls.

# Tasks

## 1. GH-016: Define The Ephemeral Interaction Protocol

- Add the authenticated request, content-free SSE phases, request ownership,
  and cancellation behavior around the existing speech contracts.
- This is atomic because it establishes the coordinator/client lifecycle before
  a model runtime can join it.

## 2. GH-016: Supervise The Answer Runtime

- Add the repository-owned Node child, Pi Agent Core and `pi-ai` adapter,
  bounded standard-stream protocol, protected configuration, and pinned model
  route with no tool capability.
- This is atomic because all model-provider behavior remains behind one child
  process boundary.

## 3. GH-016: Complete Spoken Answer Feedback

- Wire the frontend capture result, visible phases, synthesized response audio,
  endpoint playback, cancellation, and focused tests into one observed flow.
- This is atomic because it completes the accepted end-to-end interaction.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Content-Free, Cancellable Interaction Lifecycle

- Decision: The coordinator owns one request ID across capture submission,
  transcription, Pi turn, synthesis, playback, and all terminal failures.
- Proposed approach: Publish only enumerated phase and request identity; retain
  no audio, transcript, response, or conversation state and discard every late
  result after cancellation.
- Why: A private deliberate interaction must remain understandable and cannot
  allow stale speech or agent output to affect the current room state.
- Alternatives: Browser-owned orchestration; durable conversation state;
  uncorrelated asynchronous work; streamed content events.
- Review focus: cancellation races, logs, payload shapes, and cleanup of child
  and endpoint playback processes.

### H2 - Narrow Hosted Text Boundary

- Decision: Send only the current transcript and normalized context through a
  supervised Pi child to one policy-qualified OpenRouter route.
- Proposed approach: Keep credentials in deployment configuration, pin model
  and provider policy, cap input and answer sizes, and provide no tool schema.
- Why: The agent can answer a useful contextual follow-up without receiving raw
  audio, coordinator internals, device credentials, or action authority.
- Alternatives: Direct browser provider calls; coordinator-native model SDK;
  broad context; local model; tool-enabled first turn.
- Review focus: configuration handling, provider policy verification, strict
  message validation, and proof that no raw or durable content crosses the
  boundary.
