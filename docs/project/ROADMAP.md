# Roadmap

This roadmap stays deliberately loose. The first slices prove the old hardware
and the system seam before Cortex Home commits to a UI stack, automation
backbone, or repository split.

## Planpoints

### [1 CURRENT - Connected Room Endpoint](../planpoints/PP-1.md)

The ThinkPad produces one simple full-screen status view, the iMac presents it
reliably, and a test sound reaches the Sonos. An outside caller invokes one
allow-listed action and the web app shows acknowledgement, resulting state, and
failure over a live connection. The slice includes remote startup and recovery
plus measured iMac idle load, temperature, and noise.

| Crossroad | Decision | Alternatives Rejected |
|---|---|---|
| Parent repository boundary | Single integration repository through Planpoint 3 | Nested repositories; submodules; sibling repositories |
| iMac presentation path | Provisional local web client | Permanent desktop stream; direct display input |
| Shared system interaction boundary | Small Cortex Home coordinator | Direct client integrations; agent-owned orchestration |

This slice defines the minimum action and feedback shape that later interfaces
and agents inherit. It does not choose an agent provider, speech stack, broad
automation model, or child-repository layout.

### 2 - Spotify Music Channel

Spotify on the iPhone can select one Cortex Home receiver, audio plays through the
Sonos line-in, and the iMac shows useful now-playing feedback.

| Crossroad | Decision | Alternatives Rejected |
|---|---|---|
| Spotify Connect endpoint | ? | ? |
| Playback state source | ? | ? |

General system audio, synchronized multi-room audio, and a local music library
remain deferred.

### 3 - Today And Room Control

The iMac provides a useful Today channel and one room-level Hue action with
immediate state feedback. The same action can be called by the UI and one
non-screen input.

| Crossroad | Decision | Alternatives Rejected |
|---|---|---|
| Device and action authority | ? | ? |
| Channel presentation architecture | ? | ? |
| First room input | ? | ? |

This is the earliest point at which Home Assistant versus a custom control
service and a web shell versus a desktop compositor need acceptance.

### 4 - Deliberate Voice Agent Interaction

A hold-to-speak interaction can answer a contextual follow-up about the visible
channel and invoke one accepted room action with unmistakable listening,
working, success, and failure feedback.

| Crossroad | Decision | Alternatives Rejected |
|---|---|---|
| Agent runtime or framework | ? | ? |
| Speech processing boundary | ? | ? |
| Assistant action permissions | ? | ? |
| Voice privacy and retention | ? | ? |

Wake words, continuous listening, camera input, and general agent autonomy
remain deferred.

### 5 - Channel Expansion

Add channels one useful slice at a time. Current candidates are news, photos,
quotes, stocks, local media, and TV. A candidate becomes a Planpoint only when
its user flow and data source are clear.

| Crossroad | Decision | Alternatives Rejected |
|---|---|---|
| First independently deployed child project | ? | ? |

### Later Experiments

- iPhone audio and screen casting.
- Camera-assisted presence and deliberate gestures.
- Physical knobs, buttons, and clap input.
- Fitbit-assisted input.
- Local media and general video playback.

These experiments are not ordered and do not justify architecture in earlier
slices.

## Decision Heatmap

### C1 - Parent And Child Repository Boundary

- Decision: Whether this folder immediately becomes a parent Git repository
  containing separately versioned feature repositories.
- Options: One integration repository until boundaries emerge; nested Git
  repositories; Git submodules; a non-repository parent directory containing
  sibling repositories.
- Impact if wrong: Premature repositories create duplicated workflow, version
  coordination, and unclear ownership; a late split costs history and CI work
  but does not require rewriting the product.
- Proposed choice: Make this the single Cortex Home integration repository
  through at least Planpoint 3. Record candidate modules in the roadmap and
  extract only a service with an independently useful deployment lifecycle. Do
  not use nested repositories or submodules yet.
- Why: No stable feature or deployment boundaries have been demonstrated.
- Status: decided

