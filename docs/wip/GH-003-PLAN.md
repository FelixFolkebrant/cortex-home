# GH-003 Plan: Provision The Room Endpoint

# What

- Add a small, repository-owned provisioning path for the qualified Ubuntu
  24.04 iMac.
- Install the Broadcom firmware and configure the home Wi-Fi without storing
  credentials or network identifiers in the repository.
- Start a dedicated, unprivileged endpoint account automatically in a minimal
  full-screen browser session.
- Provide a local keyboard shortcut to an unprivileged recovery terminal.
- Persist the rear analog audio route and prove playback through the Sonos.
- Verify unattended startup, browser recovery, remote administration, and the
  loaded kiosk resource, temperature, and fan spot baseline.

## Out Of Scope

- Implementing the coordinator, live web client, `endpoint.identify`, or
  correlated action feedback.
- Installing a general desktop environment or configuring the iMac for normal
  desktop use.
- General network audio, Spotify Connect, speech generation, microphone input,
  or audio mixing beyond the first endpoint sound.
- Changing the operating system, replacing hardware, or optimizing acceptable
  fan behavior.
- Committing Wi-Fi credentials, addresses, machine identifiers, SSH material,
  or raw host logs.

## Deferred

- GH-004 replaces the local qualification page with the real network client and
  owns its reconnect, visual feedback, and action behavior.
- GH-004 repeats active measurements while the real identify action runs;
  GH-003 records the steady full-screen placeholder baseline.
- General playback and mixing remain in Planpoint 2 because this issue only
  proves the sound path required by the first identify action.

## Acceptance Criteria

- [ ] The repository contains one understandable provisioning entry point and
  the exact static host files needed to reproduce the endpoint from the
  qualified Ubuntu base.
- [ ] Provisioning installs only the accepted endpoint packages, fails loudly,
  and can be rerun without duplicating users, files, or services.
- [ ] Broadcom firmware loads, the iMac joins the home Wi-Fi after reboot, and
  Ethernet remains available as a recovery path.
- [ ] Wi-Fi credentials and host-specific network or machine identifiers remain
  outside Git and are not printed in committed evidence.
- [ ] A dedicated, unprivileged endpoint account starts a 1920 × 1200
  full-screen browser automatically without exposing a normal desktop session.
- [ ] The endpoint session has intentional graphics and audio device access
  without granting administrative or remote-login access to the endpoint
  account.
- [ ] `Control`+`Option`+`Return` opens an unprivileged recovery terminal above
  the kiosk, and closing the terminal returns to the full-screen page.
- [ ] The rear analog route and mixer state survive reboot, and a test sound is
  audible through the Sonos rather than the iMac speakers.
- [ ] Exiting the browser causes it to recover automatically, and one controlled
  reboot returns both the full-screen endpoint and key-based SSH without local
  login or intervention.
- [ ] A post-reboot full-screen idle spot check records CPU load, memory use,
  temperatures, available fan readings, and subjective fan noise.
- [ ] Kiosk load, interaction readiness, display output, and sound latency are
  acceptable for GH-004, or the exact blocking result is recorded before
  application work begins.
- [ ] `docs/project/IDEA.md` contains the provisioned endpoint baseline and only
  genuinely unresolved facts remain under Open Facts.
- [ ] `docs/wip/GH-003.md` records commands, summarized results, decisions,
  automated checks, and explicit manual confirmation steps.

# Tasks

## 1. GH-003: Define The Minimal Endpoint Provisioning

- Add a plain shell provisioning entry point plus the fixed session, service,
  and qualification-page files it installs.
- Install Xorg, LightDM, Openbox, Chromium, the Radeon input support, Ubuntu's
  Broadcom STA driver, Avahi, Xterm, and existing ALSA tools without a desktop
  metapackage or recommended extras.
- Create a dedicated endpoint account and configure automatic startup into the
  local full-screen qualification page.

## 2. GH-003: Connect The Room Endpoint

- Accept the Wi-Fi name and password interactively, write them only to the
  protected host network configuration, and retain wired recovery.
- Give the endpoint session explicit graphics and audio device access, persist
  the intended rear-output mixer state, move the iMac into place, and verify the
  Sonos line-in.
- Reboot once and exercise browser-process recovery while confirming that SSH
  remains available without local intervention.

## 3. GH-003: Record The Kiosk Baseline

- Record a post-reboot resource, temperature, and fan spot check while the
  full-screen session is idle.
- Record subjective fan noise, display readiness, and test-sound latency without
  retaining raw identifying logs.
- Update the product baseline and issue record with observed results and the
  precise handoff to GH-004.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep Endpoint Provisioning Repository-Owned And Small

- Decision: How the replaceable iMac configuration is reproduced.
- Proposed approach: Use one fail-fast shell entry point and committed static
  files built from standard Ubuntu facilities. Do not introduce a configuration
  management framework for one endpoint.
- Why: The iMac must be replaceable, but one host does not justify a second
  orchestration layer or a flexible role system.
- Alternatives: Record manual commands only; introduce Ansible; create a
  general multi-host installer.
- Review focus: Every persistent endpoint change is visible in the repository,
  rerunning is safe, and the implementation contains no speculative options.

### H2 - Use A Minimal Xorg Kiosk Session

- Decision: Which graphical session GH-003 provisions before the real client
  exists.
- Proposed approach: Use LightDM automatic login for a dedicated endpoint
  account, Openbox as the minimal window manager, and Ubuntu's Chromium package
  in kiosk mode over Xorg. Install without recommended packages and show a
  local qualification page until GH-004 supplies the client URL.
- Why: Xorg uses the already qualified Radeon path and LightDM supplies a normal
  local login session with device access and recovery. Ubuntu offers Chromium
  through its supported Snap transition package. This avoids a desktop
  environment while keeping the first browser proof conventional.
- Alternatives: Cage and Wayland; a full desktop session; a bare systemd X
  service; Firefox; a custom native renderer.
- Review focus: Native panel resolution, automatic full-screen startup, browser
  restart behavior, package and memory cost, and whether the old Radeon remains
  stable.

### H3 - Keep Network Secrets On The Endpoint

- Decision: How provisioning supplies the home Wi-Fi configuration.
- Proposed approach: Prompt for the SSID and password during provisioning and
  write a root-readable Netplan file on the iMac. Commit neither values, and
  keep Ethernet configured for recovery.
- Why: Wi-Fi is required at the final location, but reproducing host
  configuration does not require publishing home-network credentials.
- Alternatives: Commit an encrypted secret; configure Wi-Fi manually without a
  reproducible entry point; replace Netplan with NetworkManager.
- Review focus: Neither command output nor Git history exposes credentials,
  Wi-Fi returns after reboot, and wired SSH still works.

### H4 - Prove The Smallest Audio Path

- Decision: Which audio services are installed for the identify proof.
- Proposed approach: Persist the ALC889A rear analog mixer state and first test
  playback through the unattended session using ALSA and the local browser
  qualification page. Add a user audio server only if the browser cannot use
  the qualified device directly, and record that as a plan diff.
- Why: Planpoint 1 needs one reliable sound, not a general routing or mixing
  stack. The server baseline already proved direct ALSA playback.
- Alternatives: Install PipeWire and WirePlumber preemptively; build network
  audio now; keep the internal speakers as the endpoint output.
- Review focus: State survives reboot, output reaches only the Sonos, playback
  works without local interaction, and any added audio layer is justified by an
  observed failure.
