# PP-4: Deliberate Voice Agent Interaction

## Slice

Holding one fixed keyboard shortcut lets the user ask a short question about
the visible Today or Music channel, hear one spoken answer, and activate one
exact detected Hue scene through the same coordinator action used by other
callers.

- The USB-connected Anker PowerConf S330 microphone is deliberately activated
  from the iMac keyboard and is never sampled while the shortcut is not held.
- The iMac captures one bounded utterance and shows listening, transcribing,
  thinking, acting, speaking, success, and failure state.
- The ThinkPad transcribes English speech and synthesizes speech locally behind
  two small replaceable backend boundaries.
- A local Node process runs Pi Agent Core and sends only text and normalized
  room context through `pi-ai` to one pinned OpenRouter text model.
- The model may answer or request one exact named-scene action. The coordinator
  remains responsible for validation, execution, observed completion, and
  failure.
- Audio, transcripts, responses, and conversation state are not persisted by
  Cortex Home.

This is the smallest useful voice slice because it proves deliberate sensing,
context, local speech processing, one constrained tool, and visible feedback
without creating an ambient or general-purpose assistant.

## Out Of Scope

- Wake words, continuous listening, automatic turn detection, background
  recording, proactive initiation, or camera input for the agent. Planpoint 5's
  separately selected local Camera mirror does not provide frames or context to
  this slice.
- General conversation memory, user profiles, embeddings, retrieval, web
  search, files, email, calendar, or personal account data.
- Arbitrary coordinator actions, shell access, browser control, dynamic tool
  discovery, MCP, computer use, or administrative tools.
- Multiple tool calls, parallel tools, action planning, autonomous retries, or
  actions that were not explicitly requested in the current utterance.
- Streaming speech-to-speech, automatic voice activity detection, mid-speech
  barge-in, overlapping voice sessions, or multi-room audio.
- Making channel implementations depend on the selected model provider.
- Guaranteeing that concurrent Planpoint 5 channels are agent-aware before a
  later integration issue explicitly adds their context.

## Deferred To Later Planpoints

- Wake words and ambient sensing remain deferred because deliberate
  hold-to-speak must first establish a trustworthy privacy and feedback
  baseline.
- Conversation memory remains deferred because one contextual turn does not
  need durable history.
- More room actions remain deferred until exact scene activation demonstrates
  that model-requested actions remain understandable and predictable.
- A local language model remains replaceable behind the adapter and should be
  reconsidered only after measured hosted latency, cost, and privacy tradeoffs
  exist.
- Mid-speech interruption remains deferred until the first spoken turn is
  qualified. Every interaction is still identified and cancellable so a later
  press can stop playback, abort unfinished work, reject stale output, and
  record that the assistant response was interrupted rather than heard in full.
- Agent understanding of Camera and future channels remains explicit follow-up
  work so channel delivery does not block this slice.

## Crossroads

### C1 - Agent Runtime And Reasoning Boundary

- Decision: Whether the first agent uses a harness, a general automation
  runtime, a local model, a realtime speech model, or one small adapter around a
  text reasoning API.
- Options: OpenAI Agents SDK; Home Assistant conversation agent; LangChain or a
  similar framework; Pi Agent Core; hosted realtime speech-to-speech; a
  repository-owned Python model loop; a fully local model.
- Impact if wrong: The choice controls action authority, context ownership,
  provider coupling, conversation state, observability, and how later models
  are replaced.
- Proposed choice: Run `@earendil-works/pi-agent-core` with `pi-ai` in one
  repository-owned Node child process supervised by the Python coordinator.
  Route text reasoning through OpenRouter, pin one qualified lightweight model
  per deployment, and begin model qualification with Gemini Flash Lite. Keep
  prompts and tool definitions in reviewed repository code.
- Why: Pi provides explicit conversation state, streaming events, cancellation,
  tool validation hooks, and a provider-neutral model boundary that later
  integrations can reuse. OpenRouter keeps model selection independent from
  the harness. Accepting a Node runtime is preferable to replacing those
  lifecycle boundaries later, while a coordinator-owned child process avoids a
  second LAN service or public context endpoint. Realtime audio is unnecessary
  for the accepted press-bounded speech cascade.
- Status: decided

### C2 - Speech Processing And Capture Boundary

- Decision: Where microphone capture, transcription, and speech synthesis run.
- Options: Hosted speech-to-speech; hosted transcription and synthesis; local
  processing on the iMac; browser capture with local ThinkPad transcription and
  synthesis; a dedicated endpoint capture daemon.
