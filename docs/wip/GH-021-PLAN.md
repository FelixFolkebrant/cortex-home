# GH-021 Plan: Wake The Room

# What

- Add one fixed Alarm channel for setting a one-shot wake time with the attached
  keyboard.
- Persist the next alarm on the always-on ThinkPad so it survives browser and
  coordinator restarts and can fire while the iMac is suspended.
- At the alarm time, select the Alarm view, show the current time full-screen,
  request the exact Hue scene `Warm low`, and loop one endpoint-local audio file
  until the user dismisses the alarm.
- Add a deliberate two-step sleep flow that arms the iMac's hardware RTC and
  suspends the iMac to RAM until the alarm time.
- Make the alarm audio easy to replace through one documented focused install
  command without rebuilding the client or changing code.

## Out Of Scope

- Multiple, recurring, weekday, calendar-derived, sunrise, location-based, or
  remotely managed alarms.
- Snooze, gradual light fades, volume ramps, playlists, streaming audio,
  microphone input, voice control, touch controls, or a sound picker.
- Automatically sleeping after inactivity or at a fixed bedtime. Sleep remains
  a deliberate confirmation from the armed Alarm view.
- Suspending the ThinkPad, Hue bridge, Sonos, router, or any device other than
  the iMac.
- Wake-on-LAN, hibernation, shutdown, boot-from-off scheduling, or using a
  browser timer as the authoritative wake mechanism.
- A general scheduler, automation engine, endpoint command API, or configurable
  action sequence.

## Deferred

- Recurrence waits until one next-occurrence alarm proves scheduling,
  persistence, daylight-saving behavior, RTC wake, and dismissal.
- Snooze waits until the physical wake flow establishes whether another timer
  and repeated automatic scene requests are actually useful.
- Automatic bedtime sleep waits because unexpected suspension would affect
  Music, Camera, AirPlay, and active voice work.
- More alarm actions and selectable scenes wait until the fixed `Warm low`
  sequence is reliable and understandable.

## Acceptance Criteria

### Alarm State And Authority

- [ ] The coordinator owns exactly one one-shot alarm with `disarmed`, `armed`,
  `ringing`, `missed`, or `failed` state and publishes a normalized alarm
  snapshot over the existing endpoint connection.
- [ ] The selected `HH:MM` means the next occurrence in `Europe/Stockholm`; a
  time that has already passed schedules tomorrow rather than firing
  immediately.
- [ ] The coordinator stores only the bounded alarm state and next UTC firing
  instant in its systemd-managed state directory using an atomic replacement.
- [ ] A coordinator restart restores an armed future alarm. A due alarm up to
  15 minutes late rings immediately; an older due alarm becomes visibly
  `missed` and never surprises the room hours later.
- [ ] Invalid, impossible, duplicate, stale, or out-of-range alarm requests
  fail without changing the current schedule.
- [ ] A selected time that does not exist during the Europe/Stockholm spring
  gap is rejected visibly. During the repeated autumn hour, the alarm chooses
  the earliest matching instant that is still in the future.

### Alarm View And Keyboard Input

- [ ] `Ctrl`+`Alt`+`5` selects Alarm through the existing observed
  `channel.select` lifecycle and stops AirPlay before the Alarm view appears.
- [ ] Alarm editing is keyboard-only. Left and Right select hours or minutes;
  Up subtracts one from the selected field; Down adds one; both wrap within
  `00–23` and `00–59` exactly as requested.
- [ ] Number keys directly replace the selected field through a bounded
  two-digit entry buffer. Modified or repeated keys, letters, invalid values,
  and stale buffered digits do nothing.
- [ ] The editor clearly distinguishes the selected field, the next calendar
  occurrence, disarmed, armed, sleep-ready, missed, and failure states.
- [ ] The first plain Enter submits the displayed alarm. Only an observed armed
  snapshot enables a second plain Enter to request iMac sleep; this prevents an
  unacknowledged draft from suspending the endpoint.
- [ ] Escape before sleep disarms the alarm and returns to editing. No key used
  by the Alarm view changes Camera, Music, AirPlay, voice, or scene-cycle
  behavior outside that mounted view.

### Alarm Firing

- [ ] At the firing instant, the coordinator publishes `ringing`, selects the
  Alarm channel, and requests exactly the detected `Warm low` scene through the
  shared exact-scene execution boundary.
