# Alarm

## Purpose

Alarm lets the room display and its attached audio wake the user at one chosen
local time while the always-on ThinkPad remains the schedule authority.

## Experience

- Home shows the next armed Europe/Stockholm alarm without a permanent editor.
- A later on-demand Home tool will edit and arm it.
- A second deliberate command lets the iMac sleep after the coordinator has
  observed the alarm as armed.
- When due, Alarm requests one fixed warm Hue scene and loops the selected
  endpoint-local sound until dismissal.
- Scheduling, lighting, audio, sleep, and wake failures remain independently
  recoverable.

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
- `coordinator/client/src/alarm/`
- `coordinator/client/src/app/HomeSurface.tsx`
- `endpoint/imac/files/cortex-endpoint-alarm`
- `endpoint/imac/files/cortex-endpoint-rtc-suspend`
