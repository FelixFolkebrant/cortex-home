# AirPlay

## Purpose

AirPlay keeps an iPhone screen receiver ready on the room display while Cortex
Home remains the normal kiosk experience.

## Experience

- The receiver starts with the kiosk and is available from any Cortex channel.
- Selecting AirPlay identifies the receiver; it has no control toggle.
- A connected native mirror is borderless and full-screen; ending a mirror
  restores the browser and leaves the receiver ready for another connection.
- Discovery is simple on the home LAN and the advertised receiver is named
  `Skärmen`.

## Boundaries

- UxPlay runs for the kiosk session and is stopped only during session cleanup.
- Mirrored content and client identity are not captured, persisted, or exposed
  to the coordinator or Voice.
- Do not replace the web shell or add a compositor, window-polling framework,
  casting registry, or remote receiver control.

## Relevant Code

- `coordinator/client/src/channels/airplay/`
- `endpoint/imac/files/cortex-airplay-control`
- `endpoint/imac/files/cortex-endpoint-airplay`
- `endpoint/imac/files/openbox-rc.xml`
