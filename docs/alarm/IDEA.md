# Alarm

## Purpose

Alarm lets the room display and its attached audio wake the user at one chosen
local time while the always-on ThinkPad remains the schedule authority.

## Experience

- The keyboard edits and arms one next-occurrence Europe/Stockholm alarm.
- A second deliberate command lets the iMac sleep after the coordinator has
  observed the alarm as armed.
- When due, Alarm shows the live time full-screen, requests one fixed warm Hue
  scene, and loops the selected endpoint-local sound until dismissal.
- Scheduling, display, lighting, audio, sleep, and wake failures remain visible
  and independently recoverable.

## Boundaries

- Own exactly one one-shot alarm; no recurrence, snooze, calendar, or general
  automation engine.
- Persist schedule state on the ThinkPad, never in a browser timer.
- Grant the automatic path only the fixed `Warm low` scene through normal
  coordinator validation and observed completion.
- Keep endpoint power and audio operations behind exact, argument-validating
  loopback and root-owned helpers.
- Store replaceable MP3 files outside the repository in the bounded endpoint
  alarm-audio directory.

## Relevant Code

- `coordinator/alarm.py`
- `coordinator/client/src/channels/alarm/`
- `endpoint/imac/files/cortex-endpoint-alarm`
- `endpoint/imac/files/cortex-endpoint-rtc-suspend`
