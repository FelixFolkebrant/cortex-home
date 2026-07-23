# GH-002 Review: Qualify The iMac Endpoint

# Summary

- The branch records a useful, sanitized endpoint baseline and correctly hands
  persistent Wi-Fi, device-permission, mixer, kiosk-load, and Sonos work to
  GH-003.
- The hardware observations, 15-minute measurements, reboot recovery, and
  manual noise and speaker confirmations are internally consistent.
- No network address, hardware address, UUID, machine ID, boot ID, SSH material,
  or raw identifying log was found in the changed documents.
- Both accepted documentation findings were fixed and verified.

# Findings

## 1. The Checked Inventory Criterion Is Not Fully Recorded

- Severity: 3
- Heat: Cold
- Status: fixed
- Location: `docs/wip/GH-002.md:15`

### Problem

The issue record checks an acceptance criterion requiring installed memory and
relevant USB controllers to be recorded. The durable baseline and issue notes
record 3.8 GiB of usable memory and enumerate USB devices, but they do not state
the installed memory capacity or the detected Intel ICH8 UHCI/EHCI controller
families. A checked criterion therefore promises slightly more evidence than
the record contains.

### Fix

Record the installed-versus-usable memory distinction if the installed capacity
can be confirmed, and add the already observed Intel ICH8 USB 1.1/2.0
controllers to the issue inventory. If installed capacity cannot be confirmed
without extending qualification, narrow the criterion to usable memory and
state that limitation explicitly.

### Verification

Verified: `lshw` reports 4 GiB installed memory while procfs reports 3.8 GiB
usable memory, and the previously collected `lspci -nnk` output identifies the
Intel ICH8 UHCI/EHCI USB 1.1/2.0 controllers. Both values now appear in the
project baseline and issue record.

## 2. The Audio Task Contradicts The Accepted Sonos Deferral

- Severity: 2
- Heat: Cold
- Status: fixed
- Location: `docs/wip/GH-002-PLAN.md:86`

### Problem

The plan's Deferred section and acceptance criteria correctly say that the
Sonos is not physically connected and end-to-end playback belongs in GH-003.
The task list still says to test “the analog output connected to the Sonos,”
which describes a physical state that did not exist during GH-002 and makes the
otherwise explicit plan diff look incomplete.

### Fix

Change the task to say that GH-002 tests the rear analog output independently
and defers end-to-end Sonos playback until the physical connection exists.

### Verification

Verified: The task now names the rear analog output independently and explicitly
defers end-to-end Sonos playback until the physical connection exists, matching
the Deferred, Acceptance Criteria, and Plan Diff sections.

# Severity Scale

| Level | Name | Meaning | Action |
|---|---|---|---|
| 5 | Critical / Blocker | Broken build, severe bug, data loss, or security risk. | Must fix before merge. |
| 4 | Major | Logical flaw, architectural violation, or performance trap. | Must fix before merge. |
| 3 | Moderate | Edge-case risk, missing tests, or hard-to-maintain code. | Should fix unless intentionally deferred. |
| 2 | Minor | Suboptimal approach, duplication, or readability issue. | Optional fix. |
| 1 | Nitpick | Pure style, naming, or formatting. | Informational. |
