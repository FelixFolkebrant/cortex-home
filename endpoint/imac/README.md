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

For an already provisioned endpoint, treat that configuration as the source of
truth instead of guessing the coordinator host or copying a stale deployment
address from documentation. Read the exact configured origin with:

```sh
ssh imac 'sed -n "1p" /etc/cortex-endpoint/coordinator-url'
```

Use the command's complete output, including scheme and port, wherever an
operator step asks for the configured coordinator origin. Network addresses
remain runtime configuration and are deliberately not committed to the
repository.

Provisioning installs the minimal graphical and wireless packages plus the
reviewed Raspotify build, creates the locked `cortex-endpoint` account,
configures its automatic full-screen session, points Chromium at the network
client, and persists the rear analog mixer route. The command can be rerun to
restore the committed configuration.

The same command renders
`/var/snap/chromium/current/policies/managed/cortex-home-media.json` from the
configured coordinator origin. The managed policy treats that one HTTP origin
as a secure context and grants it unattended audio and video capture. It does
not contain a wildcard, global all-media permission, or a committed deployment
hostname. Chromium must restart before the secure-context override takes
effect.

On an already provisioned endpoint, install only that policy and restart the
kiosk with:

```sh
./endpoint/imac/provision-media
```

The focused command reads the endpoint's existing coordinator URL and asks only
for the existing `imac` account's sudo password. It does not change packages,
Wi-Fi or unrelated endpoint configuration. It restores the qualified room
mixer baseline—Master 80% and unmuted, built-in Speaker muted, rear Headphone
60% and unmuted—and pins room output to the single built-in PCI analog
PulseAudio sink used by the Sonos line-in. It applies the ALSA baseline after
the kiosk and Raspotify sessions restart; the Pulse route selects and unmutes
the sink but never changes its volume. Microphone sources are neither selected
nor disabled. Kiosk startup, Raspotify, and speech qualification all apply that
same output route so a USB microphone with its own speaker cannot become the
room output. The command also installs argument-free speech qualification
helpers and command-specific sudo rules. The capture helper emits a fixed
15-second, 16 kHz mono PCM WAV from the Anker to standard output. The
playback helper reads WAV from standard input and targets the existing
`cortex-endpoint` PulseAudio session instead of the SSH account's null sink.
Neither stores audio or starts a service.

After provisioning, confirm the rendered policy without printing other endpoint
configuration:

```sh
ssh -t imac \
  'sudo python3 -m json.tool /var/snap/chromium/current/policies/managed/cortex-home-media.json'
```

The three values must be the configured coordinator origin with one trailing
slash under `AudioCaptureAllowedUrls`,
`OverrideSecurityRestrictionsOnInsecureOrigin`, and
`VideoCaptureAllowedUrls`. The focused command restarts the kiosk; inspect
`chrome://policy` from the recovery terminal if Chromium does not grant the
microphone or camera unattended.

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

`Control`+`Option`+`Up` raises the rear Headphone control by 5 percentage
points, and `Control`+`Option`+`Down` lowers it by the same amount. Openbox owns
these endpoint-global bindings. The helper adjusts the explicitly selected
built-in analog PulseAudio sink rather than writing beneath PulseAudio through
ALSA, so increases and decreases apply coherently to both Raspotify and speech
playback without selecting the Anker output or changing microphone input.

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
