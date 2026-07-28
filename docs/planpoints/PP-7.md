# PP-7: Wake-Up Alarm

## Slice

One keyboard-set, one-shot alarm can suspend the iMac overnight and wake the
room at the next selected Europe/Stockholm time.

- `Ctrl`+`Alt`+`5` selects one explicit Alarm channel.
- The attached keyboard edits hours and minutes and arms one next-occurrence
  alarm through the coordinator.
- The always-on ThinkPad persists the schedule and remains authoritative while
  the iMac is asleep.
- A second deliberate confirmation arms the iMac's hardware RTC and enters deep
  suspend-to-RAM.
- At the firing time, the coordinator selects the Alarm channel and requests
  exactly `Warm low`; the resumed iMac shows the live time full-screen and
  loops one replaceable local MP3 until dismissal.

This is the smallest useful wake slice because it proves durable scheduling,
one bounded automatic room action, hardware-assisted endpoint sleep, local
alarm audio, and recovery as one observable morning flow.

## Out Of Scope

- Multiple alarms, recurring weekdays, snooze, gradual wake, calendar
  integration, remote editing, voice control, or a general scheduler.
- Arbitrary alarm action lists, selectable scenes, dynamic endpoint commands,
  scripts, shell access, or a general automation engine.
- Automatic idle sleep, hibernation, shutdown, boot-from-off wake, Wake-on-LAN,
  or suspending the ThinkPad and other room devices.
- Streaming, Spotify, synthesized speech, playlists, sound selection in the UI,
  or storing the alarm audio in the repository.
- Guaranteeing wake behavior during a power outage, RTC battery failure,
  ThinkPad outage, or network outage.

## Deferred To Later Planpoints

- Recurrence and snooze remain deferred until the one-shot schedule establishes
  reliable timezone, restart, sleep, wake, and dismissal semantics.
- Sunrise fades and selectable scenes remain deferred because one exact
  existing scene is enough to prove automatic Hue authority.
- Automatic bedtime behavior remains deferred until deliberate suspend proves
  it does not disrupt Music, Camera, AirPlay, or voice interactions.
- More endpoint power operations remain deferred because this slice needs only
  one bounded RTC-suspend command.

## Crossroads

### C1 - Alarm Schedule Authority

- Decision: Whether the browser, iMac, ThinkPad coordinator, or systemd owns the
  alarm schedule.
- Options: Browser timer; iMac-local daemon; coordinator-owned persisted timer;
  dynamically generated systemd timers.
- Impact if wrong: The alarm could disappear with a reload, stop while the iMac
  sleeps, duplicate across machines, or require privileged dynamic units.
- Proposed choice: Persist one normalized one-shot schedule in the ThinkPad
  coordinator's systemd-managed state directory. Publish it over existing SSE
  and derive one in-process timer on startup or update.
- Why: The ThinkPad is already the always-on state and action authority. The
  browser and iMac deliberately stop executing during suspend.
- Status: decided

### C2 - Endpoint Sleep And Wake Boundary

- Decision: How the old iMac stops overnight work and resumes at the alarm
  time.
- Options: Screen blanking; suspend-to-idle; deep suspend-to-RAM with RTC;
  hibernate; power off plus RTC or Wake-on-LAN.
- Impact if wrong: The endpoint may continue consuming power, fail to wake,
  require a login, or gain an overly broad privileged control path.
- Proposed choice: Use `/usr/sbin/rtcwake --utc --mode mem --time <epoch>`
  behind one root-owned argument-validating helper and one exact-origin
  loopback operation. Require a second deliberate Enter after the alarm is
  observed armed.
- Why: The real endpoint reports `mem`, selected `deep`, `rtc_cmos`, a
  `wakealarm` interface, installed `rtcwake`, UTC hardware clock, and
  synchronized time. A physical suspend/resume qualification still decides
  whether the observed capability is reliable.
- Status: decided

### C3 - Automatic Room Action Boundary

- Decision: What authority a due alarm receives without a current human input.
- Options: Display/audio only; one fixed scene; user-selected scene; general
  action list or automation rule.
- Impact if wrong: A scheduler could become a broad autonomous control path or
  claim success without observed room state.
- Proposed choice: Permit one fixed automatic request for the exact detected
  scene `Warm low`, routed through the same coordinator validation and observed
  completion used by human and agent scene requests.
- Why: The requested wake behavior needs one predictable light change and does
  not justify configurable automation.
