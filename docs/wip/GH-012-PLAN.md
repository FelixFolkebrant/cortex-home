# GH-012 Plan: Publish Agent-Safe Room Context

# What

- Add one pure coordinator context projection for the active Today or Music
  channel plus current lighting state.
- Copy and reduce existing normalized state so provider objects, credentials,
  artwork URLs, internal endpoint tokens, and mutable coordinator dictionaries
  cannot cross into the future model adapter.
- Keep the context inside the coordinator process for now; no model, credential,
  microphone, public endpoint, persistence, or frontend change is added.

## Out Of Scope

- OpenAI SDK or API calls, prompts, tools, model selection, API credentials, or
  conversation state.
- Audio capture, transcription, speech synthesis, playback, or agent feedback.
- Headlines or future channel context.
- New HTTP or SSE endpoints.
- Changes to Today, Music, lighting, channel selection, or action behavior.
- Generic provider, channel, context-plugin, or schema-version frameworks.

## Deferred

- GH-014 qualifies local speech independently from this pure state boundary.
- GH-016 passes this context to the model and adds ephemeral agent interaction.
- GH-018 adds the exact scene tool after the answer-only path is qualified.
- Headlines context waits until the new channel is concrete and both Planpoints
  are integrated.

## Acceptance Criteria

- [ ] One repository-owned pure function returns a new context value from exact
  active-channel, Today, Music, and lighting snapshots.
- [ ] The top-level shape contains only `activeChannel`, `channel`, and
  `lighting`.
- [ ] Today context contains availability, time zone, current conditions,
  forecast, and observation time without provider or cache fields.
- [ ] Music context contains availability or playback state and, when present,
  item type, title, creators, collection, position, duration, and observation
  time without artwork URLs.
- [ ] Lighting context contains only availability, ordered scene names, active
  scene names, and observation time.
- [ ] Only the active channel's detail is included; inactive Today or Music
  content is absent.
- [ ] Invalid or unavailable snapshots fail closed to small unavailable context
  rather than forwarding unexpected fields.
- [ ] Mutating returned nested values cannot mutate coordinator-owned state.
- [ ] Coordinator tests cover Today, Music, unavailable state, field reduction,
  invalid input, and copy isolation.
- [ ] Existing coordinator, Hue, Today, endpoint, and frontend checks remain
  unchanged and pass.
- [ ] The durable issue record documents the exact context contract and how a
  later adapter consumes it without exposing a new LAN endpoint.

# Tasks

## 1. Define The Pure Context Projection

- Add one small `coordinator/context.py` module with exact validation and
  explicit Today, Music, and lighting projections.
- Keep channel-specific projection functions concrete; do not build
  registration or plugin machinery.
- Add focused fixtures and tests for every accepted field and failure state.

## 2. Expose One Coordinator-Owned Snapshot

- Add a locked `Coordinator.context()` method that passes current normalized
  state into the pure projection and returns an isolated result.
- Do not publish the value through HTTP or SSE and do not retain another copy.
- Cover active-channel changes and concurrent snapshot replacement with
  coordinator tests.

## 3. Record The Agent Context Boundary

- Document the exact safe shape and its provider exclusions in
  `coordinator/README.md`.
- Create `docs/wip/GH-012.md` with the implementation walkthrough, plan diff,
  problems, checks, and remaining reviewer judgments.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Project State Instead Of Forwarding It

- Decision: Build one exact context object from current normalized state and
  reject unexpected shapes instead of copying coordinator snapshots wholesale.
- Proposed approach: Use explicit channel-specific projection functions and
  include only the active channel plus lighting.
- Why: Existing snapshots contain safe client data today, but future provider
  or personal fields must not become model context accidentally.
- Alternatives: Forward every SSE snapshot; serialize coordinator attributes;
  let the model adapter inspect internal objects.
- Review focus: Field allow-listing, unavailable state, nested copy isolation,
  and future channel extension.

### H2 - Keep Context Internal Until A Consumer Exists

- Decision: Add a coordinator method but no context HTTP or SSE endpoint.
- Proposed approach: The future in-process agent adapter calls the locked
  method immediately before one model request.
- Why: No current LAN caller needs this state, and a new public read boundary
  would create privacy and compatibility obligations before the agent exists.
- Alternatives: Add `/api/context`; reuse endpoint SSE; run the agent as an
  external service.
- Review focus: Thread safety, separation from endpoint identity, and whether
  the later adapter remains replaceable as a module.
