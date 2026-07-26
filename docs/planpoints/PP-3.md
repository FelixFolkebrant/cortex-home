# PP-3: Today And Room Control

## Slice

The room display can switch between useful Today and Music channels, show the
existing Hue scenes and which are active, and let the attached keyboard invoke
the same allow-listed channel and scene actions as another Cortex Home caller.

- The existing Hue bridge owns lamp, room, scene, and remote state; a pinned
  Hue client library connects it directly to the ThinkPad coordinator.
- The Cortex Home coordinator remains the only product action boundary and
  exposes normalized channel, Today, and lighting state to the client.
- One full-screen React shell presents Today and Music without adding another
  dashboard or application runtime.
- Today shows local time, date, current weather, and a small near-term forecast
  at room-viewing scale.
- Fixed keyboard shortcuts supply deliberate channel selection and scene
  cycling without adding mouse, touchscreen, or a new hardware integration.
- Accepted actions, observed results, unavailability, and failure remain
  visually unmistakable.

This is the first slice that proves Cortex Home can compose multiple channels
and control the room through the existing Hue authority without splitting its
feedback or permission paths.

## Out Of Scope

- Home Assistant, a general automation platform, dashboards, user-facing
  automations, device history, or public access.
- Individual lamp controls, color pickers, scene creation or editing,
  brightness sliders, or a general device browser.
- Calendar, email, tasks, news, commute, account data, or configurable Today
  widgets.
- More than Today and Music, nested navigation, browser history, deep links, or
  a universal channel/plugin protocol.
- Voice, microphone, camera, presence, gesture, agent, or proactive input.
- Replacing the Hue app, remapping or subscribing to the Hue remote, changing
  existing switches, or replacing manual Spotify control.
- Supporting physical controllers, configurable key bindings, or a shortcut
  settings interface.

## Deferred To Later Planpoints

- Voice activation, speech processing, and agent permissions remain in
  Planpoint 4 because they should inherit one qualified room action and channel
  context.
- Further channels remain in Planpoint 5 because Today and Music are enough to
  establish the first real composition boundary.
- A repository split remains deferred until the Hue adapter or channel client
  demonstrates an independently useful deployment lifecycle.
- Creating or editing scenes and adding other lighting controls remain later
  issue work because the existing room catalog is enough to prove named
  activation, observed state, and failure feedback.
- Home Assistant remains deferred until another device family, cross-device
  automation, history, or administration flow proves that a general platform
  would replace more machinery than it adds.

## Crossroads

### C1 - Device And Action Authority

- Decision: Which system owns Hue device identity and resulting device state
  while Cortex Home owns product actions and feedback.
- Options: The Hue bridge through a maintained client library; Home Assistant
  behind the coordinator; a custom implementation of the raw Hue protocol.
- Impact if wrong: Device identity, credentials, automations, state
  subscriptions, and future agent permissions would become expensive to move.
- Proposed choice: Keep the Hue bridge as the device authority and use pinned
  `aiohue` behind one coordinator adapter. The coordinator retains allow-listed
  semantic actions, active channel, interaction phase, and client contracts.
- Why: Home Assistant's Hue integration uses the same library. Direct use keeps
  maintained V1/V2 bridge, scene, and event support while avoiding another
  service, dashboard, configuration store, API credential, and update
  lifecycle. A later adapter can replace it without changing product actions or
  client state.
- Status: decided

### C2 - Channel Presentation Architecture

- Decision: How multiple room channels are composed, selected, and recovered.
- Options: One full-screen React shell; a compositor launching mixed native and
  web applications; isolated desktops or virtual machines; a hybrid from the
  start.
- Impact if wrong: Every future channel would inherit the runtime, navigation,
  deployment, state, and hardware-access model.
- Proposed choice: Keep one full-screen React client and let the coordinator
  own the active channel. Render Today and Music as explicit channel views
  without adding a router, general registry, or plugin API. Preserve a later
  native or streamed escape hatch only when a real channel cannot fit.
- Why: The qualified Music view proves the browser performs well on the iMac,
  and current channels need the same live state and interaction overlays. A
  compositor or universal channel framework solves needs not yet demonstrated.
- Status: decided

### C3 - Interim Room Input

- Decision: Which deliberate input invokes coordinator actions before the
  voice-agent slice.
- Options: Fixed shortcuts on the attached keyboard; subscribe to the existing
  Hue remote; add another dedicated physical controller.
- Impact if wrong: An interim input could add hardware integration and
  configuration that the later voice path makes unnecessary, or interfere
  with a remote whose native Hue behavior is already useful.
