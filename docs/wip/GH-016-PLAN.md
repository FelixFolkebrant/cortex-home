# GH-016 Plan: Answer One Contextual Follow-Up

## What

- Connect the existing press-bounded browser capture to one authenticated,
  in-memory coordinator interaction.
- Transcribe with the selected local Vosk recognizer, pass only the bounded
  transcript and a fresh normalized `agent.context` snapshot through one
  supervised Pi Agent Core child to a pinned OpenRouter text route, then
  synthesize and play one short answer through the existing Chromium and Sonos
  route.
- Publish content-free interaction phases by the capture request ID and let a
  later press, connection loss, or explicit cancellation stop every unfinished
  stage and discard late results.
- Provision only the selected production speech engines and the pinned Node,
  Pi, model, and protected credential configuration needed by this path.

### Interaction Contract

- `POST /api/agent/interactions/<request-id>` accepts only the endpoint token
  and the exact bounded `audio/wav` body established by GH-014. It returns only
  the synthesized `audio/wav` or a content-free structured failure.
- `DELETE /api/agent/interactions/<request-id>` cancels the matching endpoint
  interaction. A later hold-to-speak press cancels current processing or
  playback before it owns a new request ID.
- `POST /api/agent/interactions/<request-id>/status` lets the authenticated
  endpoint report playback start, completion, or failure.
- `agent.interaction` SSE events contain only `requestId` and one of
  `transcribing`, `thinking`, `speaking`, `completed`, or `failed`.

## Out Of Scope

- Any tool definition, tool call, or Hue action; GH-018 owns exact scene
  activation.
- Conversation history, persistence, prompt or transcript logging, streamed
  tokens or speech, wake words, automatic turns, camera context, and concurrent
  turns.
- A new LAN service, provider-specific client state in coordinator code,
  general runtime/model selection, or reusable process/plugin infrastructure.
- Automatic retries, fallback models, and fallback providers.

## Deferred

- Scene activation waits for GH-018 so the first answer path can prove the
  model, privacy, cancellation, and spoken-feedback boundaries without action
  authority.
- Mid-speech barge-in semantics and spoken-prefix history reconciliation remain
  deferred. GH-016 still stops current playback immediately when its request is
  cancelled; it does not remember how much was heard.
- Broader model comparison waits until the pinned lightweight candidate has
  measured contextual quality, full-turn latency, cost, and failure behavior.

## Acceptance Criteria

- [ ] Releasing exact `Ctrl`+`Alt`+`Space` sends one 16 kHz mono signed 16-bit
  PCM WAV only to the coordinator with the active SSE endpoint token; raw audio
  never leaves the LAN or interaction lifetime.
- [ ] The coordinator accepts only one interaction, validates the existing
  15-second WAV bound before recognition, takes one fresh immutable
  `agent.context` snapshot, and publishes only the exact content-free phases.
- [ ] The production service loads Vosk `0.3.45` with
  `vosk-model-small-en-us-0.15` and Pocket TTS `2.1.0` with English `alba`
  through the existing `Recognizer` and `Synthesizer` contracts. Qualification
  candidates do not become runtime selection.
- [ ] One repository-owned Node child is spawned per interaction, receives one
  strictly bounded request over private standard streams, returns one bounded
  result, and is terminated on cancellation, timeout, malformed output, or
  parent shutdown. No child state survives the interaction.
- [ ] The child pins Node `24.18.0`,
  `@earendil-works/pi-agent-core` `0.82.1`, and
  `@earendil-works/pi-ai` `0.82.1`; its Pi state has no tools, history,
  follow-ups, retries, or reasoning output and produces at most one
  synthesis-safe short answer.
- [ ] Model qualification starts with
  `google/gemini-3.5-flash-lite` and pins it only after representative Today and
  Music questions confirm context grounding, concise answers, acceptable
  end-to-end latency and cost, and predictable refusal or provider failure.
- [ ] Every OpenRouter request disables provider fallback, denies data
  collection, requires Zero Data Retention routing, and uses only the accepted
  provider route. Input/output logging and data-discount use remain disabled
  for the dedicated key.
- [ ] The OpenRouter key exists only in root-owned deployment configuration,
  reaches only the coordinator-owned child environment, and never appears in
  source control, installer output, client payloads, standard-stream messages,
  SSE events, or application logs.
- [ ] Chromium plays only the WAV returned for its current request, reports
  playback start and terminal status, and immediately stops and revokes audio
  for a cancelled or replaced request.
- [ ] Capture replacement, connection loss, invalid audio, empty or failed
  transcription, child startup/exit/timeout/protocol failure, provider failure,
  invalid answer, synthesis failure, and endpoint playback failure all become
  visible `failed` states without publishing content or allowing stale output.
