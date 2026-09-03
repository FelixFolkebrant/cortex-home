# AirPlay Roadmap

## Current

- [AIR-001](issues/AIR-001.md) records the physical UxPlay and Chromium
  composition investigation that introduced the receiver.
- AirPlay is the fourth fixed channel. Chromium identifies the always-ready
  receiver; each connected UxPlay mirror window temporarily appears above it.
- Passwordless discovery, a temporary runtime home, exact lifecycle cleanup,
  and the shared Sonos route are qualified on the iMac.
- [AIR-002](issues/AIR-002.md) starts UxPlay with the kiosk, removes its control
  toggle, and uses UxPlay's connection reset for automatic recovery.

## Next

- Physically qualify reconnect and stalled-connection recovery on the iMac.

## Later

- AirPlay audio-only support, other casting protocols, or general video sources
  only when they have a clear room flow.
- A retained browser overlay above native media only if endpoint technology can
  provide reliable per-pixel composition without replacing the accepted shell.

## Open Decisions

- Whether a future endpoint can compose native media and persistent browser
  feedback more cleanly than the current X11/Chromium stack.

## Accepted Decisions

- Use UxPlay after physical qualification rather than assuming AirPlay belongs
  inside the browser.
- Put the native mirror above Chromium while connected; stock Chromium on this
  endpoint cannot provide the required transparent surface with an opaque HUD.
- Start UxPlay with the kiosk and keep it available across channel changes. Its
  built-in connection teardown and reset are the recovery path; do not add a
  process or window watcher.
- Use passwordless home-LAN discovery without retained pairing identity.
- Use UxPlay's software decoder, no-timestamp mirror mode, and XVideo sink on
  the iMac. Its Openbox session uses X11 with the Radeon driver; no NVIDIA or
  Wayland-specific pipeline applies.
