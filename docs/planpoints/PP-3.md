# PP-3: Today And Room Control

## Slice

The room display can switch between useful Today and Music channels, and one
physical room control can invoke the same allow-listed channel and Hue actions
as another Cortex Home caller with visible observed-state feedback.

- The existing Hue bridge owns lamp, room, scene, and remote state; a pinned
  Hue client library connects it directly to the ThinkPad coordinator.
- The Cortex Home coordinator remains the only product action boundary and
  exposes normalized channel, Today, and lighting state to the client.
- One full-screen React shell presents Today and Music without adding another
  dashboard or application runtime.
- Today shows local time, date, current weather, and a small near-term forecast
  at room-viewing scale.
- One Hue-native remote or switch supplies deliberate tactile channel and scene
  inputs without adding normal keyboard, mouse, or touchscreen operation.
- Accepted actions, observed results, unavailability, and failure remain
  visually unmistakable.

This is the first slice that proves Cortex Home can compose multiple channels
and control the room through the existing Hue authority without splitting its
feedback or permission paths.

## Out Of Scope

- Home Assistant, a general automation platform, dashboards, user-facing
  automations, device history, or public access.
- Individual lamp controls, color pickers, arbitrary scene names, brightness
  sliders, or a general device browser.
- Calendar, email, tasks, news, commute, account data, or configurable Today
  widgets.
- More than Today and Music, nested navigation, browser history, deep links, or
  a universal channel/plugin protocol.
- Voice, microphone, camera, presence, gesture, agent, or proactive input.
- Replacing the Hue app, existing switches, or manual Spotify control.
- Supporting multiple physical controllers or configurable button mappings.
- Purchasing another room controller before the existing Hue remote is
  qualified.

## Deferred To Later Planpoints

- Voice activation, speech processing, and agent permissions remain in
  Planpoint 4 because they should inherit one qualified room action and channel
  context.
- Further channels remain in Planpoint 5 because Today and Music are enough to
  establish the first real composition boundary.
- A repository split remains deferred until the Hue adapter or channel client
  demonstrates an independently useful deployment lifecycle.
- Additional lighting scenes and controls remain later issue work because one
  scene is enough to prove authority, observed state, and failure feedback.
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

### C3 - First Physical Room Input

- Decision: Which input family first invokes coordinator actions without a
  keyboard, mouse, touchscreen, microphone, or camera.
- Options: A Hue-native remote or switch through the existing bridge; a
  dedicated USB/HID control attached to the iMac; a new custom radio or
  microcontroller input.
- Impact if wrong: The system could acquire another privileged endpoint daemon,
  bypass the coordinator action boundary, or commit to hardware that does not
  fit normal room use.
- Proposed choice: Use the existing Hue remote exposed through the direct Hue
  adapter. Confirm its exact model and supported bridge events in GH-008, then
  map only one deliberate control to channel selection and one to the accepted
  Hue scene; ignore other gestures until a later issue needs them.
- Why: This reuses the local bridge and selected device authority, avoids
  privileged iMac hardware access, and lets a tactile input call the same
  coordinator actions as another client. The exact supported device can be
  selected after confirming what the user owns or wants in the room.
- Status: decided

## Plumbing

- Threaded now: `channel.active` carries `today` or `music`; a normalized
  `today.summary` carries current conditions and the small daily forecast; and
  `room.lighting` carries availability and observed room state from the Hue
  bridge to the coordinator and client.
- Actions threaded now: `channel.select` accepts only `today` or `music`, and
  `room.scene.activate` accepts no client-supplied Hue resource or scene ID. UI
  callers and the physical-input adapter submit these same actions through the
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

1. **GH-008 - Connect The Hue Bridge**: add the pinned Hue client dependency,
   pair one repository-owned coordinator adapter, inventory the bridge
   generation, room, scenes, and available remotes without recording private
   identifiers, and qualify restart and manual Hue-control recovery.
2. **GH-009 - Control One Hue Room Scene**: expose one allow-listed coordinator
   action, publish normalized lighting state, and prove accepted, completed,
   unavailable, timeout, and failure feedback without direct client access to
   the Hue bridge.
3. **GH-010 - Compose Today And Music Channels**: add coordinator-owned channel
   selection, render a focused Today view beside the existing Music view, and
   preserve reconnect and interaction overlays across channel changes.
4. **GH-011 - Add The First Physical Room Control**: connect the accepted
   tactile input through the coordinator's existing actions and qualify channel
   selection, the Hue scene, ignored gestures, failure feedback, and recovery
   on the real room hardware.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: device and action authority; see Crossroads section.
- C2: channel presentation architecture; see Crossroads section.
- C3: first physical room input; see Crossroads section.

### Hot

#### H1 - Normalize Hue Before Product Boundaries

- Decision: Keep Hue resource IDs, application credentials, provider event
  shapes, and client-library objects inside one coordinator adapter.
- Why: The React client, physical input, and future agent should depend on
  stable room actions and state rather than the selected device authority's
  schema.
- Alternatives: Let every caller use Hue directly; expose Hue resource IDs in
  coordinator actions; mirror every bridge resource.

#### H2 - Complete Actions From Observed State

- Decision: Treat a successful Hue command as accepted work and complete it
  only after the expected room state is observed.
- Why: A service response does not prove the lamps changed, and tactile inputs
  need the same trustworthy feedback as UI and future agent callers.
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

#### H4 - Keep Physical Mappings Deliberate

- Decision: Accept only the minimum channel and room-action gestures from the
  first controller and ignore everything else.
- Why: A room control should be predictable, while configurable mappings and
  button-combination state would expand both failure modes and setup burden.
- Alternatives: Forward raw button events; expose every gesture; add a mapping
  editor before a second controller exists.
