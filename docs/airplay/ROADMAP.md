# AirPlay Roadmap

## Current

- [AIR-001](issues/AIR-001.md) records the physical UxPlay and Chromium
  composition investigation and implements the resulting on-demand receiver.
- AirPlay is the fourth fixed channel. Chromium remains the waiting and control
  view; each connected UxPlay mirror window temporarily appears above it.
- Passwordless discovery, a temporary runtime home, exact lifecycle cleanup,
  and the shared Sonos route are qualified on the iMac.

## Next

- Address only observed discovery, reconnect, audio, or lifecycle failures.
- Preserve the explicit on-demand boundary when endpoint provisioning changes.

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
- Start and stop UxPlay from one explicit AirPlay view through a narrow
  loopback helper, with no always-on receiver service or compositor.
- Use passwordless home-LAN discovery without retained pairing identity.
