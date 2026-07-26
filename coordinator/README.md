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

An outside caller can activate the fixed `Warm` scene in room `Rum` even when
the endpoint is disconnected:

```sh
curl \
  --fail-with-body \
  --header 'Content-Type: application/json' \
  --data '{"requestId":"warm-1","action":"room.scene.activate"}' \
  http://<server-host>:8080/api/actions
```

The action accepts no room, scene, or Hue resource argument. It remains open
until a later Hue event reports `Warm` active, the 10-second action bound
expires, or the adapter reports an unavailable or rejected command. Every
request needs a new request ID.

The iMac playback adapter posts a complete normalized observation to:

```text
POST /api/observations/music/playback
```

The body has exact `status`, `item`, and `positionMs` fields. The coordinator
rejects unknown or out-of-range values, adds the UTC `observedAt` timestamp,
keeps only the latest snapshot in memory, and publishes changed snapshots as
`music.playback` server-sent events. Every new endpoint connection receives the
current snapshot immediately after its `ready` event.

The coordinator also publishes `room.lighting` snapshots with only `scene`,
`status`, and `observedAt`. The scene is always `Warm`; status is `active`,
`inactive`, or `unavailable`. Hue credentials, bridge identity, room and scene
resource IDs, and raw events remain inside the adapter.

The full-screen client keeps playback, lighting, coordinator connection, and
temporary action feedback as independent state. Loaded tracks and episodes
render as the Music view, playing progress is projected locally from
`positionMs` and `observedAt`, and terminal snapshots remove the prior item.
The browser loads only the snapshot's HTTPS artwork; an unavailable image falls
back to the local Cortex Home record mark.

Each event-stream connection also receives the hashed production client entry.
If Chromium is still running a replaced bundle after coordinator deployment,
the client reloads the page and reconnects with the current build.
