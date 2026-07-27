# GH-018 Plan: Activate One Scene By Voice

# What

- Let one deliberate voice interaction either answer from the visible Today or
  Music context or request one exact detected Hue scene.
- Expose one strict `activate_scene` tool to Pi Agent Core and keep its
  execution inside the coordinator through the existing scene validation,
  serialization, observed-completion, and failure boundaries.
- Show the existing `acting` phase while Hue is changing, then synthesize a
  short answer grounded in the coordinator's observed result.
- Keep the interaction ephemeral and preserve the accepted OpenRouter routing,
  privacy, cancellation, and content-free diagnostics boundaries.

## Out Of Scope

- More tools, multiple tool calls, parallel tools, scene cycling, channel
  changes, arbitrary Hue controls, shell access, browser control, or direct Hue
  access from the Node child.
- Inferred or proactive actions, retries, action planning, follow-up questions,
  conversation memory, or accepting a scene that is not in the current
  coordinator catalog.
- Changes to speech recognition, speech synthesis, microphone capture, the
  OpenRouter model/provider route, or the existing human and keyboard scene
  action.
- Making Camera, AirPlay, or camera frames available to the agent.

## Deferred

- Additional room actions wait until one exact scene request proves that model
  tool output remains understandable, cancellable, and subordinate to observed
  coordinator state.
- Multi-turn reconciliation and spoken interruption history remain deferred
  because this issue still owns one ephemeral interaction.
- Model or provider changes remain separate qualification work so tool
  authority is not mixed with model selection.

## Acceptance Criteria

- [ ] The child receives only the current normalized Today or Music projection
  plus a fresh normalized lighting catalog; it receives no Hue identifiers,
  credentials, adapter objects, artwork URLs, camera state, or provider data.
- [ ] Pi exposes exactly one strict `activate_scene` tool whose sole argument
  is one exact scene name from the supplied catalog.
- [ ] One interaction may produce zero or one tool request. A second, parallel,
  malformed, unknown, stale, or non-exact request fails without changing the
  room.
- [ ] A valid tool request crosses only the private request-ID-keyed child
  protocol and is revalidated by the coordinator before execution.
- [ ] The coordinator uses the same scene validation, action serialization,
  Hue adapter, observed-completion, timeout, and failure semantics as
  `room.scene.activate`; the Node child never contacts Hue or the public action
  endpoint.
- [ ] The browser shows `thinking`, then `acting` while the accepted scene
  request is in flight, followed by `speaking` and an observed success or clear
  failure.
- [ ] The final spoken answer claims success only after the coordinator observes
  that exact scene active and receives only a bounded sanitized tool result.
- [ ] A question that needs no action still follows the existing answer-only
  path and does not invoke the scene adapter.
- [ ] Cancellation, endpoint replacement, disconnect, timeout, malformed child
  output, provider failure, scene disappearance, Hue rejection, and late child
  results cannot execute a stale action or publish stale success.
- [ ] OpenRouter payloads retain the pinned model, provider allowlist, ZDR,
  no-storage, no-fallback, no-reasoning, bounded-output, and no-retry controls.
- [ ] Audio, transcript, answer, tool arguments, provider content, and
  conversation state are not persisted or logged; diagnostics remain numeric
  and content-free.
- [ ] Automated tests cover answer-only, one successful tool call, every
  rejected tool shape, observed Hue failure, cancellation races, and private
  protocol bounds without real credentials or hardware.
- [ ] A deployed manual pass proves an exact scene request, a contextual
  answer without a tool, an unavailable scene failure, visible phases, spoken
  result, cancellation, and recovery.

# Tasks

## 1. GH-018: Request One Exact Scene

- Extend the normalized child request with the current lighting catalog, define
  the one strict Pi tool, and add one bounded request-ID-keyed tool exchange to
  the existing private standard-stream protocol.
- This is atomic because it establishes and tests the complete untrusted model
  request boundary without granting execution authority.

## 2. GH-018: Execute The Observed Scene Action

- Revalidate the request in the coordinator, run it through the shared exact
  scene execution boundary, publish the acting lifecycle, return one sanitized
  result to Pi, and speak only the resulting bounded answer.
- This is atomic because it connects the already constrained request to the
  existing room authority and its visible outcome.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep Tool Execution In The Existing Interaction

- Decision: Continue the same supervised Pi turn across one coordinator-owned
  tool exchange instead of giving the child Hue authority or starting an
  unrelated second interaction.
- Proposed approach: Extend the bounded private standard-stream protocol with
  one request-ID-keyed `tool_request` and one sanitized `tool_result`. The
  coordinator validates and executes the request, and the child may then
  produce only the final answer.
- Why: The model needs the real observed action result to answer truthfully,
  while credentials, validation, and state authority must remain in the
  coordinator.
- Alternatives: Give the child coordinator credentials; return a tool request
  and start a second model turn; bypass Pi's tool lifecycle; let the child call
  Hue directly.
- Review focus: protocol bounds, deadlocks, cancellation, stale messages,
  process termination, and proof that only one tool request can cross.

### H2 - Distinguish Scene Names From Descriptive Language

- Decision: Treat the lighting catalog as data and act only on an explicit
  exact tool argument, even when words such as “warm” also describe weather or
  music.
- Proposed approach: Give the model the bounded scene catalog separately from
  channel context, require one exact catalog value in the strict schema, and
  revalidate it against a fresh coordinator snapshot before Hue execution.
- Why: The earlier answer slice exposed real ambiguity between weather
  language and a scene label; descriptive conversation must not become room
  authority.
- Alternatives: Case-insensitive or fuzzy matching; infer the closest scene;
  let the model emit arbitrary labels; expose no lighting context.
- Review focus: explicit user intent, exact matching, changed catalogs,
  unavailable lighting, and ambiguous utterances.

### H3 - Reuse Observed Scene Completion

- Decision: Refactor or call the existing exact scene execution seam rather
  than creating an agent-specific Hue path.
- Proposed approach: Share coordinator-internal validation and observed
  completion while preserving the public `room.scene.activate` action
  contract and the interaction's single busy owner.
- Why: Human, keyboard, and model requests should receive the same authoritative
  result without looping the child through the public HTTP API.
- Alternatives: Duplicate Hue execution; call the public endpoint internally;
  report model-request acceptance as success.
- Review focus: action serialization, observed state, error mapping, and no
  regression to existing scene callers.