### C2 - iMac Presentation Path

- Decision: How ThinkPad-hosted output reaches the iMac screen.
- Options: A lightweight full-screen web client on the iMac; whole-desktop
  streaming from the ThinkPad; a local web shell with on-demand streaming for
  channels that need native applications.
- Impact if wrong: The choice determines iMac OS requirements, endpoint compute,
  achievable video quality, recovery behavior, and which ports remain usable.
- Proposed choice: Use a local full-screen web client provisionally in
  Planpoint 1 and measure it on the real hardware. Keep on-demand
  Sunshine/Moonlight streaming as the escape hatch for a later native
  application or video channel rather than making a permanent desktop stream
  the system shell.
- Why: The installed system identifies itself as `iMac8,1`, an Early 2008
  family that does not support using the panel as a general external display. A
  simple local web client is cheaper and easier to recover than continuously
  decoding a streamed desktop.
- Status: decided

### H1 - iMac Operating System

- Decision: Which operating system, if any, the iMac runs as an endpoint.
- Options: Retain the current macOS temporarily; install a lightweight Linux
  kiosk; use a general-purpose Linux desktop.
- Proposed approach: Ubuntu 24.04.4 LTS is now installed. Qualify the detected
  graphics, audio, network, temperature, and fan behavior before installing
  only the kiosk dependencies. Keep Debian stable as a fallback if the iMac
  exposes an Ubuntu-specific hardware or packaging problem.
- Why: The current macOS installation and its data have no value to preserve, so
  a failed Linux attempt costs time rather than valuable state. Matching the
  homelab also reduces operational variation more than a slightly smaller base
  system would reduce endpoint load.
- Alternatives: Debian stable for a leaner traditional-package base; Arch for a
  minimal rolling system; keep unsupported macOS; install a full desktop.
- Review focus: Native graphics, Ethernet, audio output, temperature and fan
  behavior, USB devices, unattended boot, and browser performance.

### H2 - Audio Attachment

- Decision: Which computer is physically responsible for the Sonos analog
  line-in.
- Options: Connect the Sonos directly to the ThinkPad; keep it connected to the
  iMac and run a small playback endpoint there; transport all ThinkPad audio to
  the iMac over the network.
- Proposed approach: Keep the Sonos attached to the iMac and run the smallest
  playback endpoint there. Generate speech and perform expensive processing on
  the ThinkPad, then send only the audio output to the endpoint.
- Why: The devices are not currently close enough for direct cabling. Keeping
  audio input/output at the room endpoint may also make microphone feedback,
  speech playback, and music mixing simpler, provided the measured endpoint load
  stays low.
- Alternatives: Run a long analog cable from the ThinkPad; move the machines;
  build general network-audio routing immediately.
- Review focus: Confirm that endpoint load, latency, and audio mixing remain
  acceptable before later media features inherit the route.

### C5 - Device And Action Authority

- Decision: Whether an established home-automation system or Cortex Home's own
  service owns device state and actions.
- Options: Home Assistant as the authority with a custom Cortex Home interface; a
  custom service talking directly to each device; independent per-channel
  integrations.
- Impact if wrong: Device identity, automation, history, permissions, and future
  AI actions would be expensive to migrate.
- Proposed choice: Evaluate Home Assistant as the authority in Planpoint 3,
  while keeping Cortex Home's visual experience separate. Do not build direct Hue
  plumbing before that comparison.
- Why: Existing local integrations and explicit action APIs may provide the
  modular control seam without forcing the Home Assistant dashboard to become
  the product UI.
- Status: open

### C6 - Channel Presentation Architecture

- Decision: How channels are composed and switched.
- Options: One full-screen web shell with routes; a compositor/window-manager
  session launching mixed applications; isolated desktops or VMs; a hybrid.
- Impact if wrong: Every channel inherits the runtime, navigation, deployment,
  and hardware-access model.