- Impact if wrong: Raw room audio could leave the home, the iMac could inherit
  unacceptable compute, or the system could require a second endpoint protocol.
- Proposed choice: Capture one press-bounded PCM utterance in Chromium from the
  USB-connected Anker PowerConf S330 and send it only to the ThinkPad. Qualify
  English Vosk against quantized `whisper.cpp`, and Piper against Pocket TTS, on
  the actual Ryzen 5 host and microphone path. Put each role behind one small
  backend contract, pin the measured winners, and return bounded audio through
  the existing client and Sonos audio route. Piper is the initial TTS baseline;
  Pocket TTS must earn selection through latency, resource, and listening
  checks. Qualify playback stop latency while the audio path is active so later
  interruption does not depend on an unmeasured Sonos buffer.
- Why: The browser already owns deliberate keyboard input, visible feedback,
  and qualified Sonos playback. The ThinkPad has more compute and is the
  accepted processing host. Vosk may favor constrained low-cost recognition,
  while Whisper may favor open conversational accuracy; the host and room
  decide that tradeoff. Local replaceable speech backends keep raw audio off
  the internet without committing the product to one engine before it is
  measured.
- Status: decided

### C3 - Assistant Action Permission

- Decision: Which actions the model may request and how its output becomes a
  real room change.
- Options: Answer only; every coordinator action; one exact scene tool; a
  general tool registry; direct Hue access.
- Impact if wrong: A broad or separate control path could make model output
  authoritative, bypass coordinator validation, or cause surprising room
  changes.
- Proposed choice: Expose only one strict `activate_scene` function with one
  scene-name argument, configure Pi for sequential execution, disable parallel
  tool calls at the provider boundary, allow at most one call, and route it
  through `room.scene.activate`. Use Pi's preflight hook to treat model output
  as an untrusted request and report only the coordinator's observed result.
- Why: Exact scene names are already the shared human-facing boundary. One
  existing action proves the trust seam without inventing agent-specific
  permissions or exposing Hue identifiers.
- Status: decided

### C4 - Voice Privacy And Retention

- Decision: What leaves the home, what is retained, and what the user can see
  while sensing or processing occurs.
- Options: Hosted raw audio with provider conversation state; local audio with
  hosted text reasoning; fully local processing; retained transcripts and
  history.
- Impact if wrong: The system occupies a private one-room home, so hidden
  capture or unclear provider retention would be difficult to trust.
- Proposed choice: Keep raw audio and synthesized audio on the LAN. Send only
  the current transcript, a minimal normalized context snapshot, and the one
  tool schema through OpenRouter. Disable prompt logging, deny data collection,
  require Zero Data Retention routing, and pin an allowed provider route.
  Persist no application transcript, response, recording, or conversation
  history and never log their contents. Show every sensing and processing phase
  on screen.
- Why: This keeps the most sensitive input local while allowing a capable
  replaceable reasoning model. OpenRouter adds another processor between the
  home and the selected model provider, so the deployed route and its effective
  retention controls must be explicit rather than inferred from the model
  name.
- Status: decided

### C5 - Concurrent Channel Development

- Decision: How voice and channel issues proceed concurrently without sharing a
  mutable working directory or creating permanent repositories.
- Options: One serial branch; one long-lived branch per Planpoint; one Git
  worktree per active issue; separate repositories; worktrees with a shared
  symlinked `docs/` directory.
- Impact if wrong: Concurrent issues could allocate duplicate records, hide
  integration conflicts, or make documentation changes appear in the wrong
  branch.
- Proposed choice: Keep one integration repository and create one worktree per
  active issue branch. Reserve every `GH-XXX` identifier in accepted Planpoints
  on `main`, keep a complete independent `docs/` checkout in each worktree, and
  integrate through frequent rebases and small PRs.
- Why: Git worktrees already share repository objects and refs. Sharing checked
  out files would bypass each worktree's index, while separate repositories
  would duplicate a deployment lifecycle that has not diverged.
- Status: decided

## Plumbing

- Threaded now: a coordinator-owned `agent.context` value contains the active
  channel's minimal observed state and the current lighting catalog without
  provider payloads, credentials, artwork URLs, or client objects.
- Input boundary: one endpoint-authenticated request contains a bounded PCM
  utterance. The audio exists only for the request lifetime.
- Interaction boundary: `agent.interaction` publishes one request ID and exact
  `listening`, `transcribing`, `thinking`, `acting`, `speaking`, `completed`, or
  `failed` phase without persisting content.
