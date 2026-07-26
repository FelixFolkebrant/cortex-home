# GH-011 Plan: Discover And Cycle Room Scenes

## What

- Replace the fixed `Warm` target with the complete existing scene catalog for
  the exact Hue room `Rum`.
- Publish normalized room-lighting state containing availability, ordered scene
  names, every currently active scene name, and observation time.
- Generalize `room.scene.activate` to accept one exact detected scene name and
  complete only after Hue reports that requested scene active.
- Display the active scene state above both Today and Music.
- Add `Ctrl`+`Alt`+`S` to activate the next detected scene, wrapping from the
  last scene to the first.
- Keep the Hue remote exclusively native to Hue; Cortex Home does not subscribe
  to or interpret its button events.

## Out Of Scope

- Creating, editing, deleting, importing, or renaming Hue scenes.
- Individual lamps, room power, brightness, colors, effects, zones, other
  rooms, or a general Hue resource browser.
- An on-screen scene picker, scene search, favorites, aliases, configurable
  ordering, configurable key bindings, or scene history.
- Voice capture, an AI-agent runtime, natural-language matching, fuzzy scene
  names, or agent permissions.
- Hue remote input, another physical controller, or changes to native Hue
  behavior.

## Deferred

- Planpoint 4 will let the deliberate voice agent inspect the same normalized
  scene catalog and invoke `room.scene.activate` with an exact scene name.
- Friendly aliases and natural-language matching belong at the future agent
  boundary; the coordinator remains exact and deterministic.
- Scene creation, editing, favorites, and custom ordering remain in native Hue
  until a later product flow justifies owning them.

## Acceptance Criteria

- [ ] The Hue adapter resolves exactly one room named `Rum` and every scene
  whose group is that room. Zero or multiple room matches, an empty catalog, an
  empty scene name, or case-insensitively duplicate scene names make scene
  state and activation unavailable rather than selecting or hiding a provider
  resource.
- [ ] Available `room.lighting` snapshots have exact `status`, `scenes`,
  `activeScenes`, and `observedAt` fields. `status` is `available`; `scenes`
  contains every unique room scene name in deterministic case-insensitive
  order; `activeScenes` contains the active subset in that same order.
- [ ] Unavailable snapshots use `status: "unavailable"` with empty `scenes` and
  `activeScenes`; they never present a cached scene as currently available.
- [ ] Both Hue static and dynamic-palette activity count as active. Zero, one,
  or multiple active scenes are represented truthfully without inferring lamp
  power or inventing a scene.
- [ ] Hue scene updates made through the native Hue app or remote publish a
  changed aggregate snapshot. Unchanged aggregate state is suppressed.
- [ ] `POST /api/actions` accepts `room.scene.activate` only with a unique
  request ID and one exact `scene` value from the current available catalog.
  Missing, unknown, non-string, ambiguous, or extra fields are rejected without
  recalling a scene.
- [ ] Scene names, but no Hue scene ID, group ID, bridge identity, credential,
  provider object, or raw event, may cross the adapter boundary.
- [ ] A valid named activation reports accepted work and completes only after a
  later aggregate observation contains the requested name in `activeScenes`.
  Bridge rejection, interruption, unavailability, and missing observation
  retain distinct safe failure results.
- [ ] Named scene actions remain independent of endpoint availability and retain
  the existing unique-request and one-visible-action serialization rules.
- [ ] The shared room badge displays `Scenes unavailable`, `Custom lighting`
  when no scene is active, the active scene name when exactly one is active,
  and every active scene name when Hue reports more than one. It remains visible
  above Today and Music.
- [ ] `Ctrl`+`Alt`+`S` chooses the next name from the coordinator-provided
  `scenes` order after exactly one active scene and wraps after the last.
  With zero or multiple active scenes it starts from the first catalog entry.
- [ ] The scene shortcut uses a new request ID and the generalized
  `room.scene.activate` action. It prevents the browser default only when it
  can submit a scene action and shows the existing working, completed, and
  failed room feedback for the selected name.
- [ ] Repeated, shifted, meta-modified, incomplete, and other key combinations
  invoke no action. A scene shortcut is also ignored while another visible
  action is active or scene state is unavailable.
- [ ] Existing `Ctrl`+`Alt`+`1` and `Ctrl`+`Alt`+`2` channel selection,
  playback, Today, endpoint identification, weather, and manual Hue behavior
  remain unchanged.
- [ ] No Hue button subscription, remote mapping, credential change, new
  dependency, daemon, service, or public endpoint is added.
- [ ] Focused adapter, coordinator, HTTP/SSE, and client tests cover catalog
  resolution, duplicate names, aggregate external updates, zero/one/multiple
  active scenes, named activation, observed completion, failure, cycling,
  wrapping, ignored keys, and reconnect state without a live bridge.
- [ ] Existing coordinator, endpoint, and frontend tests continue to pass;
  Python compilation, shell parsing, dependency integrity, frontend checks and
  build, production audit, and whitespace checks pass.
- [ ] The final issue record contains exact deployment, recovery, invocation,
  automated-check, and reviewer-owned real-room confirmation steps without
  credentials, network addresses, Hue resource IDs, or raw events.

## Tasks

### 1. Normalize The Room Scene Catalog

