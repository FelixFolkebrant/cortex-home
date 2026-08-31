# Cortex Home

Cortex Home is a local-first home interface for a one-room flat. A Lenovo
ThinkPad hosts coordination and durable state, while an old iMac acts as a
replaceable room display and nearby audio endpoint.

The first slice proves that the iMac can boot into a lightweight network client,
respond visibly and audibly to one ThinkPad-hosted action, and report success or
failure without exposing the system outside the home network.

## Current Hardware

- Coordinator: 2020 Lenovo ThinkPad running Ubuntu Server.
- Room endpoint: Apple `iMac8,1` running Ubuntu 24.04.4 LTS with hostname and
  administrative username `imac`.
- Room audio: Sonos Play:5 Gen 1 connected through its analog line-in.
- Lighting: Philips Hue bridge and three lamps.

The iMac's qualified hardware and operating-system baseline is recorded in
[PLT-001](docs/platform/issues/PLT-001.md).

## Project Documents

| Document | Purpose |
|---|---|
| [Documentation index](docs/README.md) | Module ownership, issue prefixes, and navigation |
| [General idea](docs/general/IDEA.md) | Product-wide intent and shared constraints |
| [General roadmap](docs/general/ROADMAP.md) | Current direction across modules |
| [Workflow](docs/general/WORKFLOW.md) | Lightweight module roadmaps and living issue records |

Each product area has its own IDEA, ROADMAP, active work, and completed issue
history below `docs/`.