- Speech boundary: one recognizer backend converts bounded PCM to English text
  and one synthesizer backend converts the final answer to bounded audio. The
  selected engines remain configuration, not coordinator behavior.
- Media permission boundary: establish the exact configured coordinator origin
  as the shared Chromium media secure-context boundary and grant only audio
  capture for this issue; Planpoint 5 may add exact-origin video capture after
  rebasing this boundary.
- Harness boundary: the coordinator supervises one local Node child and
  exchanges request-ID-keyed messages over private standard streams. Pi Agent
  Core owns the ephemeral model turn; it does not receive coordinator internals
  or credentials for device integrations.
- Reasoning boundary: `pi-ai` sends one transcript plus one context snapshot to
  one pinned OpenRouter model, permits zero or one strict tool call, and obtains
  one short text answer.
- Action boundary: an exact requested scene goes through
  `room.scene.activate`; completion remains a later Hue observation.
- Output boundary: the selected synthesizer produces ephemeral audio that
  Chromium plays through the existing PulseAudio and Sonos route.
- Cancellation seam: every capture, Pi turn, synthesis result, and playback is
  tied to the interaction request ID. Cancellation stops local playback and
  aborts unfinished work where supported; every later result for that ID is
  ignored. Exact spoken-prefix history reconciliation remains deferred with
  multi-turn conversation.
- Pattern set: agents consume normalized coordinator context and request
  allow-listed coordinator actions; they do not own observed state or device
  integrations.

## Issues

1. **GH-012 - Publish Agent-Safe Room Context**: extract one immutable,
   provider-free context projection for Today, Music, and lighting without
   adding a model, microphone, public endpoint, or frontend change.
2. **GH-014 - Qualify Deliberate Local Speech**: qualify the USB-connected
   Anker PowerConf S330, press-bounded Chromium capture, the shared exact-origin
   media security boundary, English Vosk and quantized `whisper.cpp`, Piper and
   Pocket TTS, the two small backend contracts, endpoint permissions, bounded
   start and playback-stop latency, and resource use before agent behavior
   depends on them.
3. **GH-016 - Answer One Contextual Follow-Up**: add the supervised Node
   process, Pi Agent Core with `pi-ai`, protected OpenRouter credential, pinned
   qualified text model, request-ID cancellation seam, ephemeral interaction
   lifecycle, and one spoken answer about Today or Music without tools.
4. **GH-018 - Activate One Scene By Voice**: expose only exact scene activation,
   execute at most one strict tool call through the coordinator, and speak the
   observed result.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: agent runtime and reasoning boundary; see Crossroads section.
- C2: speech processing and capture boundary; see Crossroads section.
- C3: assistant action permission; see Crossroads section.
- C4: voice privacy and retention; see Crossroads section.
- C5: concurrent channel development; see Crossroads section.

### Hot

#### H1 - Treat Model Output As A Request

- Decision: Validate every model-requested scene through the existing
  coordinator action and complete only from observed Hue state.
- Why: Natural-language confidence is not evidence that an action is allowed or
  that the room changed.
- Alternatives: Let the model call Hue; treat function output as completion;
  give the agent a broader internal coordinator handle.

#### H2 - Make Sensing State Unmistakable

- Decision: Tie microphone capture to one held shortcut and show every phase
  from listening through speaking or failure.
- Why: A deliberate voice feature in a one-room home must never leave recording
  or processing ambiguous.
- Alternatives: Wake word; click-to-toggle recording; hidden background
  capture; audio-only acknowledgement.

#### H3 - Keep Context Minimal And Observed

- Decision: Build one fresh context projection from coordinator-owned state for
  each interaction and send only the active channel plus lighting state.
- Why: The agent needs useful context but should not receive provider payloads,
  stale conversation memory, or every future channel by default.
- Alternatives: Ask the model to infer the screen; forward all SSE snapshots;
  let each channel call the model directly.

## References

- Pi Agent Core:
  `https://github.com/earendil-works/pi/tree/main/packages/agent`
- OpenRouter tool calling:
  `https://openrouter.ai/docs/guides/features/tool-calling`
- OpenRouter Zero Data Retention:
  `https://openrouter.ai/docs/guides/features/zdr`
- Vosk: `https://alphacephei.com/vosk/`
- `whisper.cpp`: `https://github.com/ggml-org/whisper.cpp`
- Piper: `https://github.com/OHF-Voice/piper1-gpl`
- Pocket TTS: `https://github.com/kyutai-labs/pocket-tts`
