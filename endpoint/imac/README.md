# iMac Endpoint

Run the provisioning entry point from the repository root while the qualified
iMac is reachable through the `imac` SSH host:

```sh
./endpoint/imac/provision
```

When the base endpoint is already provisioned, install or restore only its
Spotify receiver:

```sh
./endpoint/imac/provision-raspotify
```

The focused command asks only for the existing `imac` account's sudo password.

The command copies the fixed provisioning files to a temporary directory on
the iMac and asks for:

1. The existing `imac` account's sudo password.
2. The home Wi-Fi name.
3. The home Wi-Fi password.
4. The coordinator's local HTTP origin, without a path.

The Wi-Fi values are read by the remote installer without echoing the password.
They are written only to the root-readable Netplan configuration on the iMac.
The coordinator URL is written only to the endpoint's local configuration. The
temporary remote copy is removed when provisioning exits.

Provisioning installs the minimal graphical and wireless packages plus the
reviewed Raspotify build, creates the locked `cortex-endpoint` account,
configures its automatic full-screen session, points Chromium at the network
client, and persists the rear analog mixer route. The command can be rerun to
restore the committed configuration.

Raspotify advertises one `Högtalaren` Spotify Connect receiver. It runs as the
endpoint user and shares that user's PulseAudio session with Chromium so both
Spotify and endpoint feedback use the qualified Sonos route. Raspotify remains
an unofficial, Premium-only Spotify client intended for personal use.

The receiver invokes `/usr/local/bin/cortex-playback-event` for supported
librespot events. The standard-library adapter keeps only a normalized runtime
snapshot at `/run/raspotify/cortex-playback.json` so metadata-only track events
can be combined with later play, pause, and seek events. It sends no account,
client, host, or raw event fields to the coordinator and logs only a generic
failure. A reporting failure exits the adapter without stopping audio; the next
supported receiver event retries with the current runtime state. Stopping or
failing Raspotify reports `unavailable` through a non-blocking systemd
`ExecStopPost` command.

The endpoint advertises itself as `imac.local` on the home network. Press
`Control`+`Option`+`Return` on the iMac keyboard to open an unprivileged
recovery terminal above the kiosk. Run `su - imac` there when administrative
access is required, and close the terminal to return to the full-screen page.

## Playback Diagnostics

When Music becomes black unexpectedly, note the song title and reproduce it
once while following the receiver journal for at most 60 seconds:

```sh
ssh <endpoint-ssh-host>
sudo timeout 60 journalctl \
  --follow \
  --unit=raspotify.service \
  --output=short-precise
```

Immediately after the screen becomes black, capture the normalized playback
state and the recent receiver log:

```sh
sudo cat /run/raspotify/cortex-playback.json | python3 -m json.tool
sudo journalctl \
  --unit=raspotify.service \
  --since="-2 minutes" \
  --output=short-precise \
  --no-pager
```

On the coordinator, capture the same two-minute window:

```sh
ssh <server-ssh-host>
sudo journalctl \
  --unit=cortex-home.service \
  --since="-2 minutes" \
  --output=short-precise \
  --no-pager
```

If Chromium developer tools open with `Control`+`Shift`+`J`, record any red
console or failed artwork-network message at the moment the screen changes.
The useful distinction is whether the normalized state says `playing` with a
complete `item`, or `unavailable` with `item: null`. Do not copy the raw
`/api/events` stream because its initial ready event contains the endpoint
token.
