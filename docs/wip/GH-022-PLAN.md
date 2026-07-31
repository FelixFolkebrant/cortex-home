# GH-022 Plan: Run The Agent Core Locally

# What

- Add one laptop-local development entry point that exercises the existing
  speech and model components as a complete deliberate interaction without the
  coordinator HTTP API, room client, iMac, Sonos, or Hue bridge.
- Separate the provider-backed agent turn from Cortex Home's room integration
  so the same bounded turn can answer directly or request one allow-listed tool
  through an injected executor.
- Prove the tool continuation with one repository-owned, in-memory development
  tool whose result returns to the same Pi turn before the final answer.
- Capture from and play through the development laptop's selected audio devices
  behind local input and output boundaries, while retaining the selected Vosk
  recognizer, Pocket TTS synthesizer, pinned OpenRouter route, ephemeral
  content, cancellation, and bounded failures.

## Out Of Scope

- The ThinkPad coordinator service, endpoint HTTP or SSE protocol, room client,
  iMac provisioning, Anker microphone, Sonos playback, Hue execution, or any
  other physical-home integration.
- A general tool registry, dynamic tool discovery, MCP, shell or browser
  access, arbitrary local commands, multiple or parallel tool calls, retries,
  planning, or autonomous behavior.
- Changing the selected STT, TTS, agent framework, model, provider route,
  prompt-retention policy, or production deployment layout.
- Wake words, continuous listening, voice activity detection, barge-in,
  overlapping interactions, conversation memory, or a graphical interface.
- Treating the IdeaPad's microphone, speakers, latency, or resource use as
  qualification evidence for the eventual room deployment.

## Deferred

- GH-018 will connect the proven tool-request boundary to exact Hue scene
  activation through the coordinator and will own observed room completion,
  browser phases, Sonos output, deployment, and physical confirmation.
- Additional tools wait until one production tool proves the permission and
  observation boundary. The local development tool is test scaffolding, not a
  product capability or a plugin system.
- Broader agent behavior remains deferred until deliberate single-turn use is
  useful and trustworthy.

## Acceptance Criteria

- [ ] One documented command starts a deliberate local voice interaction on a
  Linux development laptop without starting or contacting Cortex Home services
  or room hardware.
- [ ] The local input boundary records one bounded utterance from an explicitly
  selected or documented default input and always releases the device on
  completion, cancellation, and failure.
- [ ] The selected Vosk backend transcribes the existing 16 kHz mono PCM shape,
  the pinned OpenRouter route runs the turn, and the selected Pocket TTS backend
  produces audio for the local output boundary.
- [ ] One turn can either answer without a tool or request exactly one
  allow-listed development tool, receive its bounded sanitized result, and
  produce the final spoken answer in the same Pi turn.
- [ ] Tool definitions and execution are injected into the agent turn; the core
  does not import the development tool, coordinator, Hue adapter, audio device,
  or deployment configuration.
- [ ] Unknown, malformed, repeated, parallel, stale, or cancelled tool requests
  fail without execution, and a tool result cannot be mistaken for observed
  production state.
- [ ] The runner reports listening, transcribing, thinking, acting, speaking,
  completed, failed, and cancelled phases without printing or persisting audio,
  transcripts, answers, tool arguments, tool results, or provider content.
- [ ] `Ctrl`+`C` and bounded component timeouts release local audio resources,
  abort unfinished model work where supported, and ignore late results.
- [ ] Missing audio commands or devices, invalid PCM, unavailable models,
  missing credentials, provider failure, invalid agent output, tool failure,
  synthesis failure, and playback failure each produce an explicit terminal
  error.
- [ ] Automated tests exercise answer-only, successful tool continuation,
  rejected tool shapes, cancellation races, speech failures, and local audio
  cleanup with faux collaborators and no credentials, network, or hardware.
- [ ] A manual IdeaPad pass confirms one spoken answer, one spoken tool-backed
  answer, visible terminal phases, cancellation, recovery, and intelligible
  local playback; the record labels these as development-host evidence only.
- [ ] Agent, Python, production dependency, audit, syntax, and whitespace checks
  relevant to the changed files pass.

# Tasks

## 1. GH-022: Extract One Bounded Tool Turn

- Refactor the current answer-only Pi turn into a small provider-backed agent
  core that accepts an explicit bounded tool definition and executor, supports
  zero or one sequential tool request, and returns one final answer.
- This is atomic because it establishes the reusable reasoning and tool seam
  with deterministic tests before any audio or room adapter invokes it.

## 2. GH-022: Add The Local Voice Workbench

- Add the documented laptop runner, local audio input and output boundaries,
  in-memory development tool, lifecycle reporting, cancellation, and focused
  tests around the existing selected speech backends and extracted agent core.
- This is atomic because it composes already-bounded components into one
  developer-facing interaction without changing production integration.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep The Agent Core Independent Of Integrations

- Decision: Define the reusable boundary at one ephemeral text-and-tool turn,
  while microphone capture, playback, coordinator state, and hardware remain
  callers or executors outside it.
- Proposed approach: Inject a bounded tool definition and executor into the Pi
  turn, and compose speech plus local audio only in the development runner.
- Why: Speech, reasoning, and tool negotiation can be exercised on the laptop
  without creating a second production architecture or making the agent aware
  of Hue, HTTP, browser, or device details.
- Alternatives: Copy the production coordinator into a local mode; put STT and
  TTS inside the Node child; let the child call Cortex Home or hardware
  directly; create a general plugin framework.
- Review focus: dependency direction, process ownership, cancellation, and how
  GH-018 can reuse the boundary without bypassing coordinator authority.

### H2 - Use A Clearly Non-Product Development Tool

- Decision: Prove tool continuation with one deterministic in-memory tool that
  cannot affect the laptop or home.
- Proposed approach: Define the tool next to the local runner, give it a
  bounded schema and sanitized result, and make its output explicitly
  simulated in the system prompt and terminal phase reporting.
- Why: A harmless executor proves the complete model/tool lifecycle while the
  physical system is unavailable, without creating false observed state or an
  accidental capability.
- Alternatives: Mock tool use only in tests; call the Hue coordinator remotely;
  expose filesystem, shell, clock, network, or laptop controls.
- Review focus: no production registration, no ambient side effects, exact
  single-call enforcement, and truthful final wording.

### H3 - Keep Local Voice Evidence In Its Proper Scope

- Decision: Use the IdeaPad to validate developer usability and component
  composition, not to replace the accepted room-hardware qualification.
- Proposed approach: Keep audio devices selectable at the runner boundary,
  record only content-free local measurements, and leave all room-path checks
  to GH-018.
- Why: The laptop can prove that the software loop works while saying nothing
  conclusive about the iMac microphone, ThinkPad load, Sonos buffering, or Hue
  observation.
- Alternatives: Rebaseline the product on the IdeaPad; hard-code its devices;
  omit live local audio and test only files.
- Review focus: no machine-specific paths or identity, clear setup errors, and
  an explicit separation between development and deployment evidence.
