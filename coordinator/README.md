# Coordinator

Install the coordinator from a machine that can reach the Ubuntu server over
SSH:

```sh
./coordinator/install <server-ssh-host>
```

The SSH destination is supplied at runtime so the server hostname or address
does not enter Git. The installer uses pnpm to build the React client, copies
only the production artifacts and coordinator to `/opt/cortex-home`, installs
the locked Python and Node answer runtimes, installs `cortex-home.service`, and
starts the coordinator on port 8080. On the first deployment it asks for the
dedicated OpenRouter key without echoing it and writes only
`/etc/cortex-home/agent.env`, owned by `root:cortex-home` with mode `0640`.
Later deployments preserve that file. The x86-64 server requires Python 3.11
or later with `venv` support.

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

For normal IdeaPad development, install the locked client dependencies and
voice runtime once, export the real provider key in the current shell, then
start a local room:

```sh
pnpm --dir coordinator/client install --frozen-lockfile
export OPENROUTER_API_KEY=<private-key>
./coordinator/develop
```

If the repository's ignored `.env` already holds the key, load it into just the
current shell before the last command:

```sh
set -a
. ./.env
set +a
./coordinator/develop
```

The command starts Vite at `http://127.0.0.1:5173` and its loopback-only
coordinator at port 8080. It uses deterministic local room observations for
Today, Music, Lighting, and Alarm, but voice is real: browser capture, Vosk,
Pocket TTS, Pi Agent Core, and the pinned OpenRouter route. It needs the Vosk
model at `$HOME/.local/share/cortex-home/vosk-model-small-en-us-0.15`; it fails
with a content-free error when the key or speech runtime is unavailable. It
uses the repository `.venv`; follow the Local Voice Workbench setup below once
to create it and install the selected speech engines. It
starts no coordinator service, iMac bridge, Hue adapter, Spotify receiver, or
weather refresh. `Control`+`C` stops both processes. Camera is a normal
local-browser permission flow; AirPlay, endpoint audio, and sleep show
unavailable because the iMac bridge is intentionally absent.

Use the fixed unavailable presentation when working on empty or degraded UI:

```sh
./coordinator/develop --scenario unavailable
```

The local room is development-host evidence only. Deploy and test the physical
room before treating an integration or room behavior as confirmed.

For client work that specifically needs installed coordinator state, keep the
installed coordinator running and forward its private loopback port:

```sh
ssh -N -L 8080:127.0.0.1:8080 <server-ssh-host>
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

`Control`+`Alt`+`M` toggles a local iMac performance overview above the browser
shell. It reads bounded current CPU, memory, temperature, load, and uptime data
from the endpoint's origin-bound loopback bridge and polls only while visible.

## Speech Qualification

`Ctrl`+`Alt`+`Space` explicitly starts and ends a voice session. Chromium opens
one mono 16 kHz microphone stream only after the session is accepted; `Escape`,
focus loss, microphone failure, coordinator reconnection, or client cleanup
ends it and closes every track. Repeat keydowns and combinations containing
Shift or Meta do nothing. While active, the browser applies local RMS voice
activity detection with a 0.018 threshold, requires 400 ms of speech, and ends
a turn after 850 ms of silence; one submitted turn remains capped at 15 seconds.
The detector is paused while the former one-shot answer is processing or
playing, so playback cannot become a user turn before VOI-008 adds barge-in.

The resulting in-memory value is a WAV container containing one channel of
signed 16-bit little-endian PCM at 16 kHz. The browser sends it only to its
authenticated coordinator interaction. No recording, transcript, or
synthesized answer is stored or logged by the application.

Install the pinned qualification candidates on the ThinkPad with:

```sh
./coordinator/install-speech <server-ssh-host>
```

This installs Vosk `0.3.45` with `vosk-model-small-en-us-0.15`,
`whisper.cpp` `1.9.1` with `ggml-base.en-q5_1.bin`, Piper `1.5.0` with
`en_US-lessac-medium`, and Pocket TTS `2.1.0` with the English `alba` voice
under `/opt/cortex-speech`. The Vosk, Whisper, and Piper downloads are verified
against pinned model checksums. Candidate dependencies stay in the isolated
`/opt/cortex-speech/qualification-venv`; they do not change the running
coordinator environment.

Create a private JSON manifest outside the repository. Recognition cases need
an exact expected value and a path to a bounded capture; synthesis cases are
the short answer texts both candidates must speak:

```json
{
  "recognition": [
    {
      "audio": "/tmp/cortex-speech/case-1.wav",
      "expected": "<private expected words>"
    }
  ],
  "synthesis": [
    "<private short answer>"
  ]
}
```

For real-room recognition qualification, stream the fixed 15-second Anker
capture into a private RAM-backed directory on the ThinkPad:

```sh
install -d --mode=700 /dev/shm/cortex-speech
ssh imac@imac.local \
  sudo -n -u cortex-endpoint \
  /usr/local/bin/cortex-speech-qualification-capture \
  > /dev/shm/cortex-speech/case-1.wav
