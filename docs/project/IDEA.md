# Cortex Home

## What

Cortex Home is a local-first home interface for a 28 m² one-room flat. It should
make the home feel responsive, tactile, and a little retro-futuristic without
becoming an always-listening "Jarvis" or replacing interactions that are
already faster on a phone or laptop.

The Lenovo ThinkPad is the always-on compute and coordination host. The
Early 2008-family iMac is intended to be a quiet, replaceable room endpoint:
primarily a display and, where useful, a connection point for nearby audio or
USB devices. It should not own durable state or perform work that can sensibly
run on the ThinkPad.

This repository is the system-level Crossroads project. It owns the product
intent, shared constraints, system decisions, integration contracts, and
roadmap. Candidate child projects are recorded here, but they are not split into
separate repositories until an independent deployment or maintenance boundary
has been demonstrated.

## Product Character

### Fun And Convenient

- Prefer interactions that are both useful and delightful.
- Combine visual, sound, and tactile feedback so every action has a clear
  response.
- Avoid keyboard, mouse, and touchscreen as normal room controls.
- Do not add voice or gesture control where a phone or laptop is plainly better.
- Let voice complement a visible interface instead of hiding the system behind
  a voice-only assistant.

### Gradually Extensible

- A new capability should be addable as a small, understandable module.
- Human, tactile, and future AI controls should invoke the same explicit system
  actions rather than grow separate control paths.
- The web interface should render observed system state. It must not trust an
  agent's claim that an action succeeded.
- Do not design a universal plugin system before two real modules prove what
  needs to be shared.
- Prefer existing device and media software over custom protocol
  implementations.

### Agent-Ready, Not Agent-Dependent

- Define a small catalog of semantic actions such as changing channel,
  activating a lighting scene, or controlling playback.
- Let the web app, physical controls, and agents invoke the same actions through
  one policy boundary on the ThinkPad.
- Stream interaction phase, action acknowledgement, observed state, and errors
  to the web app for live feedback.
- Give an agent structured context such as the active channel and exposed room
  state instead of asking it to infer state from pixels.
- Let agents navigate and populate predefined interfaces. New components and
  layouts are normal reviewed code changes, even when an agent helps create
  them during a development session.
- Require deliberate invocation in the first agent slice. Proactive behavior is
  not needed for the MVP.
- Keep model providers, speech engines, and agent protocols outside the core
  action contract so they can change without rewriting device or UI logic.
- Do not expose arbitrary shell access, browser control, administrative Home
  Assistant actions, or every discovered device to an agent.

## Candidate MVP

The exact MVP is not accepted yet. The current candidate is:

1. The iMac reliably presents a ThinkPad-controlled full-screen interface.
2. Channels can be changed without using a keyboard, mouse, or touchscreen.
3. A Today channel shows time, weather, and a small amount of genuinely useful
   daily context.
4. A Music channel shows what is playing.
5. Spotify on the iPhone can select a Cortex Home receiver and play through the
   Sonos line-in.
6. The three Philips Hue lamps can be controlled through a small set of
   room-level actions with immediate visible feedback.
7. A non-UI caller can invoke one allowed action and receive the same live
   feedback as the web interface.

## Candidate Later Capabilities

- Voice follow-up and hold-to-speak AI interaction.
- Physical knobs, buttons, claps, or other tactile inputs.
- General iPhone audio and screen casting.
- News, photos, quotes, stocks, local media, and TV channels.
- Camera-assisted presence or deliberate hand gestures.
- Fitbit-assisted interactions.
- A local music library.

These are directions, not promises. Each enters the roadmap only when it is
close enough to define as a useful vertical slice.

## User Flows

### Morning Glance

1. The iMac wakes or is already showing the Today channel.
2. The user sees time, weather, and today's most useful context at a distance.
3. The user can request more detail without first finding a phone.
4. The screen and voice response make it clear what the system understood.

### Play Spotify

1. The user opens Spotify on the iPhone.
2. The user selects the Cortex Home receiver.
3. Audio starts through the Sonos Play:5 line-in.
4. The iMac changes to or updates the Music channel with clear playback
   feedback.

### Change Channel

1. The user invokes a simple room-appropriate control.
2. The display immediately acknowledges the input.
3. The requested channel replaces the current channel.
4. A failed or unavailable channel is obvious rather than silently ignored.

### Control The Room

1. The user invokes a named room action such as a lighting scene.
2. The Hue bridge performs the device-level change.
3. The display or sound confirms the accepted action.
4. The interface reflects the resulting state.

### Ask A Follow-Up

1. The user deliberately starts a voice interaction while viewing a channel.
2. The current channel provides visible context to the assistant.
3. The assistant answers and may invoke the same explicit actions available to
   other controls.
4. Recording and processing state is always visible.

## Devices

| Device | Intended Role | Known Unknowns |
|---|---|---|
| 2020 Lenovo ThinkPad, Ubuntu Server | Always-on compute, coordination, and durable state | Exact model, ports, CPU, RAM, and current services |
| Apple `iMac8,1`, Ubuntu 24.04.4 LTS | Full-screen network client and likely nearby audio/USB endpoint | Kiosk load, thermals, power draw, persistent audio routing, and Wi-Fi after firmware installation |
| Sonos Play:5 Gen 1 | Speaker through its analog line-in | Currently near the iMac; a direct ThinkPad cable would require changing the physical layout |
| Philips Hue bridge and three lamps | Local lighting control | Bridge generation and existing room/scene setup |
| iPhone 17 | Personal controller, Spotify source, and possible casting source | None needed for the first slice |
| Google Fitbit | Possible later sensor/input | Exact model and accessible data |
| Anker conference microphone | Possible deliberate voice input | Exact model and preferred physical location |

