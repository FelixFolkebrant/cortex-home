# Coordinator

Install the coordinator from a machine that can reach the Ubuntu server over
SSH:

```sh
./coordinator/install <server-ssh-host>
```

The SSH destination is supplied at runtime so the server hostname or address
does not enter Git. The installer uses pnpm to build the React client, copies
only the production artifacts and coordinator to `/opt/cortex-home`, installs
`cortex-home.service`, and starts the coordinator on port 8080. Node.js and pnpm
are build-time dependencies only; the server runtime still requires only
Python.

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

With the endpoint connected, an outside caller can invoke the only allowed
action:

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

The iMac playback adapter posts a complete normalized observation to:

```text
POST /api/observations/music/playback
```

The body has exact `status`, `item`, and `positionMs` fields. The coordinator
rejects unknown or out-of-range values, adds the UTC `observedAt` timestamp,
keeps only the latest snapshot in memory, and publishes changed snapshots as
`music.playback` server-sent events. Every new endpoint connection receives the
current snapshot immediately after its `ready` event.

The full-screen client keeps playback, coordinator connection, and temporary
identify feedback as independent state. Loaded tracks and episodes render as
the Music view, playing progress is projected locally from `positionMs` and
`observedAt`, and terminal snapshots remove the prior item. The browser loads
only the snapshot's HTTPS artwork; an unavailable image falls back to the local
Cortex Home record mark.

Each event-stream connection also receives the hashed production client entry.
If Chromium is still running a replaced bundle after coordinator deployment,
the client reloads the page and reconnects with the current build.
