# AirPlay

## Purpose

AirPlay provides a deliberate, on-demand way to mirror an iPhone on the room
display while keeping Cortex Home as the normal kiosk experience.

## Experience

- Selecting AirPlay shows a minimal receiver-control view without starting the
  receiver automatically.
- A keyboard or on-screen switch starts and stops the receiver.
- A connected native mirror is borderless and full-screen; leaving AirPlay
  stops it and restores the browser.
- Discovery is simple on the home LAN and the advertised receiver is named
  `Skärmen`.

## Boundaries

- UxPlay runs only on demand; it is not an always-on service.
- Mirrored content and client identity are not captured, persisted, or exposed
  to the coordinator or Voice.
- Keep native receiver control behind the narrow loopback endpoint bridge.
- Do not replace the web shell or add a compositor, window-polling framework,
  casting registry, or remote receiver control.

## Relevant Code

- `coordinator/client/src/channels/airplay/`
- `endpoint/imac/files/cortex-airplay-control`
- `endpoint/imac/files/cortex-endpoint-airplay`
- `endpoint/imac/files/openbox-rc.xml`
