# GH-010 Plan: Compose Today And Music Channels

## What

- Add coordinator-owned `channel.active` state with exactly `today` and
  `music`; the initial channel after coordinator startup is `today`.
- Add the allow-listed `channel.select` action, which accepts only one of those
  two channel names and completes after the coordinator publishes the matching
  active-channel snapshot.
- Fetch current weather and a three-day forecast for Linköping through one
  narrow coordinator adapter, normalize it as `today.summary`, and keep the
  endpoint browser away from the weather provider.
- Render explicit full-screen Today and Music views in the existing React
  shell. Today shows local time, date, current conditions, and the small
  forecast at room-viewing scale.
- Preserve Music playback, Warm-scene state, connection recovery, and the
  existing interaction overlay while a channel changes or the endpoint
  reconnects.

## Out Of Scope

- More channels, a router, browser history, URLs, deep links, a channel
  registry, plugins, configurable dashboards, or widgets.
- Calendar, email, tasks, news, commute, traffic, account data, or any
  configurable Today content.
- An on-screen channel picker or ordinary keyboard, mouse, or touchscreen
  operation.
- A Hue remote mapping, other physical controls, or changes to the accepted
  Warm scene action.
- Weather history, alerts, hourly detail, location search, user geolocation,
  or a weather-settings UI.

## Deferred

- GH-011 will invoke this issue's `channel.select` and existing
  `room.scene.activate` actions from the qualified Hue remote.
- Further channels, their presentation needs, and any reusable channel
  abstraction remain deferred to Planpoint 5 because two concrete views are
  enough to establish the composition boundary.
- A weather-provider change remains a narrow coordinator-adapter change; a
  second provider, user-selected locations, or stored weather history is not
  justified by this first Today view.

## Acceptance Criteria

- [ ] The coordinator owns an in-memory active-channel snapshot with exactly
  `active: "today"` or `active: "music"`; startup defaults to `today`, every
  endpoint connection receives the latest snapshot, and changed selections are
  published as `channel.active` events.
- [ ] `POST /api/actions` accepts `channel.select` only with a unique request
  ID and an exact `channel` value of `today` or `music`; unknown, missing, or
  extra action fields are rejected without changing the active channel.
- [ ] A valid selection reports accepted work and completes only after the
  matching active-channel snapshot is published. It does not require an
  endpoint connection and preserves the existing request-ID and one-visible-
  interaction serialization rules.
- [ ] The coordinator alone fetches weather. A small adapter requests yr.no's
  Locationforecast 2.0 compact endpoint for fixed Linköping coordinates
  `58.4108,15.6214` and the `Europe/Stockholm` time zone; it exposes no raw
  response, coordinates, credential, or provider object through HTTP,
  server-sent events, or normal logs.
- [ ] The yr.no client sends a truthful identifying User-Agent, uses HTTPS and
  coordinates with no more than four decimal places, persists its `Expires`
  and `Last-Modified` cache metadata on the ThinkPad, and uses
  `If-Modified-Since` only after the cached response expires. A 203, 429,
  malformed, or unavailable response becomes safe unavailable Today state and
  never causes browser-to-yr.no traffic.
- [ ] Every endpoint connection receives a normalized `today.summary` snapshot
  with only time-zone, current-condition, forecast, availability, and observed
  time fields. A failed or unavailable provider reports an explicit unavailable
  summary and does not affect Music, Hue, coordinator health, or channel
  selection.
- [ ] The React shell renders Today and Music as explicit views without a
  router. Today shows a large local clock and date in the summary time zone,
  current condition and temperature, and the three-day forecast; it has a
  legible unavailable state with no stale weather presented as current and
  gives the required MET Norway / CC BY 4.0 attribution.
- [ ] Music retains its existing loaded, empty, stopped, and unavailable
  presentation. Playback, lighting, connection state, and temporary action
  feedback survive channel updates and endpoint reconnection independently.
- [ ] Channel selection visibly acknowledges the requested channel, shows the
  completed channel after the matching snapshot arrives, and makes a failed or
  unavailable interaction unmistakable without leaving a stale overlay over
  the selected view.
- [ ] Focused coordinator, HTTP/SSE, weather-adapter, and client reducer tests
  cover the accepted channel contract, invalid selections, reconnect snapshots,
  weather normalization and unavailability, view-state preservation, and
  interaction ordering without a live weather service or Hue bridge.
- [ ] Existing coordinator, endpoint, and frontend tests continue to pass;
  Python compilation, affected shell parsing, dependency integrity, frontend
  checks and build, production audit, and whitespace checks pass.