- [ ] The scene request uses current coordinator validation and observed Hue
  completion. It never fuzzy-matches another scene, retries autonomously, or
  reports acceptance as success.
- [ ] The ringing view makes the live local time the dominant full-screen
  element and remains readable from normal room distance.
- [ ] The iMac starts the fixed endpoint-local alarm file when it observes the
  matching ringing alarm and loops it until dismissal. Reload, reconnect, and
  repeated ringing snapshots cannot start overlapping players.
- [ ] A plain Enter while ringing stops the local audio, dismisses the alarm,
  disarms the one-shot schedule, and returns to Today.
- [ ] A missing `Warm low` scene, Hue failure, unavailable audio file, endpoint
  bridge failure, or playback failure remains visible while the other wake
  effects continue where possible.
- [ ] Alarm state, scene outcome, audio state, and dismissal contain no
  credentials or private content and do not grant a general automatic-action
  boundary.

### Replaceable Audio

- [ ] The alarm uses `/etc/cortex-endpoint/wake-alarm.mp3`, owned by root and
  readable by `cortex-endpoint`; the repository does not contain copyrighted or
  personal alarm audio.
- [ ] `./endpoint/imac/provision-alarm-audio <local-mp3>` validates a regular
  bounded `.mp3` file, installs it atomically at that path, and leaves
  coordinator, kiosk, Wi-Fi, media policy, and unrelated endpoint
  configuration unchanged.
- [ ] Replacing the file requires no source edit, client rebuild, coordinator
  restart, or full endpoint provisioning.
- [ ] Starting, looping, stopping, replacing, missing-file, invalid-file, and
  stale-process behavior are covered without playing real audio in automated
  tests.

### iMac Sleep And RTC Wake

- [ ] Before implementation depends on it, a bounded physical qualification
  proves that the real iMac enters deep suspend-to-RAM and resumes from its
  `rtc_cmos` alarm at the requested UTC instant.
- [ ] Sleep is available only for one observed armed alarm far enough in the
  future to complete the request; the endpoint rejects missing, stale, past,
  malformed, or more-than-26-hour wake instants.
- [ ] The exact-origin loopback bridge may invoke only one root-owned validated
  RTC-suspend helper. The helper accepts one bounded epoch and cannot run an
  arbitrary command or alter another system setting.
- [ ] A sleep request stops UxPlay, confirms the local alarm file is readable,
  arms the RTC, and suspends the iMac. Failure leaves the iMac awake and the
  coordinator alarm armed with a visible error.
- [ ] During suspend, Chromium, UxPlay, Raspotify, PulseAudio, and endpoint
  scripts perform no work; only hardware needed to retain RAM and wait for the
  RTC wake remains active.
- [ ] On RTC resume, the existing graphical session, Chromium kiosk, network,
  endpoint bridge, audio route, and coordinator connection recover without
  manual login or restart.
- [ ] An early manual wake does not ring before the scheduled instant. The user
  can return to the armed view and deliberately sleep again.
- [ ] If RTC wake fails, the always-on coordinator still attempts `Warm low`
  and records the alarm as ringing, but it never claims that the iMac displayed
  or played the alarm.

### Verification

- [ ] Coordinator tests cover persistence, next-occurrence calculation,
  daylight-saving edges, restart recovery, missed alarms, exact scene
  activation, failure isolation, dismissal, and stale requests.
- [ ] Frontend tests cover the complete keyboard table, numeric buffer,
  observed arming, two-step sleep, full-screen ringing, one-player ownership,
  dismissal, reconnect, and responsive states.
- [ ] Endpoint tests cover exact-origin control, epoch bounds, the narrow
  sudoers rule, RTC command construction, audio-file installation, process
  ownership, and cleanup without suspending the test host.
- [ ] The complete automated repository check set passes.
- [ ] A deployed manual pass proves awake firing, deep overnight-equivalent
  suspend and RTC wake, `Warm low`, full-screen time, replaceable audio,
  dismissal, early wake, restart recovery, and explicit failure presentation.

# Tasks

## 1. GH-021: Persist One Wake Alarm

- Add the normalized one-shot alarm state, next-occurrence calculation,
  systemd-owned persistence, restart recovery, and protected alarm actions.
- This is atomic because it establishes the authoritative schedule without
  adding UI, automatic room actions, audio, or endpoint power control.