- [ ] Coordinator, child protocol, frontend lifecycle/playback, production
  installation, and relevant endpoint tests cover success, cancellation races,
  and each bounded failure without real credentials, provider calls, or
  retained audio.
- [ ] A deployed manual pass confirms Today and Music context, phase feedback,
  spoken Sonos output, cancellation during each processing phase and playback,
  recovery after failure, keyboard-only operation, and readable responsive
  states.

## Tasks

### 1. GH-016: Add The Ephemeral Pi Answer Child

- Add the exact Node and Pi package pins, reviewed no-tools system prompt, one
  request/response standard-stream schema, OpenRouter route controls, output
  bounds, timeout and signal handling, and a fake-provider child test harness.
- This is atomic because it proves one isolated text turn without changing the
  coordinator, browser, or deployment.

### 2. GH-016: Own The Agent Interaction Lifecycle

- Add the authenticated WAV, cancellation, and playback-status endpoints; one
  coordinator-owned interaction state machine; selected recognizer,
  synthesizer, and child adapters; exact SSE phases; and stale-result cleanup.
- Return synthesized WAV directly to the owning request instead of sending
  transcript, response text, or audio through SSE.
- This is atomic because it establishes the complete server-side lifecycle and
  privacy boundary behind fake speech and model collaborators.

### 3. GH-016: Complete Spoken Answer Feedback

- Submit the captured WAV, render transcribing through terminal feedback, play
  only the current returned WAV, report playback status, and make a later press,
  blur, reconnection, unmount, or playback error cancel every owned resource.
- Add focused frontend tests for success, every visible failure, replacement,
  late events, playback stop, keyboard behavior, and responsive/live-region
  presentation.
- This is atomic because it connects the already qualified capture and audio
  route to the accepted server lifecycle.

### 4. GH-016: Provision The Pinned Answer Runtime

- Extend the production installer and systemd unit with the selected Vosk and
  Pocket TTS dependencies and artifacts, the checksum-verified Node 24 LTS
  runtime, the locked child package, root-owned OpenRouter configuration, and
  startup validation that fails before serving when a required pin or secret is
  absent.
- Verify the current ZDR-qualified route, perform the bounded model and
  full-turn room checks, and record exact reconstruction commands and measured
  evidence in `GH-016.md` without recording prompts, transcripts, answers,
  credentials, host identity, or raw logs.
- This is atomic because it turns the tested interaction into one reproducible
  production deployment without preserving qualification-only switching.

## Heatmap

Reference: `../project/HEATMAP.md`.

### Hot

#### H1 - One Request Owns The Whole Cancellable Lifecycle

- Decision: The capture request ID and current endpoint token own submission,
  transcription, one Pi child, synthesis, playback, and the terminal phase.
- Proposed approach: Keep one coordinator state machine, abort and explicitly
  cancel from the client, terminate the per-request child, stop current browser
  audio, and ignore every late result or event after ownership changes.
- Why: A private deliberate interaction must remain understandable and cannot
  let stale speech or agent output affect the current room.
- Alternatives: Browser-owned orchestration; one ID per stage; a persistent Pi
  session; overlapping interactions; streamed content events.
- Review focus: replacement and disconnect races, terminal-state idempotency,
  child cleanup, response disconnects, browser audio cleanup, and absence of
  retained content.

#### H2 - Keep The Hosted Boundary Explicitly Narrow

- Decision: Send only one bounded transcript and normalized context snapshot
  to one pinned model/provider route with no tool or retry authority.
- Proposed approach: Begin qualification with
  `google/gemini-3.5-flash-lite`, keep the prompt and bounds in reviewed child
  code, disable reasoning and fallbacks, and enforce both `zdr: true` and
  `data_collection: "deny"` on every request.
- Why: The agent can answer a useful contextual follow-up without receiving raw
  audio, coordinator internals, device credentials, arbitrary history, or
  action authority.
- Alternatives: Direct browser calls; coordinator-native provider SDK; broad
  context; local model; dynamic routing; tool-enabled first turn.
- Review focus: effective request payload, provider and account policy,
  configuration handling, answer validation, qualification evidence, and proof
  that only bounded text crosses the hosted boundary.

#### H3 - Use A Per-Interaction Child As The Retention Boundary

- Decision: Spawn a fresh Node child for each accepted interaction instead of
  keeping a stateful Pi process alive.
- Proposed approach: Give the child one request on standard input, allow one
  result on standard output, keep standard error content-free, and terminate
  the process group on cancellation or timeout.
- Why: Process lifetime makes no-history behavior, crash recovery, and
  cancellation observable without inventing reset or multiplexing protocols.
- Alternatives: Persistent supervised child; in-process Python provider call;
  second LAN service; reusable worker pool.
- Review focus: cold-start cost, process-tree termination, pipe bounds, exit
  handling, credential exposure, and the absence of inherited conversation
  state.
