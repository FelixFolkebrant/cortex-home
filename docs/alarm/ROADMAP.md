# Alarm Roadmap

## Current

- [ALA-001](wip/ALA-001.md) implements one persisted next-occurrence alarm,
  keyboard editing, due and missed recovery, the fixed `Warm low` action,
  endpoint-local selectable audio, and RTC-backed endpoint sleep.
- Deep suspend was rejected after physical testing exposed Radeon display
  corruption. The implementation uses suspend-to-idle with RTC wake.
- Automated checks and most physical behavior are complete; the final bounded
  suspend-to-idle, wake, recovery, sound, lighting, dismissal, and early-wake
  reviewer pass remains open in ALA-001.

## Next

- Complete and record the physical ALA-001 qualification, then archive its
  living issue record.
- Fix only observed wake reliability, graphical recovery, network recovery, or
  audio cleanup gaps before expanding scheduling behavior.

## Later

- Weekday recurrence, snooze, sunrise fades, or more sounds only after the
  one-shot wake flow is reliable.
- Automatic bedtime behavior only after deliberate sleep proves it does not
  disrupt Music, Camera, AirPlay, or Voice.
- More automatic room actions only through a separately accepted narrow flow.

## Open Decisions

- Whether suspend-to-idle delivers enough power savings and wake reliability on
  the 2008 iMac to remain worthwhile.
- Which single next alarm feature matters after the basic wake flow is proven.

## Accepted Decisions

- Let the ThinkPad own and atomically persist one normalized one-shot schedule.
- Interpret `HH:MM` as the next Europe/Stockholm occurrence with explicit DST,
  late, and missed behavior.
- Require observed arming and a separate deliberate suspend command.
- Isolate display, fixed lighting, and local audio effects so one failure never
  hides the time or creates autonomous retries.
- Use endpoint-local selectable MP3 files and a narrow RTC helper rather than
  Spotify, generated speech, or a general power API.