```

Use that path in the private manifest, run both recognizers, then remove the
RAM-backed directory immediately. The helper accepts no arguments and emits
only the fixed Anker PCM shape; it never creates an endpoint file.

Run each candidate in a fresh process so its CPU and peak-memory summary remains
comparable. Run the commands on the ThinkPad from a session that forwards the
operator's existing SSH agent, then verify the one endpoint hop before playback:

```sh
ssh -A <server-ssh-host>
ssh -o StrictHostKeyChecking=accept-new imac@imac.local true
```

Do not copy an operator private key onto the ThinkPad.
Endpoint qualification invokes only the two root-owned capture and playback
helpers through their command-specific sudo rules. Both reject arguments. The
playback helper reads one WAV from standard input and targets the existing
`cortex-endpoint` PulseAudio socket; neither stores audio or starts a service.

```sh
/opt/cortex-speech/qualification-venv/bin/python \
  /opt/cortex-speech/qualify_speech.py recognition \
  --backend vosk \
  --manifest /tmp/cortex-speech/manifest.json \
  --model /opt/cortex-speech/models/vosk-model-small-en-us-0.15

/opt/cortex-speech/qualification-venv/bin/python \
  /opt/cortex-speech/qualify_speech.py recognition \
  --backend whisper.cpp \
  --manifest /tmp/cortex-speech/manifest.json \
  --model /opt/cortex-speech/models/ggml-base.en-q5_1.bin

/opt/cortex-speech/qualification-venv/bin/python \
  /opt/cortex-speech/qualify_speech.py synthesis \
  --backend piper \
  --manifest /tmp/cortex-speech/manifest.json \
  --model /opt/cortex-speech/models/en_US-lessac-medium.onnx \
  --endpoint imac@imac.local

/opt/cortex-speech/qualification-venv/bin/python \
  /opt/cortex-speech/qualify_speech.py synthesis \
  --backend pocket-tts \
  --manifest /tmp/cortex-speech/manifest.json \
  --model /opt/cortex-speech/pocket-cache \
  --voice alba \
  --endpoint imac@imac.local
