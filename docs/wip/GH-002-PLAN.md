# GH-002 Plan: Qualify The iMac Endpoint

# What

- Complete the `iMac8,1` hardware inventory without recording host-specific
  identifiers.
- Measure sustained server-idle CPU, memory, temperature, and fan behavior.
- Verify the installed Ubuntu system can use the graphics, Ethernet, USB, and
  audio hardware needed by the room endpoint.
- Qualify the installed Wi-Fi hardware far enough to identify any provisioning
  required before the iMac can move to its intended room location.
- Determine which local audio output reaches the Sonos line-in and whether it
  needs explicit ALSA or mixer configuration.
- Verify the machine can reboot unattended and return to remote administration.
- Record reproducible evidence and the remaining risks that GH-003 must address.

## Out Of Scope

- Installing a graphical session, browser, kiosk, coordinator, or web client.
- Persistently configuring full-screen startup, audio routing, networking, or
  recovery services.
- Installing wireless firmware or connecting the iMac to the home Wi-Fi.
- Measuring full-screen client load; GH-003 performs that measurement with the
  actual endpoint software installed.
- Implementing the identify action or its visual and audible feedback.
- Replacing Ubuntu, changing hardware, or publishing machine and network
  identifiers.

## Deferred

- Endpoint packages and persistent host configuration remain in GH-003 because
  this issue establishes the baseline they must improve without conflating
  observation with provisioning.
- Active kiosk CPU, memory, temperature, fan noise, and browser behavior remain
  in GH-003 because a representative client does not exist yet.
- End-to-end Sonos playback remains in GH-003 because the Sonos cannot be
  physically connected until Wi-Fi provisioning allows the iMac to move into
  place. GH-002 still validates the iMac's analog output path.
- The correlated visual and audio action path remains in GH-004 because it
  depends on a provisioned endpoint.

## Acceptance Criteria

- [ ] The exact iMac screen size, CPU, installed memory, graphics adapter,
  storage device and capacity, Ethernet adapter, audio devices, and relevant USB
  controllers are recorded.
- [ ] Ubuntu release, kernel, firmware, loaded hardware drivers, failed services,
  and available package updates are inspected, with endpoint-relevant problems
  recorded.
- [ ] A sustained idle sample of at least fifteen minutes records CPU load,
  memory use, temperatures, available fan readings, and subjective fan noise.
- [ ] Ethernet link state and post-reboot SSH recovery are confirmed without
  storing addresses, keys, machine IDs, or other host-specific identifiers.
- [ ] The Broadcom wireless hardware and driver path are inspected; any missing
  firmware or configuration required by GH-003 is identified precisely.
- [ ] Graphics and display detection are confirmed using the installed system
  without installing the kiosk stack.
- [ ] Internal audio and the rear analog output are tested separately; the
  working route or exact failure and the configuration GH-003 must supply are
  recorded. End-to-end Sonos playback is deferred until physical connection is
  possible.
- [ ] Relevant attached USB devices are enumerated and any device needed by the
  current Planpoint is tested.
- [ ] The controlled reboot returns the iMac to an administrable state without
  local login or intervention.
- [ ] `docs/project/IDEA.md` contains the completed qualification baseline and
  only genuinely unresolved facts remain under Open Facts.
- [ ] `docs/wip/GH-002.md` records commands, summarized results, decisions,
  automated checks, and explicit manual confirmation steps.

# Tasks

## 1. GH-002: Record The iMac Hardware Baseline

- Collect a sanitized, reproducible inventory of the display, CPU, memory,
  graphics, storage, network, audio, and USB hardware.
- Inspect Ubuntu, driver, service, and package health without changing the
  endpoint.
- Run and record the sustained server-idle resource, temperature, and noise
  baseline.
- Update the project baseline and issue record with observed facts.

## 2. GH-002: Validate Endpoint Hardware Paths

- Verify display detection and the loaded graphics path.
- Test the internal audio output and rear analog output independently,
  including mixer state; defer end-to-end Sonos playback until the physical
  connection exists.
- Verify Ethernet, qualify the Wi-Fi hardware and driver path, inspect relevant
  USB devices, and confirm unattended return to SSH after one controlled
  reboot.
- Record the working paths, precise failures, and the provisioning requirements
  handed to GH-003.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep Qualification Non-Persistent

- Decision: Separate hardware qualification from endpoint provisioning.
- Proposed approach: Use read-only inspection and temporary playback or device
  tests. Do not install packages or persistently change boot, network, mixer, or
  service configuration in this issue.
- Why: A clean baseline makes GH-003's effects measurable and prevents
  exploratory host changes from becoming undocumented configuration.
- Alternatives: Configure each subsystem while testing it; provision the whole
  endpoint as part of qualification.
- Review focus: Every endpoint change must either disappear when its test ends
  or be moved to GH-003.

### H2 - Store Evidence Without Host Identity

- Decision: Decide which qualification evidence belongs in the repository.
- Proposed approach: Record hardware models, driver names, software versions,
  summarized measurements, test commands, and outcomes. Exclude addresses,
  serial numbers, UUIDs, machine and boot IDs, SSH material, and raw logs that
  contain them.
- Why: Future provisioning needs reproducible technical facts, not identifiers
  that expose the home network or a particular installation.
- Alternatives: Commit complete command output; record only prose conclusions.
- Review focus: The record must be useful for reproducing decisions while
  remaining safe in a public repository.
