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

## Starting Point

GH-022 is merged. Its shared `agent-turn.js` already creates a fresh Pi turn,
permits zero or one injected strict tool, serializes tool execution, rejects
unsafe tool shapes, and continues to one bounded final answer. Its local
workbench proves that continuation with an in-memory development executor.

Production still deliberately uses one request line and one terminal result
line between `agent_runtime.py` and `answer-child.js`; it sends only Today or
Music context and gives the child no tools. GH-018 changes that production
transport just enough to let the coordinator execute the one injected tool. It
does not move Hue authority, credentials, scene observation, or interaction
ownership into Node.

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

## 1. GH-018: Add One Bounded Coordinator Tool Exchange

- Extend the production agent context with only a fresh available-scene catalog:
  exact human-facing names, never Hue IDs, bridge state, credentials, or
  arbitrary lighting metadata. Do not expose a tool while lighting is
  unavailable.
- Make `answer-child.js` derive the strict `activate_scene` schema from that
  catalog and inject it into the existing GH-022 turn core. The child validates
  the tool name, arguments, request ID, and one-call limit before it asks the
  parent to act.
- Replace the production `communicate()` transaction with bounded private
  newline-JSON messages: the initial request, at most one child
  `tool_request`, exactly one matching coordinator `tool_result`, then one
  terminal completed or failed message. Each message is request-ID keyed,
  schema checked, size bounded, and content-free outside the current
  transcript, exact scene name, and bounded final answer.
- Keep stderr empty and fail the whole interaction on a duplicate, out-of-order,
  unknown, malformed, stale, cancelled, or oversized message. The coordinator
  must terminate the child process group on cancellation, timeout, endpoint
  replacement, disconnect, or protocol failure.
- This is atomic because it establishes the complete untrusted model-request
  boundary without granting execution authority.

## 2. GH-018: Execute And Report One Observed Scene Action

- Give `Coordinator.interact()` the one callback needed to handle a validated
  child tool request. When it arrives, confirm the interaction is still the
  active endpoint-owned request, publish `acting`, and revalidate the exact
  scene against the latest available catalog while holding the existing action
  ownership boundary.
- Extract or reuse the scene execution primitive behind `room.scene.activate`;
  do not call the public HTTP route or duplicate Hue behavior. The shared path
  must retain its current serialization, adapter timeout, observed completion,
  error mapping, and endpoint action-status behavior.
- Return only a bounded sanitized observed result to the child. A successful
  final answer may claim activation only after that result confirms the exact
  requested scene; unavailable, rejected, timed-out, and cancelled cases stay
  explicit, content-free failures and never become a spoken success.
- This is atomic because it connects the already constrained request to the
  existing room authority and its visible outcome.

## 3. GH-018: Prove The Full Room Path

- Add focused Node protocol tests for no-tool answers, one successful tool
  continuation, every rejected message shape, provider failure, and cancellation
  races. Add coordinator tests for fresh-catalog revalidation, observed Hue
  success and failure, phase order, endpoint replacement, and ignored late
  child results.
- Deploy only after automated checks pass. On the physical room path, verify one
  contextual answer, one exact scene request, an unavailable-scene failure,
  cancellation during both thinking and acting, recovery, browser phases, and
  intelligible Sonos playback. Keep each observation window at or below 60
  seconds.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep Tool Execution In The Existing Interaction

- Decision: Continue the same supervised Pi turn across one coordinator-owned
  tool exchange instead of giving the child Hue authority or starting an
  unrelated second interaction.
- Proposed approach: Reuse GH-022's injected-tool continuation and extend only
  the production private standard-stream protocol with one request-ID-keyed
  `tool_request` and one sanitized `tool_result`. The coordinator validates and
  executes the request, and the child may then produce only the final answer.
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