## 2. GH-021: Edit The Alarm From The Keyboard

- Add Alarm as the fifth fixed channel, implement the hours/minutes editor and
  exact keyboard table, and render observed armed, missed, and failure states.
- This is atomic because it completes the visible scheduling interaction
  against the persisted coordinator boundary.

## 3. GH-021: Ring The Room

- Fire the schedule, select the full-screen clock, request exact `Warm low`,
  control one endpoint-local looping player, and dismiss back to Today.
- This is atomic because it connects one due schedule to the complete visible,
  lighting, and audio wake result.

## 4. GH-021: Suspend Until The Alarm

- Extend the exact-origin endpoint bridge with the bounded sleep operation,
  install the narrow privileged RTC helper, and qualify deep suspend/resume on
  the real iMac.
- This is atomic because it adds the privileged power-management seam only
  after the alarm works while the endpoint is awake.

## 5. GH-021: Replace The Alarm Audio

- Add and document one focused MP3 installer with validation, atomic
  replacement, ownership, and no unrelated deployment effects.
- This is atomic because changing the user-owned alarm sound has a separate
  operator lifecycle from application deployment.

# Heatmap

Reference: `../project/HEATMAP.md`.

Crossroad decisions for schedule authority, automatic scene activation,
endpoint suspend, and audio ownership live in `../planpoints/PP-7.md`.

## Hot

### H1 - Make Sleep A Two-Step Confirmation

- Decision: Use the first Enter to arm through the coordinator and a second
  Enter, enabled only by the observed armed state, to suspend the iMac.
- Proposed approach: Show the resolved date and time after arming, then present
  one explicit `Press Enter to sleep` state. Escape disarms and returns to
  editing.
- Why: A network acknowledgement must not suspend the endpoint implicitly, and
  automatic idle sleep could interrupt other room uses.
- Alternatives: Sleep immediately on arm; add a separate shortcut; sleep after
  a timeout; use an on-screen pointer control.
- Review focus: accidental suspension, stale acknowledgements, key repeat,
  cancellation, and clear sleep failure.

### H2 - Use Exact Field Editing

- Decision: Keep one selected field and one bounded two-digit buffer instead of
  a free-form text input.
- Proposed approach: Left/Right changes fields; Up decrements; Down increments;
  two number presses replace the selected value; field changes and a short
  timeout clear the numeric buffer.
- Why: The attached keyboard is the room control, and the requested direction
  deliberately makes Down move later and Up move earlier.
- Alternatives: Native time input; free-form `HH:MM`; one-minute-only arrows;
  auto-advance after two digits.
- Review focus: wraparound, invalid hours/minutes, timeout behavior, visible
  selection, and exact modifier/repeat rejection.

### H3 - Keep Audio Endpoint-Local And Single-Owner

- Decision: Loop one fixed iMac-local MP3 through a small endpoint player
  controlled by the existing exact-origin bridge.
- Proposed approach: Start only for the matching ringing alarm, record one
  owned player PID, reject overlap, and stop it on dismissal, session cleanup,
  or replacement.
- Why: The sound remains available immediately after resume and changing it
  does not require rebuilding or redeploying the web client.
- Alternatives: Bundle audio in the client; serve it from the ThinkPad; invoke
  Spotify; synthesize a tone; allow a directory or playlist.
- Review focus: stale PIDs, audio route, loop behavior, failure copy, atomic
  replacement, and no playback during suspend.

### H4 - Bound Late Recovery

- Decision: Fire an alarm at most 15 minutes late after a coordinator restart
  and mark older due alarms missed.
- Proposed approach: Compare the persisted UTC firing instant during startup;
  restore future timers, ring within the fixed grace window, otherwise publish
  `missed` and require a new alarm.
- Why: A wake alarm should recover from a brief restart but must not activate
  lights and audio unexpectedly much later in the day.
- Alternatives: Always fire late; always discard overdue alarms; use an
  operator-configurable grace period.
- Review focus: clock jumps, process downtime, duplicate firing, and visible
  missed state.

## Stylistic

### S1 - Full-Screen Time While Ringing

- Choice: Remove editor chrome while ringing and let the live time fill the
  display, retaining only a quiet dismissal hint and compact failure status.
- Alternative: Keep the editor visible; show a dashboard; add animated sunrise
  graphics.
- When to apply: Only while the observed one-shot alarm is ringing.