- Replace the single-scene resolver and controller in `coordinator/hue.py` with
  one exact-room catalog that owns provider resources, subscriptions, active
  aggregation, and name-to-resource lookup.
- Publish complete available or unavailable snapshots and recompute them after
  any catalog scene update.
- Activate one exact catalog name within the existing total timeout, completing
  only from a later matching active observation.
- Cover catalog validation, active aggregation, external changes,
  interruption, recall failure, timeout, and recovery with fake Hue resources.

### 2. Publish And Activate Named Scenes

- Replace the fixed Warm coordinator snapshot with the normalized catalog and
  active-scene snapshot while preserving changed-state publication and
  reconnect behavior.
- Require one exact `scene` field for `room.scene.activate`, pass only that name
  into the Hue adapter, and retain endpoint-independent execution and current
  action serialization.
- Update HTTP, server-sent event, coordinator, and focused verifier contracts
  from fixed Warm activation to named scene activation.
- Cover validation, safe payloads, observed completion, distinct failures,
  endpoint disconnection, and reconnect snapshots.

### 3. Display And Cycle Scenes

- Replace the fixed Warm badge and copy with shared available, custom,
  single-active, multiple-active, and unavailable scene presentation.
- Extend the fixed keyboard classifier with physical `KeyS`; compute the next
  scene from the published order and active subset, then submit the named scene
  through the existing client action lifecycle.
- Preserve channel selection, view state, interaction serialization, listener
  cleanup, and native Hue control.
- Cover presentation state, next-scene selection, wraparound, ambiguous current
  state, and ignored key combinations.

### 4. Deploy And Record The Scene Catalog

- Update operator documentation with the normalized scene contract, exact named
  action, fixed shortcut, native-only remote boundary, and recovery path.
- Deploy through `./coordinator/install <server-ssh-host>` and confirm initial
  catalog display, native external scene changes, keyboard cycling, wraparound,
  named action success, unavailable feedback, and recovery on the real room
  hardware.
- Replace the Warm-specific verifier with a bounded named-scene verifier or
  update it without retaining a misleading fixed-Warm entry point.
- Create `docs/wip/GH-011.md` with the implementation walkthrough, plan diff,
  problems, exact check results, durable decisions, and remaining reviewer
  judgments.

## Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Make Detected Scene Names The Product Boundary

- Decision: Expose every unique scene name from exact room `Rum` and accept one
  exact detected name in `room.scene.activate`, while keeping Hue IDs internal.
- Proposed approach: Fail scene availability if the exact room is ambiguous,
  the catalog is empty, or any scene names are empty or duplicated without
  regard to case. Publish the complete ordered name catalog and use exact name
  lookup for activation.
- Why: The display, keyboard, and future voice agent need a stable human-facing
  catalog. Exact unique names keep the coordinator deterministic without
  leaking provider identifiers or inventing aliases before the agent flow.
- Alternatives: Keep only `Warm`; expose Hue IDs; silently select one duplicate;
  configure a repository-owned allow-list; add fuzzy matching now.
- Review focus: Existing room naming, duplicate handling, catalog changes after
  startup, name validation, provider-ID containment, and later voice-tool use.

### H2 - Represent Aggregate Scene Activity Without Guessing

- Decision: Normalize all currently active room scenes instead of forcing one
  active scene or treating every non-Warm state as inactive.
- Proposed approach: Publish ordered `scenes` and `activeScenes` arrays with an
  explicit availability status. Zero active scenes means custom or manually
  changed lighting; multiple active scenes remain visible as multiple.
- Why: Hue reports activity per scene, and external Hue controls can leave no
  exact scene active. Preserving zero or multiple matches prevents the display
  and future agent context from claiming more than the bridge observed.
- Alternatives: Publish one nullable scene; choose the first active scene;
  infer activity from lamp values; retain the fixed active/inactive Warm badge.
- Review focus: Static and dynamic activity, event ordering, unchanged
  suppression, disconnect state, multiple active scenes, and narrow display.

### H3 - Cycle The Coordinator Catalog Deterministically

- Decision: Define what the single keyboard gesture does when scene activity is
  clear, absent, or ambiguous.
- Proposed approach: Sort scene names case-insensitively at the coordinator.
  `Ctrl`+`Alt`+`S` selects the entry after the sole active scene and wraps; if
  zero or multiple scenes are active, it selects the first entry.
- Why: One fixed gesture stays predictable without configurable order or a
  client-owned catalog. Starting from the first scene gives custom and
  ambiguous states a deterministic recovery path.
- Alternatives: Preserve provider order; random or recently used order; add
  previous and next shortcuts; refuse to cycle unless exactly one is active;
  add an on-screen picker.
- Review focus: Whether alphabetical cycling feels natural, wraparound,
  catalog-update races, unavailable state, and the chosen `Ctrl`+`Alt`+`S`
  shortcut.

## Stylistic

### S1 - Name Observed Scene State Directly

- Choice: Show `Scenes unavailable`, `Custom lighting`, one active scene name,
  or the complete active-name list without a control or provider detail.
- Alternative: Keep `Warm active/inactive`, show lamp values, or add a scene
  menu.
- When to apply: Use this shared badge above Today and Music until a later
  interaction requires a dedicated scene-control surface.
