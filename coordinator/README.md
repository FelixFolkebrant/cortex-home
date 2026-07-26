# Coordinator

Install the coordinator from a machine that can reach the Ubuntu server over
SSH:

```sh
./coordinator/install <server-ssh-host>
```

The SSH destination is supplied at runtime so the server hostname or address
does not enter Git. The installer uses pnpm to build the React client, copies
only the production artifacts and coordinator to `/opt/cortex-home`, installs
`aiohue==4.8.1` in `/opt/cortex-home/venv`, installs `cortex-home.service`, and
starts the coordinator on port 8080. Node.js and pnpm are build-time
dependencies only. The server requires Python 3.11 or later with `venv`
support.

After the first deployment, pair the coordinator with the Hue bridge from a
machine that can reach the server over SSH:

```sh
./coordinator/pair-hue <server-ssh-host> <bridge-host>
```

The command validates the supplied local bridge host, asks for a deliberate
link-button press, and stores the application credential at
`/etc/cortex-home/hue.json` on the server. It prints only room, scene, remote
model, and advertised remote-event details, then observes sanitized remote
presses for 60 seconds. It never prints the bridge identity or application key.
The fixed credential file is owned by `root:cortex-home` with mode `0640` and
survives ordinary coordinator deployments.

`GET /api/health` reports Hue as `unconfigured`, `connecting`, `connected`,
`unreachable`, `unauthorized`, `event_interrupted`, or
`invalid_configuration`. These states do not change Music behavior or the
coordinator HTTP status.

Today uses yr.no's Locationforecast 2.0 compact endpoint for fixed Linköping
coordinates. Only the ThinkPad calls yr.no; it identifies Cortex Home with the
repository URL, caches the response and its expiry metadata at
`/var/cache/cortex-home/locationforecast.json`, and conditionally refreshes it
after expiry. The endpoint receives only normalized current conditions and a
three-day forecast, then displays the required MET Norway / CC BY 4.0
attribution. If the forecast cannot be refreshed, Today says weather is
unavailable without changing Music, Hue, or the coordinator health endpoint.

For local development, start the coordinator:

```sh
python3 coordinator/cortex_home.py --host 127.0.0.1
```

Then start the Vite client in another terminal:

```sh
pnpm --dir coordinator/client install
pnpm --dir coordinator/client dev
```

Run the automated checks with:

```sh
python3 -m unittest discover -s coordinator/tests
python3 -m unittest discover -s endpoint/imac/tests
pnpm --dir coordinator/client check
pnpm --dir coordinator/client test
pnpm --dir coordinator/client build
```

With the endpoint connected, an outside caller can invoke its identify action:

```sh
curl \
  --fail-with-body \
  --header 'Content-Type: application/json' \
  --data '{"requestId":"manual-1","action":"endpoint.identify"}' \
  http://<server-host>:8080/api/actions
```

The request remains open until the endpoint reports completion or failure. The
JSON response carries the same request ID. Use a new request ID for every
invocation while the coordinator process remains running.

An outside caller can activate any detected scene in room `Rum` by its exact
name, even when the endpoint is disconnected:

```sh
curl \
  --fail-with-body \
  --header 'Content-Type: application/json' \
  --data '{"requestId":"relax-1","action":"room.scene.activate","scene":"Relax"}' \
  http://<server-host>:8080/api/actions
```

The action accepts one exact name from the current `room.lighting` scene
catalog, but no room or Hue resource identifier. It remains open until a later
Hue event reports that scene active, the 10-second action bound expires, or the
adapter reports an unavailable or rejected command. Every request needs a new
request ID.

An outside caller can select the room's active view even while the endpoint is
reconnecting:

```sh
curl \
  --fail-with-body \
  --header 'Content-Type: application/json' \
  --data '{"requestId":"show-music-1","action":"channel.select","channel":"music"}' \
  http://<server-host>:8080/api/actions
```

The only accepted channel values are `today` and `music`. The coordinator
starts on Today, publishes the selected `channel.active` snapshot to every
endpoint connection, and returns completion after it publishes that state.
On the room display, `Ctrl`+`Alt`+`1` selects Today and `Ctrl`+`Alt`+`2`
selects Music through that same action. `Ctrl`+`Alt`+`S` activates the next
detected room scene in case-insensitive name order and wraps after the last
scene. Other key combinations and repeated key presses do nothing. The Hue
remote remains exclusively native to Hue; Cortex Home does not subscribe to
its button events.

For a focused deployed check, use the repository-owned verifier with one exact
detected scene name. It checks safe health, generates a unique request ID, and
requires observed completion while the operator watches the lamps and room
display:

```sh
./coordinator/verify_scene.py <server-host> 'Relax'
```

The iMac playback adapter posts a complete normalized observation to:

```text
POST /api/observations/music/playback
```

The body has exact `status`, `item`, and `positionMs` fields. The coordinator
rejects unknown or out-of-range values, adds the UTC `observedAt` timestamp,
keeps only the latest snapshot in memory, and publishes changed snapshots as
`music.playback` server-sent events. Every new endpoint connection receives the
current snapshot immediately after its `ready` event.

The coordinator also publishes `room.lighting` snapshots. An available
snapshot contains the complete scene-name catalog for exact room `Rum` and
every currently active scene:

```json
{
  "status": "available",
  "scenes": ["Bright", "Relax", "Warm"],
  "activeScenes": ["Relax"],
  "observedAt": "2026-07-26T12:00:00.000Z"
}
```

Names use deterministic case-insensitive order. No active scene means the lamps
have custom lighting; multiple active scenes remain explicit. Missing or
ambiguous room configuration, an empty catalog, duplicate names without regard
to case, or Hue unavailability publishes `status: "unavailable"` with empty
arrays. Hue credentials, bridge identity, room and scene resource IDs, and raw
events remain inside the adapter.

The full-screen client keeps playback, lighting, coordinator connection, and
temporary action feedback as independent state. Loaded tracks and episodes
render as the Music view, playing progress is projected locally from
`positionMs` and `observedAt`, and terminal snapshots remove the prior item.
The browser loads only the snapshot's HTTPS artwork; an unavailable image falls
back to the local Cortex Home record mark.

Each event-stream connection also receives the hashed production client entry.
If Chromium is still running a replaced bundle after coordinator deployment,
the client reloads the page and reconnects with the current build.
