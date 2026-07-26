# GH-009 Plan: Control The Warm Room Scene

## What

- Resolve the sole Hue room named `Rum` and its `Warm` scene inside the existing
  coordinator adapter without exposing Hue resource IDs.
- Publish one normalized `room.lighting` snapshot that says whether `Warm` is
  active, inactive, or unavailable.
- Add the allow-listed `room.scene.activate` action with no caller-supplied room,
  scene, or provider fields.
- Keep the action request open until a post-command Hue observation confirms
  `Warm` is active or the action reaches an unavailable, timeout, or failure
  result.
- Show persistent lighting state and temporary accepted, completed, and failed
  action feedback on the existing room display.

## Out Of Scope

- More rooms, scenes, or lighting actions.
- Individual lamp controls, brightness, colors, scene editing, arbitrary Hue
  entity browsing, or client-supplied scene names.
- A general provider, action-handler, device, or configuration framework.
- Turning the room off or toggling the scene.
- Changing Hue app scenes, room membership, remote mappings, or manual control.
- Today, channel selection, or physical remote input.

## Deferred

- GH-010 will compose Today and Music with coordinator-owned channel state while
  retaining the lighting snapshot and interaction feedback added here.
- GH-011 will map the existing Hue remote to this same
  `room.scene.activate` action.
- Additional scenes and controls remain later work because `Warm` is sufficient
  to prove semantic action authority and observed completion.

## Acceptance Criteria

- [ ] The adapter resolves exactly one room named `Rum` and exactly one `Warm`
  scene belonging to it; missing or ambiguous matches make the action
  unavailable rather than selecting another Hue resource.
- [ ] Hue application credentials, bridge identity, room and scene resource
  IDs, client-library objects, and raw provider events remain inside the Hue
  adapter and never enter HTTP, server-sent events, or normal logs.
- [ ] Every endpoint connection receives a normalized `room.lighting` snapshot
  with exact `scene`, `status`, and `observedAt` fields; status is only
  `active`, `inactive`, or `unavailable`.
- [ ] Hue scene-status events publish changed lighting snapshots, including
  changes made through the Hue app, the existing remote, or ordinary switches.
- [ ] `POST /api/actions` accepts `room.scene.activate` with a unique request ID
  and no room, scene, Hue ID, or other provider argument.
- [ ] The action does not require the room endpoint to be connected, and Hue
  unavailability does not affect Music, endpoint identification, or coordinator
  health.
- [ ] A scene request completes only after a post-command Hue observation
  reports `Warm` active; command rejection, bridge interruption, and an absent
  matching observation produce distinct failure, unavailable, and timeout
  results.
- [ ] The connected room display shows accepted, completed, unavailable,
  timeout, and failed scene feedback without executing the Hue action itself.
- [ ] The existing Music view shows whether `Warm` is active, inactive, or
  unavailable without adding a lighting control.
- [ ] Duplicate request IDs and overlapping actions are rejected consistently,
  and endpoint disconnection fails only endpoint-owned identification rather
  than an in-flight Hue action.
- [ ] Focused tests cover exact target resolution, sanitized snapshots, external
  state changes, observed completion, unavailable state, command failure,
  timeout, action serialization, HTTP responses, server-sent events, and client
  state reduction without requiring the real bridge.
- [ ] Existing coordinator, endpoint, and frontend tests continue to pass;
  Python compilation, affected shell parsing, systemd verification, dependency
  integrity, frontend checks and build, production audit, and whitespace checks
  pass.
- [ ] The final issue record contains exact invocation, deployment, recovery,
  automated-check, and reviewer-owned live confirmation steps without
  credentials, network addresses, bridge identity, or Hue resource IDs.

## Tasks

### 1. Observe And Activate One Exact Hue Scene

- Resolve `Rum` and its `Warm` scene from the initialized V2 bridge, retain
  provider identifiers inside the adapter, and normalize the scene's observed
  active status.
- Add one bounded adapter operation that recalls `Warm` and completes only from
  a later matching scene observation.
- Cover target mismatch, external changes, connection loss, command failure,
  timeout, and recovery with fake-bridge tests.

### 2. Expose One Coordinator-Owned Room Action

- Publish the current lighting snapshot with each endpoint connection and on
  changes.
- Dispatch `room.scene.activate` through the existing request-ID lifecycle,
  serialize visible actions, and map adapter outcomes to explicit HTTP and
  display-facing results.
- Preserve the endpoint-owned identify callback and ensure Hue work survives an
  endpoint disconnect.

### 3. Present Lighting State And Action Feedback

- Extend the client room state with independent lighting and scene-interaction
  events so Music state survives every update.
- Add a small persistent `Warm` status and reuse the full-screen interaction
  layer for accepted, completed, unavailable, timeout, and failed outcomes.
- Document the outside-caller command and bounded live checks on the real room.

## Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Resolve One Product Target By Exact Hue Names

- Decision: Bind the semantic room action to room `Rum` and scene `Warm` while
  keeping Hue identifiers private.
- Proposed approach: Resolve exact names after every bridge connection and
  require one matching scene whose Hue group is the one matching room. Treat
  missing or duplicate matches as unavailable.
- Why: The user reduced the bridge to one deliberately named room and selected
  one scene. Exact matching is understandable and fails loudly if the Hue
  configuration changes.
- Alternatives: Store provider IDs; accept names or IDs from callers; choose
  the first room or scene; add a configuration or discovery UI.
- Review focus: Group membership, duplicate handling, reconnect behavior, and
  absence of provider identifiers outside the adapter.

### H2 - Complete Only From A Later Scene Observation

- Decision: Define successful action completion as an observed post-command
  active status for `Warm`.
- Proposed approach: Subscribe to scene updates before accepting work, issue
  the recall through `aiohue`, and wait within the existing action bound for a
  later target-scene event that reports static or dynamic active state.
- Why: A successful bridge response proves command acceptance, not resulting
  room state. A later Hue observation supplies the trustworthy feedback chosen
  by Planpoint 3.
- Alternatives: Complete from the recall response; poll after a fixed delay;
  infer completion from aggregate power or brightness.
- Review focus: Already-active recall, stale events, event interruption,
  command errors, timeout cancellation, and late observations.

### H3 - Serialize Visible Actions Without Coupling Their Owners

- Decision: Allow only one coordinator action to own the room interaction
  feedback at a time while keeping endpoint and Hue failure boundaries
  independent.
- Proposed approach: Reuse the bounded request-ID store for both allow-listed
  actions, record which component owns each request, and reject a second active
  action consistently. Disconnecting the endpoint fails only an
  endpoint-owned identify request.
- Why: Concurrent actions would compete for one full-screen feedback layer, but
  Hue must remain callable when the endpoint is absent or reconnecting.
- Alternatives: Maintain unrelated per-provider queues; allow overlapping
  overlays; require an endpoint for every room action; build a general action
  scheduler.
- Review focus: Duplicate and busy handling, endpoint replacement, request
  trimming, terminal races, and preserving existing identify behavior.

## Stylistic

### S1 - Treat Inactive As A Deliberately Broad State

- Choice: Display `Warm active`, `Warm inactive`, or `Warm unavailable` rather
  than naming another scene or inferring lamp power.
- Alternative: Publish individual lamp state, aggregate brightness, or the name
  of any active Hue scene.
- When to apply: Use this narrow wording wherever GH-009 presents
  `room.lighting`; expand it only when another accepted room action needs more
  state.
