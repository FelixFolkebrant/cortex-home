# GH-005 Plan: Provision The Spotify Receiver

## What

- Add repository-owned provisioning for one named Raspotify receiver on the
  qualified iMac.
- Pin and validate the reviewed Raspotify package before installing it.
- Share the endpoint user's existing PulseAudio route so Spotify and Chromium
  do not compete for direct ALSA access.
- Deploy the receiver and qualify discovery, Sonos playback, recovery, and
  resource use on the real endpoint.

## Out Of Scope

- Playback metadata or state in the coordinator and web client.
- Cortex Home playback controls.
- General network audio, multi-room audio, AirPlay, or Bluetooth.
- A Music channel UI.

## Deferred

- Normalized receiver events move to GH-006 after the receiver itself is
  qualified.
- The Music view moves to GH-007 after coordinator playback state exists.
- A general audio transport remains deferred until another source or room
  requires it.

## Acceptance Criteria

- [ ] The main iMac provisioning path installs the reviewed `amd64` Raspotify
  package only after its package name, version, architecture, dependency, and
  checksum pass.
- [ ] Provisioning is fail-fast and rerunnable without committing credentials
  or host identity.
- [ ] Raspotify runs as the unprivileged `cortex-endpoint` user and sends audio
  through that user's existing PulseAudio session.
- [ ] Spotify on the iPhone discovers exactly one receiver named `Cortex Home`.
- [ ] Selecting `Cortex Home` plays Spotify through the Sonos line-in rather
  than the iMac speakers.
- [ ] Chromium's identify signal still plays through the Sonos after Raspotify
  is installed.
- [ ] Service failure is visible, and service or endpoint-session restart
  restores the receiver without reinstalling it.
- [ ] A playback sample of no more than 60 seconds records CPU, memory, and
  receiver RSS without retaining host identifiers or raw logs.
- [ ] Repository shell, systemd, and whitespace checks pass.
- [ ] The issue record contains exact automated and reviewer-owned manual
  confirmation steps.

## Tasks

### 1. Accept The Local Spotify Receiver

- Record the accepted Raspotify-on-iMac placement in Planpoint 2 and the
  roadmap.
- Keep the playback-state Crossroad open for GH-006.

### 2. Provision The Spotify Receiver

- Add the reviewed package guard, receiver configuration, and systemd override
  to the existing iMac provisioning path.
- Document the receiver behavior and deployment command.

### 3. Qualify The Live Receiver

- Deploy to the iMac, confirm service and discovery state, and record a bounded
  playback resource sample.
- Leave physical sound and iPhone interaction as explicit reviewer
  confirmations.

## Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Share The Endpoint PulseAudio Session

- Decision: Run Raspotify as `cortex-endpoint` with its PulseAudio backend.
- Proposed approach: Override the packaged system service user and runtime
  environment while retaining its remaining sandbox and managed directories.
- Why: Chromium already uses the endpoint user's PulseAudio session. The
  package's root-owned direct ALSA default could make Spotify and identify
  playback contend for the same device.
- Alternatives: Use direct ALSA and accept exclusive playback; add a system
  PulseAudio daemon; transport decoded audio from the ThinkPad.
- Review focus: Startup ordering, socket access, service hardening, and mixed
  Spotify and identify playback.

### H2 - Fail When The Reviewed Package Changes

- Decision: Provision one reviewed Raspotify build rather than silently
  installing whatever `latest` becomes.
- Proposed approach: Download the architecture-specific upstream package and
  validate its metadata and SHA-256 checksum before `apt` installs it.
- Why: Raspotify does not publish a versioned Ubuntu repository path for this
  host, while an unreviewed package update could change dependencies, service
  hardening, or librespot behavior.
- Alternatives: Add the Raspotify apt repository; install the unverified latest
  package; build librespot in this repository.
- Review focus: Clear failure output and a straightforward reviewed-version
  update.