```

The recognition summary contains only aggregate word error rate, latency, CPU,
memory, and model size. The synthesis summary contains only aggregate
generation latency, output duration, endpoint use, CPU, memory, and model size.
Neither summary contains qualification text, file paths, or host identity.
Remove the private manifest and bounded inputs as soon as both recognition runs
finish. Listening quality, first audible output, and prompt playback stop remain
reviewer observations because software completion is not evidence of what
reached the Sonos.

The selected product roles are Vosk recognition and Pocket TTS
synthesis. They implement the `Recognizer` and `Synthesizer` protocols in
`coordinator/speech.py`; coordinator behavior sees only `WaveAudio`, text, and
explicit `SpeechError` failures rather than engine objects. whisper.cpp and
Piper remain pinned qualification evidence and are not runtime switches.

## Contextual Answer Runtime

The production installer downloads the official Node `24.18.0` x86-64 archive,
checks its pinned SHA-256 digest, and installs it under
`/opt/cortex-home/node`. It installs only Vosk `0.3.45`,
`vosk-model-small-en-us-0.15`, Pocket TTS `2.1.0`, and the English `alba` voice
for the selected speech path. The Vosk archive is checksum-verified. The
coordinator preloads both speech engines and validates the private agent
configuration before it opens port 8080.

One-shot interactions retain the fresh `/opt/cortex-home/agent/answer-child.js`
process. An explicit voice session instead owns one
`/opt/cortex-home/agent/dialogue-child.js` process from session activation to
its terminal event. It receives only each bounded transcript and fresh reduced
active-view context through standard input. That context contains exactly
`activeChannel` and `channel`; lighting remains internal until later accepted
work. The dialogue retains at most six complete exchanges and 6,000 text
characters in memory, removing the oldest complete exchange before each
provider request. It emits ordered text deltas and one bounded final answer;
the coordinator terminates its process group and discards its history on
replacement, disconnect, cancellation, session end, timeout, malformed output,
or shutdown.

The locked child uses `@earendil-works/pi-agent-core` and
`@earendil-works/pi-ai` `0.82.1` with
`google/gemini-3.5-flash-lite`. Every request permits only
`google-vertex/global`, disables fallbacks, requires supported parameters,
denies data collection, enables Zero Data Retention routing, and sends
`store: false`. The provider key reaches only the coordinator and the
per-interaction child environment; it is never sent to the browser.

The endpoint contract is:

- `POST /api/voice/sessions/<session-id>` with the active endpoint token starts
  one explicit session; `DELETE` ends it and invalidates its microphone and
  turn ownership.
- `POST /api/agent/interactions/<request-id>` with the active endpoint token,
  `audio/wav`, `X-Voice-Session`, and `X-Voice-Turn-Epoch` returns an
  accepted JSON interaction. The coordinator accepts only the next exact epoch
  and sends local `audio/wav` segments over the owning endpoint event stream.
- `DELETE /api/agent/interactions/<request-id>` cancels or reserves that
  endpoint-owned request ID.
- `POST /api/agent/interactions/<request-id>/status` reports `speaking`,
  `completed`, or `failed`.
- `voice.session` SSE publishes only the session ID, epoch, and `listening`,
  `user-speaking`, `ending`, or `ended` state. `agent.interaction` publishes only the
  request ID, session ID, epoch, and `transcribing`, `thinking`, `speaking`,
  `completed`, or `failed`.
- `agent.audio` SSE delivers one local answer WAV segment for the active request;
  `agent.audio.complete` says no further segment will arrive. Neither event
  includes transcript, answer text, or provider content.

The coordinator, browser, and Node child all reject stale session or epoch
data. Endpoint replacement, disconnect, an explicit session end, invalid audio,
recognition, provider, synthesis, and playback failures cannot publish work into
a replacement session. Sessions retain no audio and only their bounded,
in-memory dialogue until their terminal lifecycle event.

Exact non-repeating `Ctrl`+`Alt`+`D` toggles a local voice diagnostics panel.
It is hidden by default and renders only numeric timing, duration, byte, and
character counts:

- upload transfer is the coordinator's bounded WAV body-read time;
- STT and TTS are local coordinator stage durations;
- LLM round trip includes child startup plus OpenRouter/provider request time;
- answer transfer is the browser's response-body read time;
- total to audio runs from upload start until the answer WAV is available;
- playback is observed browser playback time;
- capture and answer rows show audio duration and bytes, while transcript and
  response rows show character counts.

The panel never receives or renders the request ID, transcript, answer, context,
credential, provider detail, or audio content. The coordinator returns the
server measurements in `X-Cortex-Debug-Metrics`; the browser accepts only the
fixed non-negative numeric allowlist and ignores every other field.

## Local Voice Workbench

VOI-005 adds a development-laptop-only voice loop. It has no coordinator HTTP
client, endpoint client, Hue adapter, room hardware access, or deployment
configuration. It captures one bounded 15-second utterance with the selected
Vosk recognizer, sends only its transcript through the pinned OpenRouter route,
and plays the selected Pocket TTS result locally. The optional development tool
is in-memory and always reports a simulated result; it cannot inspect or alter
the laptop or room.

On Arch, install the local command and runtime prerequisites, then prepare an
isolated Python environment and the locked Node package:

```sh
sudo pacman -S --needed alsa-utils nodejs pnpm python unzip
python -m venv .venv
.venv/bin/python -m pip install \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  --requirement coordinator/requirements.txt
pnpm --dir coordinator/agent install --frozen-lockfile
```

Download the selected Vosk model outside the repository and verify its pinned
archive checksum before unzipping it:

```sh
mkdir -p "$HOME/.local/share/cortex-home"
curl --fail --location --output /tmp/vosk-model-small-en-us-0.15.zip \
  https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
printf '%s  %s\n' \
  30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498 \
  /tmp/vosk-model-small-en-us-0.15.zip | sha256sum --check -
unzip -q /tmp/vosk-model-small-en-us-0.15.zip -d "$HOME/.local/share/cortex-home"
```

List ALSA device names if the PipeWire default device is not the desired source
or sink:

```sh
arecord -L
aplay -L
```

With an OpenRouter key in the current shell, this command starts the persistent
local interaction loop. It does not start or contact any Cortex Home service:

```sh
OPENROUTER_API_KEY=<private-key> \
  .venv/bin/python coordinator/local_voice.py \
  --vosk-model "$HOME/.local/share/cortex-home/vosk-model-small-en-us-0.15"
