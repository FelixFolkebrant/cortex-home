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
[`IDEA.md`](docs/project/IDEA.md#imac-qualification-baseline).

## Project Documents

| Document | Purpose |
|---|---|
| [`IDEA.md`](docs/project/IDEA.md) | Product intent, hardware, user flows, and constraints |
| [`ROADMAP.md`](docs/project/ROADMAP.md) | Current direction and deferred decisions |
| [`PP-1.md`](docs/planpoints/PP-1.md) | Current connected-room-endpoint slice |
| [`GH-001-PLAN.md`](docs/wip/GH-001-PLAN.md) | Current repository-bootstrap issue plan |

Cortex Home uses the Crossroads workflow described in
[`WORKFLOW.md`](docs/project/WORKFLOW.md).