### iMac Qualification Baseline

Inventory and server-idle behavior observed on 2026-07-23:

| Area | Observation |
|---|---|
| Identity | Apple `iMac8,1`; 24-inch panel; firmware `IM81.88Z.00C1.B00.0802091538` |
| Access | Hostname `imac`; administrative username `imac`; SSH confirmed working |
| Operating system | Ubuntu 24.04.4 LTS, x86-64 |
| Kernel | Linux `6.8.0-136-generic` |
| Processor | Intel Core 2 Duo E8235; two cores; 800 MHz to 2.8 GHz |
| Memory | 4 GiB installed RAM; 3.8 GiB usable RAM; 3.8 GiB swap |
| Storage | 1 TB WDC WD1002FAEX rotational disk; Optiarc DVD drive |
| Display | Internal 52 × 32 cm panel; native 1920 × 1200 mode; 32-bit `radeondrmfb` framebuffer |
| Graphics | AMD/ATI RV630/M76 Mobility Radeon HD 2600 XT/2700 using the `radeon` kernel driver |
| Audio | Intel HDA with ALC889A analog and digital playback devices using `snd_hda_intel` |
| Ethernet | Marvell 88E8058 using `sky2`; link up at 1 Gbit/s full duplex |
| Wi-Fi | Broadcom BCM4321 detected through `b43`; no wireless interface because `b43/ucode11.fw` is missing; Ubuntu provides `firmware-b43-installer` |
| USB | Intel ICH8 UHCI/EHCI USB 1.1/2.0 controllers; built-in Bluetooth, iSight, and infrared; Apple keyboard; wireless input receiver; no USB device required by Planpoint 1 |
| System health | No failed systemd services or currently indexed package upgrades |
| Fifteen-minute idle load | 97–100% CPU idle; 3.4 GiB memory available; no swap use |
| Fifteen-minute temperature | CPU cores 54–58°C; Radeon 75–77°C |
| Fifteen-minute fan speed | Optical drive 985–997 RPM; hard drive 1207–1211 RPM; CPU 1197–1201 RPM |
| Noise | Awaiting final subjective confirmation; the preliminary idle observation was quiet |
| Audio test | Separate internal-speaker and rear analog ALSA streams succeeded after temporarily unmuting `Master`; the user heard the internal speakers; Sonos playback awaits physical connection |
| Boot and recovery | A controlled reboot returned to SSH without local intervention; Ethernet was up and no services had failed at 38 seconds uptime |
| Unattended device access | After reboot with no local login, `imac` lacks `audio`, `video`, and `render` device access; GH-003 must provide an intentional endpoint session or service permission |

The server-only resource baseline is qualified. Measure power draw and repeat
the resource, temperature, fan, and noise observations with the full-screen
client running in GH-003. Machine ID, boot ID, network addresses, and other
host-specific identifiers are deliberately not recorded.

## Constraints

### C1 - Keep Compute On The ThinkPad

- Constraint: Run coordination, integrations, durable state, and expensive
  processing on the ThinkPad unless direct attachment makes a tiny endpoint
  process simpler.
- Why it matters: The iMac is old and resource-constrained. Its fans were quiet
  during the preliminary server-only baseline, but kiosk load is not yet known.

### C2 - Treat The iMac As Replaceable

- Constraint: The system must tolerate replacing the iMac endpoint without
  migrating its source of truth.
- Why it matters: Its age makes hardware failure plausible.

### C3 - Do Not Promise Fanless Operation

- Constraint: Measure idle temperature, fan speed, noise, and power before
  calling the endpoint quiet enough.
- Why it matters: Low software load cannot eliminate the iMac display,
  power-supply, storage, and minimum fan requirements.

### C4 - Local-First MVP

- Constraint: MVP control stays on the home network and does not require
  exposing an inbound public service.
- Why it matters: This reduces security, privacy, and availability decisions
  while the system is young.

### C5 - Explicit Sensing

- Constraint: Microphone and camera use must be deliberate, visibly indicated,
  and locally processed by default in the first agent slice.
- Why it matters: The system occupies a single private room.

### C6 - Clear Feedback

- Constraint: Every room interaction must visibly or audibly acknowledge
  receipt, success, and failure.
- Why it matters: Voice, gesture, and tactile controls lack the implicit
  feedback of a screen tap.

### C7 - Preserve Manual Control

- Constraint: Cortex Home must not make the Hue app, light switches, Spotify
  app, or ordinary device controls unusable.
- Why it matters: The experimental system must fail without making the room
  difficult to use.

### C8 - Defer Unproven Boundaries

- Constraint: Do not create separate repositories, a plugin framework, or a
  universal channel protocol until real slices demonstrate the boundary.
- Why it matters: Early approaches are expected to differ substantially.

### C9 - One Action Policy Boundary

- Constraint: Agents, interfaces, and physical inputs invoke the same
  allow-listed semantic actions through the ThinkPad coordinator.
- Why it matters: Parallel control paths would drift in permissions, behavior,
  and feedback.

### C10 - Feedback Follows Observed State

- Constraint: Distinguish an accepted command from the resulting device or
  interface state, and show failures explicitly.
- Why it matters: Immediate agent speech is not proof that a physical action
  happened.

## Open Facts

- iMac idle power draw, plus temperature, fan behavior, and power draw under
  kiosk load.
- Unattended audio and graphics device permissions, persistent mixer
  configuration, and end-to-end Sonos playback after the iMac moves into place.
- Wi-Fi operation after GH-003 installs the required Broadcom firmware and
  configures the home network.
- Exact ThinkPad model, available ports, and current services.
- Whether Spotify Premium is available; headless Spotify Connect receivers
  require it.
- Which interaction should switch channels in the first usable version.