- [ ] The final issue record contains exact configuration, deployment,
  recovery, automated-check, and reviewer-owned live confirmation steps
  without credentials, network addresses, coordinates, or provider payloads.

## Tasks

### 1. Publish Concrete Channel And Today State

- Add `channel.active` and `today.summary` snapshots to the coordinator's
  connection and update path; keep the existing endpoint and Hue state
  contracts unchanged.
- Add `channel.select` to the existing request-ID lifecycle, including its
  accepted, matching-snapshot completion, busy, duplicate, validation, and
  endpoint-disconnected behavior.
- Add the narrow yr.no adapter for fixed Linköping coordinates, with its
  persisted cache metadata and a truthful identifying User-Agent; normalize
  provider values and recover from startup, request, and refresh failures
  without blocking the HTTP server.
- Cover the state, action, provider, HTTP, and SSE contracts with fakes.

### 2. Compose Two Explicit Channel Views

- Extend the client room reducer with independent active-channel and Today
  summary state, preserving playback, lighting, connection, and interaction
  updates.
- Keep one full-screen shell and switch only between explicit `Today` and
  `Music` view components; add no navigation framework or control surface.
- Present temporary channel-selection feedback above either view and retain the
  existing reconnect and Warm-scene feedback behavior.
- Cover reducer and presentation-state transitions, then document the exact
  local and deployed review path.

## Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep Channel Selection Coordinator-Owned And Concrete

- Decision: Represent only `today` and `music` as coordinator-owned active
  state, selected through one semantic action.
- Proposed approach: Publish an exact `channel.active` snapshot, validate the
  `channel.select` argument against the two accepted names, and complete the
  request after publishing its matching state. The client renders an explicit
  conditional view from that snapshot.
- Why: A later physical input and agent need one product action and observed
  result, while two views do not justify a router, registry, or plugin API.
- Alternatives: Client-local view state; URLs or a React router; one process or
  desktop per channel; a dynamic channel registry.
- Review focus: Action completion ordering, reconnect state, duplicate or busy
  requests, no endpoint dependency, and absence of a generalized framework.

### H2 - Normalize One Bounded Today Summary At The Coordinator

- Decision: Fetch weather behind one small adapter and publish a bounded,
  provider-neutral summary rather than provider data or browser requests.
- Proposed approach: Use yr.no's Locationforecast 2.0 compact endpoint from
  the ThinkPad with Linköping's fixed `58.4108,15.6214` coordinates and the
  `Europe/Stockholm` time zone. Send a truthful application and repository URL
  User-Agent, cache each response with its `Expires` and `Last-Modified`
  metadata, and conditionally refresh only after expiry. Normalize its instant
  temperature and symbol code plus the next three local calendar days into a
  summary; publish explicit unavailable state on failure.
- Why: yr.no supplies the required forecast without a browser credential or
  another runtime dependency. Its required coordinator-side caching and
  identification fit the existing local-first boundary, and fixed Linköping
  avoids location discovery or settings.
- Alternatives: Direct browser fetches; Open-Meteo or another weather API;
  provider-shaped events; weather polling from the iMac; a general provider
  framework.
- Review focus: yr.no attribution and traffic terms, truthful identification,
  cache expiry and conditional requests, Linköping and daylight-saving
  boundaries, symbol-code normalization, stale-data handling, bounded request
  and refresh failures, and no impact on the existing channels.

### H3 - Keep Persistent Room State Independent Of Channel Presentation

- Decision: Channel changes switch the visible view without discarding room
  state or temporary feedback.
- Proposed approach: Store active channel, Today, playback, lighting,
  connection, and interaction as separate reducer fields. Keep connection and
  interaction layers at the shared shell level.
- Why: A selected channel should not erase Music state, lighting feedback, or
  a reconnect notice, and the same ownership will make the Hue remote's later
  actions clear.
- Alternatives: Remount an isolated app per channel; duplicate connection and
  feedback logic; reset all state when changing views.
- Review focus: Event ordering while reconnecting, interaction-overlay
  lifetime, stale or unavailable Today state, narrow layouts, and reduced
  motion.

## Stylistic

### S1 - Let Today Be A Calm Glance, Not A Dashboard

- Choice: Give time and date the strongest hierarchy, then current weather,
  then three compact forecast cards and a quiet MET Norway attribution; use
  the existing warm, low-noise visual language.
- Alternative: Dense widget cards, equal visual weight, charts, or provider
  branding.
- When to apply: Use this hierarchy only for the explicit Today view. Do not
  turn it into a shared dashboard component before another channel proves that
  need.
