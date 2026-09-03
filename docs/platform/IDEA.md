# Platform

## Purpose

Platform makes the Cortex Home runtime reproducible and keeps the old room
hardware understandable. It owns the ThinkPad coordinator service, the iMac
endpoint, deployment and provisioning, networking boundaries, recovery paths,
and shared audio and media access.

## Current Topology

- The ThinkPad runs the Python coordinator, serves the built React client,
  owns integrations and durable state, and supervises the Node agent child.
- The `iMac8,1` runs Ubuntu 24.04 LTS, LightDM, Openbox, and a full-screen
  Chromium session at 1920 × 1200.
- The iMac is a replaceable endpoint. Repository provisioning reconstructs its
  kiosk, network, native helpers, permissions, and audio route.
- The Sonos Play:5 Gen 1 receives the iMac rear analog output. Chromium,
  Raspotify, speech playback, AirPlay, and alarms share that selected route.

## Boundaries

- Keep secrets, deployment addresses, machine identity, and private evidence
  outside Git.
- Keep the coordinator LAN-only and the endpoint control bridge bound to
  loopback and the configured coordinator origin.
- Prefer narrow root-owned endpoint helpers over a general privileged API.
- Keep endpoint state disposable unless a feature explicitly requires local
  files, such as selectable alarm audio.
- Preserve SSH and an unprivileged recovery terminal when the kiosk fails.

## Relevant Code

- `coordinator/`: service runtime, integrations, and browser client.
- `endpoint/imac/`: native helpers, configuration, and endpoint tests.
- `ops/`: Ansible inventory example, playbooks, and shared host-provisioning
  roles.
