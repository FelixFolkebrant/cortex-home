# GH-008 Plan: Connect The Hue Bridge

## What

- Add pinned `aiohue` support to the ThinkPad coordinator without installing a
  general automation platform.
- Pair Cortex Home with the existing Hue bridge through its physical link
  button and keep the resulting application credential outside the repository.
- Maintain one local bridge connection that identifies availability, bridge
  generation, the room, scenes, and the existing remote for later issues.
- Qualify restart, reconnection, and manual Hue control before exposing a
  lighting action or client state.

## Out Of Scope

- Activating a scene or changing any lamp from Cortex Home.
- Publishing `room.lighting` to the endpoint client.
- Today, channel selection, or physical-button action mappings.
- Home Assistant, another automation platform, or direct raw Hue protocol code.
- Individual lamp controls, arbitrary entity browsing, history, automations, or
  a general device-adapter framework.
- Purchasing, pairing, or supporting another physical room controller.

## Deferred

- GH-009 will expose one semantic Hue scene action and observed lighting state
  after the bridge path is qualified.
- GH-010 will compose Today and Music with coordinator-owned channel state.
- GH-011 will map the existing remote to the accepted channel and scene actions
  after GH-008 records its supported events.
- Home Assistant remains deferred until another device family or cross-device
  behavior proves that it would remove more integration work than it adds.

## Acceptance Criteria

- [ ] The coordinator uses pinned `aiohue==4.8.1` from an isolated Python
  environment; no Home Assistant runtime or raw Hue client is added.
- [ ] A repository-owned operator command discovers the bridge locally, waits
  for deliberate physical link-button authorization, and stores the resulting
  application credential outside the repository without printing it.
- [ ] The credential and discovered bridge identity are readable only by the
  coordinator service and administrative users and are never committed,
  returned by HTTP, or written to normal logs.
- [ ] The adapter connects locally after unattended coordinator startup and
  records only the bridge generation and the minimum room, scene, and remote
  capabilities required by Planpoint 3.
- [ ] The exact existing remote model and its supported press events are
  qualified. If the bridge cannot expose them through `aiohue`, issue work stops
  and reopens Planpoint 3's input decision.
- [ ] Missing credentials, an unreachable bridge, rejected authentication, and
  an interrupted event connection produce distinct operational state without
  taking down Music or the coordinator HTTP service.
- [ ] Bridge and coordinator restarts recover without another link-button press
  or manual state repair.
- [ ] Stopping Cortex Home or making its adapter unavailable does not prevent
  the Hue app, the existing remote, or ordinary switches from controlling the
  lamps.
- [ ] Focused automated tests cover adapter startup, sanitized inventory,
  unavailable states, event interruption, and recovery without requiring the
  real bridge.
- [ ] Existing coordinator, endpoint, and frontend tests continue to pass;
  Python compilation, affected shell parsing, systemd verification, dependency
  integrity, and whitespace checks pass.
- [ ] The issue record contains exact pairing, deployment, credential,
  recovery, automated-check, and reviewer-owned live confirmation steps without
  bridge IDs, network addresses, application keys, or raw event transcripts.

## Tasks

### 1. Install One Isolated Hue Dependency

- Add the smallest repository-owned Python dependency file and build an
  isolated coordinator environment during installation.
- Run the service with that environment while keeping the existing stable
  coordinator deployment entry point.

### 2. Pair And Connect The Bridge

- Add one explicit pairing command that requires the bridge's physical button
  and writes a protected application credential on the ThinkPad.
- Add one Hue adapter around `aiohue`; keep library objects, resource IDs, and
  raw events inside it.
- Report clear unconfigured, connecting, connected, and unavailable operational
  state without exposing lighting state or actions yet.

### 3. Qualify The Existing Hardware

- Record the bridge generation and sanitized counts or names needed to select
  the room, one scene, and the existing remote.
- Confirm the remote's usable press events, bounded reconnection behavior, and
  manual Hue independence on the real system.
- Keep each diagnostic or monitoring window at 60 seconds or less.

## Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Add A Dependency Without Adding A Platform

- Decision: Install pinned `aiohue` in an isolated coordinator Python
  environment.
- Proposed approach: Keep one direct dependency declaration and update the
  existing installer and systemd service to use the isolated interpreter.
- Why: `aiohue` supplies maintained V1/V2 discovery, authentication, resources,
  and events. Home Assistant uses the same library, while implementing those
  boundaries or installing its whole platform would add avoidable ownership.
- Alternatives: Home Assistant Container; system Python packages; vendored
  dependencies; custom HTTPS and event-stream code.
- Review focus: Reproducible installation, host isolation, service startup,
  upgrade behavior, and retaining the stable deployment command.

### H2 - Keep One Adapter Thread, Not An Adapter Framework

- Decision: Bridge the asynchronous Hue client into the existing coordinator
  with one lifecycle owned by a small Hue module.
- Proposed approach: Run one bounded adapter lifecycle beside the threaded HTTP
  server and expose only operational state needed by this issue.
- Why: The coordinator must remain responsive when Hue is unavailable, but a
  reusable provider framework is not justified by one service.
- Alternatives: Rewrite the coordinator around an async framework; run a
  separate Hue service; add a generic adapter registry.
- Review focus: Startup and shutdown, thread safety, reconnect cancellation,
  event interruption, and tests that cannot leak background work.

### H3 - Treat Pairing Material As A Host Secret

- Decision: Create the Hue application credential only after physical bridge
  authorization and store it outside source control.
- Proposed approach: Use one explicit operator command and a fixed,
  least-readable host path consumed by the coordinator service.
- Why: Pairing is rare and physical by design. Configuration flexibility,
  browser-based onboarding, and logging the generated value would add exposure
  without improving normal operation.
- Alternatives: Commit a key; pass it on every deployment; create a web pairing
  flow; require interactive pairing on each restart.
- Review focus: File ownership and mode, command output, error messages,
  deployment preservation, and ensuring HTTP responses never include secrets.

### H4 - Preserve Manual Hue Independence

- Decision: Treat the Hue bridge as authoritative and Cortex Home as another
  replaceable client.
- Proposed approach: Observe bridge availability and recover the adapter without
  changing bridge-owned scenes, remote mappings, or other client access.
- Why: Cortex Home must fail without making the room difficult to control.
- Alternatives: Move existing Hue behavior into Cortex Home; make the
  coordinator the only allowed bridge client; recreate scenes during install.
- Review focus: Coordinator and bridge restarts, authentication rejection,
  existing remote behavior, Hue app control, and absence of destructive bridge
  configuration.
