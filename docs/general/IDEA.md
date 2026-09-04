# Cortex Home

## Purpose

Cortex Home is a local-first home interface for a one-room flat. It turns a
small collection of existing devices into a playful, understandable room
computer without making an AI model or a hosted service the owner of the home.

The system should be useful through its persistent Home surface and ordinary
keyboard controls even when voice, internet services, or individual
integrations are unavailable.

## Product Character

### Fun And Convenient

- The room display should feel intentional from across the room rather than
  like a general desktop or an administration panel.
- Common actions should be quick, visible, and easy to recover from.
- New capabilities should earn their place through a real user flow.

### Gradually Extensible

- Add one useful module or integration at a time.
- Keep module boundaries concrete and avoid speculative plugin systems.
- Prefer normalized product actions and state over leaking provider objects or
  hardware identifiers through the system.

### Agent-Ready, Not Agent-Dependent

- The coordinator, visible surfaces, and manual controls remain authoritative.
- Voice and future agents receive explicit, narrow context and permissions.
- Sensing is deliberate and visible; recordings and conversation state are not
  retained unless a later accepted feature explicitly requires it.

## System Shape

- A 2020 Lenovo ThinkPad running Ubuntu Server owns coordination, integrations,
  expensive processing, and durable state.
- An Ubuntu `iMac8,1` is a replaceable room display and local audio/video
  endpoint.
- A Sonos Play:5 Gen 1 receives analog room audio from the iMac.
- A Philips Hue bridge remains the authority for three room lamps and their
  scenes.
- One React client composes normalized room state on Home and enters only
  deliberate temporary modes while the coordinator accepts allow-listed
  actions.

Detailed hardware and deployment facts belong to the
[Platform module](../platform/IDEA.md). Surface-specific behavior belongs to the
corresponding module rather than this document.

## Shared Constraints

- Keep the MVP reachable only on the home network unless a later feature
  deliberately changes that boundary.
- Keep compute-heavy work on the ThinkPad when the room endpoint does not need
  to own it.
- Treat the iMac as reproducible and replaceable; do not place unique durable
  state there without a clear reason.
- Preserve manual Hue, Spotify, endpoint recovery, and keyboard control when
  Cortex Home components fail.
- Show accepted work, observed completion, and failure honestly. Do not claim
  success from a command alone when the integration can report resulting state.
- Avoid broad action, shell, browser, or device access when one exact product
  operation is sufficient.

## Modules

The current product is divided into Platform, Shell, Today, Music, Lighting,
Voice, Camera, AirPlay, and Alarm. Their IDEA and ROADMAP documents are the
sources of truth for module behavior and direction. General documentation owns
only decisions that genuinely span those modules.