- Status: decided

### C4 - Alarm Audio Ownership

- Decision: Whether alarm audio is bundled in the web client, served by the
  ThinkPad, stored on the iMac, or delegated to Spotify.
- Options: Client asset; authenticated coordinator response; one endpoint-local
  file; streaming service; generated tone.
- Impact if wrong: Audio may be unavailable immediately after resume, require a
  client rebuild to change, depend on the network, or create a broad media
  feature.
- Proposed choice: Install one root-owned fixed MP3 at
  `/etc/cortex-endpoint/wake-alarm.mp3` through
  `./endpoint/imac/provision-alarm-audio <local-mp3>`. Loop one owned local
  player through the accepted PulseAudio/Sonos route and control it from the
  exact-origin endpoint bridge.
- Why: The sound can start locally after resume and can be replaced without
  application deployment or a new media catalog.
- Status: decided

## Plumbing

- State boundary: `alarm.state` publishes only exact state, selected local
  `HH:MM`, resolved UTC `firesAt`, and bounded failure status.
- Action boundary: fixed coordinator actions arm, disarm, and dismiss one alarm;
  the due timer may request only exact `Warm low`.
- Persistence boundary: one atomically replaced JSON document below the
  coordinator service's `StateDirectory`; no history or recurring rule store.
- Channel boundary: `channel.select` adds only `alarm`, and the application
  retains its explicit hard-coded channel switch.
- Keyboard boundary: global `Ctrl`+`Alt`+`5` selects Alarm; unmodified
  field-editing keys exist only while Alarm is mounted.
- Power boundary: the browser can request only the observed armed `firesAt`
  through the exact-origin loopback bridge. A narrow root helper validates the
  epoch and invokes only `rtcwake`.
- Audio boundary: one fixed endpoint MP3, one player PID, and start/stop/status
  operations; no browsing, upload UI, playlist, or remote stream.
- Recovery boundary: the coordinator owns late/missed semantics; the endpoint
  reports sleep and playback failures without claiming wake success.

## Issues

1. **GH-021 - Wake The Room**: persist one next-occurrence alarm, add the
   keyboard Alarm view, fire full-screen time plus exact `Warm low` and local
   audio, install replaceable audio, and qualify deliberate RTC suspend/resume
   on the physical iMac.

## Qualification Baseline

Read-only inspection on 2026-07-27 found:

- `/sys/power/state`: `freeze mem disk`
- `/sys/power/mem_sleep`: `s2idle [deep]`
- RTC driver: `rtc_cmos 00:03`
- `/sys/class/rtc/rtc0/wakealarm` and `/dev/rtc0` present
- `/usr/sbin/rtcwake` installed
- system and hardware clocks in UTC with NTP synchronized

These facts make the proposal credible but do not prove that the 2008 iMac
firmware resumes its graphics, network, USB keyboard, audio, and kiosk session
reliably. GH-021 must perform that bounded physical qualification before
shipping the sleep path.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: alarm schedule authority; see Crossroads section.
- C2: endpoint sleep and wake boundary; see Crossroads section.
- C3: automatic room action boundary; see Crossroads section.
- C4: alarm audio ownership; see Crossroads section.

### Hot

#### H1 - One Next Occurrence

- Decision: Interpret `HH:MM` as one future Europe/Stockholm occurrence and
  disarm after dismissal.
- Why: It proves the complete wake path without recurrence rules or hidden
  morning automation.
- Alternatives: Countdown duration; daily recurrence; weekday schedule.

#### H2 - Explicitly Confirm Suspend

- Decision: Arm first and suspend only after a second Enter against observed
  state.
- Why: Endpoint power changes need clearer intent than editing or submitting a
  schedule.
- Alternatives: Suspend immediately; automatic idle timer; separate power key.

#### H3 - Isolate Wake Effects

- Decision: Display, light, and audio attempt independently and report their
  own failures while the alarm remains dismissible.
- Why: Missing Hue or audio must not prevent the time display, and one failed
  effect must not trigger retries or duplicate players.
- Alternatives: All-or-nothing firing; autonomous retries; silent partial
  failure.

## References

- `rtcwake(8)`:
  `https://man7.org/linux/man-pages/man8/rtcwake.8.html`
- Linux RTC documentation:
  `https://docs.kernel.org/admin-guide/rtc.html`
- Linux device wakeup model:
  `https://docs.kernel.org/driver-api/pm/devices.html`