```

Pass `--input-device <alsa-name>` or `--output-device <alsa-name>` to select a
non-default device. The terminal prints `ready` between turns plus content-free
lifecycle phases and errors: `listening`, `transcribing`, `thinking`, optional
`acting`, `speaking`, then `completed`, `failed`, or `cancelled`. Press Enter
to begin one turn, `Ctrl`+`C` to cancel only its current stage, and `Ctrl`+`D`
at `ready` to exit. Cancellation stops local recording or playback, terminates
unfinished model work, releases the audio devices, and returns to `ready`. Ask
explicitly to test the development tool to exercise the one simulated tool
continuation; a successful response is not room or hardware evidence.

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
  --data '{"requestId":"show-camera-1","action":"channel.select","channel":"camera"}' \
  http://<server-host>:8080/api/actions
```

The only accepted channel values are `today`, `music`, `camera`, and
`airplay`. The
coordinator starts on Today, publishes the selected `channel.active` snapshot
to every endpoint connection, and returns completion after it publishes that
state. On the iMac endpoint, Openbox owns all four channel chords globally:
`Ctrl`+`Alt`+`1` selects Today, `Ctrl`+`Alt`+`2` selects Music, and
`Ctrl`+`Alt`+`3` selects the local Camera mirror after ensuring UxPlay is
stopped. `Ctrl`+`Alt`+`4` selects the AirPlay control view without starting the
receiver. Its on-screen switch controls the receiver through an origin-bound
loopback bridge on the iMac; plain `Enter` toggles it while AirPlay is active.
Browser-only environments can render the view but cannot control a local
receiver. `Ctrl`+`Alt`+`S` activates the next detected
room scene in
case-insensitive name order and wraps after the last scene. While Music is
active, `Ctrl`+`M` locally toggles its fullscreen artwork presentation without
sending a coordinator action. Leaving Music resets that presentation. Other
key combinations and repeated key presses do nothing. The Hue remote remains
exclusively native to Hue; Cortex Home does not subscribe to its button events.

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

The coordinator also exposes an internal `Coordinator.context()` method for
future local agent work. It is not an HTTP or SSE endpoint. The method returns
one fresh reduced value with exactly these top-level keys:

```json
{
  "activeChannel": "music",
  "channel": {
    "type": "music",
    "available": true,
    "playbackState": "playing",
    "itemType": "track",
    "title": "Never Gonna Give You Up",
    "creators": ["Rick Astley"],
    "collection": "Whenever You Need Somebody",
    "positionMs": 1200,
    "durationMs": 213573,
    "observedAt": "2026-07-26T12:00:01.000Z"
  },
  "lighting": {
    "available": true,
    "scenes": ["Bright", "Relax", "Warm"],
    "activeScenes": ["Warm"],
    "observedAt": "2026-07-26T12:00:02.000Z"
  }
}
```

Only the active channel appears in `channel`. A Today channel contains
`type`, `available`, `timeZone`, `current`, `forecast`, and `observedAt`.
Unavailable or invalid snapshots reduce to a small unavailable context instead
of forwarding unknown fields. The projection omits provider objects,
credentials, artwork URLs, Spotify URIs, endpoint tokens, Hue resource IDs, raw
events, cache metadata, and coordinator-owned mutable dictionaries. Each
interaction builds a still-smaller active-view projection immediately before
its one model request and passes only `activeChannel` and `channel` to the
supervised child.

The full-screen client keeps playback, lighting, coordinator connection, and
temporary action feedback as independent state. Loaded tracks and episodes
render as the Music view, playing progress is projected locally from
`positionMs` and `observedAt`, and terminal snapshots remove the prior item.
The browser loads only the snapshot's HTTPS artwork; an unavailable image falls
back to the local Cortex Home record mark.

Music's local fullscreen presentation centers the square artwork and samples a
small in-browser copy to choose the surrounding majority color, a recurring
distinctive title-fill color, and whichever of pure black or white has higher
contrast. Its rotated title is the progress indicator; the unplayed segment is
60% opaque and the creators are 40% opaque. Complete track changes swipe left
over 400ms while the surrounding majority color fades. The presentation omits
source, collection, timestamps, duration, normal player chrome, and shared
feedback. The final-ten-second upcoming treatment is implemented for complete
upcoming-item input; the current normalized receiver does not publish that
metadata and the client does not fabricate it.

Each event-stream connection also receives the hashed production client entry.
If Chromium is still running a replaced bundle after coordinator deployment,
the client reloads the page and reconnects with the current build.