- Proposed choice: Keep the existing `Ctrl`+`Alt` channel shortcuts and add
  `Ctrl`+`Alt`+`S` to cycle through the detected room scenes. The Hue remote
  remains exclusively native to Hue and Cortex Home does not subscribe to its
  events.
- Why: The keyboard is already attached to the endpoint and already invokes
  coordinator-owned channel actions. One scene-cycle shortcut proves named room
  actions without another adapter, configuration surface, or conflict with the
  remote's existing behavior.
- Status: decided

## Plumbing

- Threaded now: `channel.active` carries `today` or `music`; a normalized
  `today.summary` carries current conditions and the small daily forecast; and
  `room.lighting` carries the detected scene catalog, availability, and active
  scene names from the Hue bridge to the coordinator and client.
- Actions threaded now: `channel.select` accepts only `today` or `music`, and
  `room.scene.activate` accepts one exact detected scene name but no Hue
  resource ID. UI and keyboard callers submit these same actions through the
  coordinator.
- Result boundary: Coordinator acceptance acknowledges only that a request may
  proceed. Completion follows a matching active-channel snapshot or observed
  Hue state; timeout and unavailability produce correlated failure.
- Credential boundary: The Hue application key and weather credentials stay on
  the ThinkPad. The endpoint client receives normalized state and never
  connects directly to the Hue bridge or a weather provider.
- Pattern set: Provider entities and events terminate at a narrow adapter;
  coordinator-owned semantic actions and normalized observed state are the
  reusable product boundary.

## Issues

1. **GH-008 COMPLETE - Connect The Hue Bridge**: added the pinned Hue client
   dependency, paired one repository-owned coordinator adapter, inventoried the
   bridge generation, room, scenes, and available remotes without recording
   private identifiers, and qualified restart and manual Hue-control recovery.
2. **GH-009 COMPLETE - Control One Hue Room Scene**: exposed one allow-listed
   coordinator action, published normalized lighting state, and proved
   accepted, completed, unavailable, timeout, and failure feedback without
   direct client access to the Hue bridge.
3. **GH-010 COMPLETE - Compose Today And Music Channels**: added
   coordinator-owned channel selection, rendered a focused Today view beside
   the existing Music view, and preserved reconnect and interaction overlays
   across channel changes.
4. **GH-011 COMPLETE - Discover And Cycle Room Scenes**: replaced the fixed
   Warm snapshot with the room's complete scene catalog and active scene names,
   accepted exact named-scene activation, and cycled the catalog from one fixed
   keyboard shortcut without integrating the Hue remote.

## Completion

Planpoint 3 was accepted as complete on 2026-07-26. The reviewer accepted the
current deployed state and explicitly waived the remaining reviewer-owned live
checks recorded in its issue documents.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: device and action authority; see Crossroads section.
- C2: channel presentation architecture; see Crossroads section.
- C3: interim room input; see Crossroads section.

### Hot

#### H1 - Normalize Hue Before Product Boundaries

- Decision: Keep Hue resource IDs, application credentials, provider event
  shapes, and client-library objects inside one coordinator adapter.
- Why: The React client, keyboard, and future agent should depend on
  stable room actions and state rather than the selected device authority's
  schema.
- Alternatives: Let every caller use Hue directly; expose Hue resource IDs in
  coordinator actions; mirror every bridge resource.

#### H2 - Complete Actions From Observed State

- Decision: Treat a successful Hue command as accepted work and complete it
  only after the requested named scene is observed active.
- Why: A service response does not prove the lamps changed, and keyboard and
  future agent callers need the same trustworthy feedback as other callers.
- Alternatives: Complete immediately after the API response; delay for a fixed
  interval; let each caller decide whether the action worked.

#### H3 - Keep The First Channel Shell Concrete

- Decision: Implement Today and Music explicitly while sharing only active
  channel, connection, and temporary interaction behavior already proven to
  repeat.
- Why: Two real channels justify composition but not a dynamic registry,
  extension API, route framework, or general widget system.
- Alternatives: Build a plugin architecture; add routing and configurable
  dashboards; duplicate the complete full-screen shell in each channel.

#### H4 - Keep Keyboard Mappings Deliberate

- Decision: Accept only the fixed channel and scene-cycle shortcuts and ignore
  other key combinations.
- Why: A room control should be predictable, while configurable mappings would
  expand both failure modes and setup burden before voice control exists.
- Alternatives: Subscribe to the Hue remote; accept broad single-key controls;
  add configurable key bindings.
