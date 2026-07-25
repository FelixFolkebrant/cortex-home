# PP-2: Spotify Music Channel

## Slice

Spotify on the iPhone can select a Cortex Home receiver, play through the Sonos
line-in, and make the iMac show observed now-playing state.

- A named Spotify Connect receiver starts unattended on the room endpoint.
- Selecting it in the Spotify iPhone app sends audio through the iMac's existing
  rear analog route to the Sonos.
- The receiver reports playback, pause, track, position, and failure events to
  the ThinkPad coordinator.
- The iMac shows useful track, artist, artwork, progress, and availability
  feedback from coordinator-owned observed state.
- Receiver and display recovery are tested without making the Spotify app or
  Sonos unusable when Cortex Home is unavailable.
- Added endpoint load and playback behavior are measured on the real hardware.

This is the smallest real channel that exercises the qualified audio endpoint
and turns the provisional identify screen into a useful room display.

Acceptance requires an active Spotify Premium account. The existing working
Raspotify setup confirms that prerequisite. It also requires accepting an
unofficial Spotify Connect implementation: librespot states that it only
supports Premium and that using it may be prohibited by Spotify.

## Out Of Scope

- Starting, pausing, seeking, skipping, or changing volume from Cortex Home.
- Spotify browsing, search, queue editing, playlists, lyrics, or account UI.
- General iPhone audio, AirPlay, Bluetooth, local music, or other media sources.
- Synchronized multi-room audio or Sonos network control.
- A permanent channel navigation or presentation architecture.
- Automatic switching away from Music when playback stops.
- Public internet access to the coordinator.

## Deferred To Later Planpoints

- The Today channel, Hue actions, channel navigation, and the long-term channel
  presentation architecture remain in Planpoint 3 because this slice only needs
  one provisional Music view.
- Agent-driven media actions remain deferred until Planpoint 4 establishes the
  agent trust boundary.
- General audio, other media providers, a local library, and multi-room playback
  remain later experiments because Spotify alone does not prove a shared media
  abstraction.

## Crossroads

### C1 - Spotify Connect Endpoint

- Decision: Which process becomes the selectable Cortex Home receiver and where
  it runs.
- Options: Run standalone librespot on the iMac; make the Chromium client a
  receiver with Spotify's Web Playback SDK; run a receiver on the ThinkPad and
  add general network-audio transport to the iMac.
- Impact if wrong: The choice fixes the authentication, credential, audio,
  recovery, and endpoint-resource boundaries that later music work inherits.
- Proposed choice: Install a reviewed Raspotify package on the iMac and run its
  bundled librespot receiver as an unattended service using zero-conf discovery
  and the already qualified local audio route. Store any receiver credentials
  outside the repository with owner-only permissions.
- Why: The iMac is directly attached to the Sonos, and Raspotify is a thin
  systemd wrapper around the already proven librespot receiver. Local playback
  avoids adding browser playback, a Spotify developer application, or general
  network audio. The tradeoff is deliberate: librespot is unofficial, requires
  Premium, and warns that its Spotify API use may be prohibited.
- Status: decided

### C2 - Playback State Source

- Decision: Which observation the Music view trusts as the state of the room
  receiver.
- Options: Normalize librespot's local playback events; poll Spotify's Web API
  from the ThinkPad; infer playback from browser or audio activity.
- Impact if wrong: Now-playing feedback could lag, represent another Spotify
  device, require a second account integration, or claim playback that the room
  endpoint did not perform.
- Proposed choice: Treat librespot's local events as the authoritative
  observation for this receiver. A small endpoint adapter forwards normalized
  snapshots to the coordinator, which owns the current in-memory state and
  publishes it to the web client.
- Why: Librespot exposes track metadata and playing, paused, stopped, seek,
  position-correction, volume, and unavailable events from the process that
  actually feeds the Sonos. Spotify's Web API would add OAuth, cloud polling,
  rate limits, and device filtering without improving this slice's source of
  truth.
- Status: open

## Plumbing

- Threaded now: a `music.playback` snapshot carries `status`, `item`, and
  `positionMs` from the iMac receiver adapter through the coordinator to the
  full-screen client. `item` is absent when nothing is loaded and otherwise
  contains the Spotify URI, item type, title, creators, collection, artwork URL,
  and duration.
- Pattern set: An endpoint or service adapter reports observed state to the
  coordinator; the coordinator retains the latest snapshot and publishes it to
  subscribed interfaces. Provider events and credentials do not become the
  client contract.

## Issues

1. **GH-005 - Provision The Spotify Receiver**: install a pinned Raspotify
   receiver on the iMac, route it through the existing Sonos output, and qualify
   discovery, unattended startup, recovery, and endpoint load.
2. **GH-006 - Publish Spotify Playback State**: normalize receiver events into
   `music.playback` snapshots and carry availability, metadata, progress, and
   failures through the coordinator.
3. **GH-007 - Present The Music Channel**: replace the provisional idle view
   with a useful now-playing display while preserving identify and connection
   feedback.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: Spotify Connect endpoint; see Crossroads section.
- C2: playback state source; see Crossroads section.

### Hot

#### H1 - Keep The Receiver At The Attached Audio Endpoint

- Decision: Let the iMac perform only Spotify reception and playback while the
  ThinkPad retains normalized state and coordination.
- Why: Direct local playback avoids introducing a general network-audio layer
  and fits the accepted exception for a tiny process serving attached hardware.
- Alternatives: Decode on the ThinkPad and transport audio; move the Sonos
  cable; make Chromium own playback.

#### H2 - Keep The First Music View Read-Only

- Decision: Show observed playback and availability without adding Cortex Home
  playback controls.
- Why: Selecting and controlling the receiver in Spotify already satisfies the
  user flow. Read-only state proves the channel seam before another action and
  permissions surface is needed.
- Alternatives: Add transport controls now; mirror the complete Spotify player;
  show only track text without playback state.