- Proposed choice: Prove a small web shell in Planpoint 1, but accept the
  long-term choice only in Planpoint 3. Hardware access belongs behind server
  actions, so it does not require browser hardware APIs. Add a native or streamed
  escape hatch only when a real channel cannot fit.
- Why: Hyprland, multiple native apps, and VMs solve flexibility that the first
  channels do not yet require.
- Status: open

### C7 - Later Agent Trust Boundary

- Decision: At Planpoint 4, choose when microphones and an AI agent may observe
  or act and which capabilities the selected runtime receives.
- Options: Explicit activation and allow-listed actions; wake-word activation;
  continuous sensing; broad agent tool access.
- Impact if wrong: Privacy and trust are difficult to restore after the system
  behaves unexpectedly in a one-room home.
- Proposed choice: For the first agent slice, use explicit activation, visible
  sensing state, and allow-listed actions. Revisit wake words, proactive
  behavior, and camera activation only if a later user flow needs them.
- Why: This preserves the playful interaction goal without making ambient
  surveillance a prerequisite.
- Status: open

### C8 - Shared Control Boundary

- Decision: How the web app, physical inputs, audio interaction, and future
  agents observe and control Cortex Home without creating separate behavior paths.
- Options: Each client talks directly to Home Assistant and media services; use
  Home Assistant as the entire application contract; place a small Cortex Home
  coordinator in front of device, media, and display adapters.
- Impact if wrong: UI state, device results, agent permissions, and audio
  feedback could diverge, forcing every feature to be rewritten when a new
  control surface is added.
- Proposed choice: Run a small Cortex Home coordinator on the ThinkPad. It owns the
  active channel, interaction phase, allow-listed action catalog, and feedback
  stream. It delegates through narrow adapters to the accepted device authority,
  media service, and web client.
- Why: Home Assistant is a good device authority but channels and multimodal
  interaction are product state. One narrow boundary lets a web app, physical
  control, or agent call the same action and observe the same result without
  making the AI model the orchestrator.
- Status: decided

## Proposed Interaction Plumbing

```text
Web app ───────┐
Physical input ├── action request ──> Cortex Home coordinator ──> adapter/service
Agent adapter ─┘                           │                       │
                                          └── live feedback <─────┘
                                                   │
                                      web UI, audio, action caller
```

Planpoint 1 should thread only one small shape through this path:

1. A caller sends an action name, validated arguments, and a request ID.
2. The coordinator reports that the action was accepted or rejected.
3. The responsible adapter performs the action.
4. The coordinator publishes observed state or a clear failure associated with
   the request ID.
5. The web app updates immediately; an audio acknowledgement may use the same
   event.

The live web connection can use WebSockets. A later agent adapter may translate
the same action catalog into Home Assistant LLM tools, MCP tools, or a
provider-specific tool format. Those are adapters, not the source of truth.

## Deferred Agent Decisions

None of these choices is required for Planpoints 1–3:

- Pi, OpenClaw, LangChain, a small hand-written agent loop, or another runtime.
- Local versus hosted language model and the specific model provider.
- Home Assistant LLM tools, MCP, or provider-specific tool calling.
- Speech-to-text and text-to-speech engines.
- Conversation memory and persistence.
- Wake word, proactive initiation, and camera context.
- Any reusable visual components beyond those demanded by a real channel.

Deferring is safe because the runtime will receive structured context and call
the coordinator's allowed actions through an adapter. Planpoint 4 should compare
agent runtimes against one concrete flow instead of selecting one from feature
lists in advance.

## Proposed Cooling Order

1. Identify the hardware and physical cable constraints.
2. Decide C1 for Planpoint 1; use PP-1 to validate C2; C8 is decided.
3. Prove one screen, one sound, and one state/action round trip end to end.
4. Decide Spotify-specific choices for Planpoint 2.
5. Decide C5 and C6 using evidence from the first two slices.
6. Revisit C1 only when a module has an independent deployment lifecycle.
7. Decide C7 immediately before deliberate voice work.
