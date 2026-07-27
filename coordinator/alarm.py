import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


TIME_ZONE = ZoneInfo("Europe/Stockholm")
TIME_PATTERN = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
STATES = {"disarmed", "armed", "ringing", "missed", "failed"}
RECOVERY_GRACE = timedelta(minutes=15)
MAX_ERROR_LENGTH = 160


@dataclass(frozen=True)
class AlarmSnapshot:
    status: str
    time: str | None
    firesAt: str | None
    error: str | None

    def payload(self):
        return asdict(self)


DISARMED = AlarmSnapshot("disarmed", None, None, None)


def utc_now():
    return datetime.now(timezone.utc)


def next_occurrence(time_text, now):
    if not isinstance(time_text, str) or not TIME_PATTERN.fullmatch(time_text):
        raise ValueError("Alarm time must be an HH:MM value.")

    local_now = now.astimezone(TIME_ZONE)
    hour, minute = (int(part) for part in time_text.split(":"))
    target_date = local_now.date()
    if (hour, minute) <= (local_now.hour, local_now.minute):
        target_date += timedelta(days=1)

    candidates = {
        datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            tzinfo=TIME_ZONE,
            fold=fold,
        )
        .astimezone(timezone.utc)
        for fold in (0, 1)
        if datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            tzinfo=TIME_ZONE,
            fold=fold,
        )
        .astimezone(timezone.utc)
        .astimezone(TIME_ZONE)
        .replace(tzinfo=None)
        == datetime(target_date.year, target_date.month, target_date.day, hour, minute)
    }
    if not candidates:
        raise ValueError("Alarm time does not exist on the next calendar occurrence.")

    return min(candidate for candidate in candidates if candidate > now)


def utc_text(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def parse_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Alarm firesAt must be a UTC timestamp.")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise ValueError("Alarm firesAt must be a UTC timestamp.") from error
    if parsed.tzinfo != timezone.utc or utc_text(parsed) != value:
        raise ValueError("Alarm firesAt must be a UTC timestamp.")
    return parsed


def armed_alarm(time_text, now):
    return AlarmSnapshot("armed", time_text, utc_text(next_occurrence(time_text, now)), None)


def due_state(snapshot, now):
    if snapshot.status != "armed":
        return snapshot
    delay = now - parse_utc(snapshot.firesAt)
    if delay < timedelta(0):
        return snapshot
    status = "ringing" if delay <= RECOVERY_GRACE else "missed"
    return AlarmSnapshot(status, snapshot.time, snapshot.firesAt, None)


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "status",
        "time",
        "firesAt",
        "error",
    }:
        raise ValueError("Invalid persisted alarm state.")
    status = snapshot["status"]
    time_text = snapshot["time"]
    fires_at = snapshot["firesAt"]
    error = snapshot["error"]
    if status not in STATES:
        raise ValueError("Invalid persisted alarm state.")
    if status == "disarmed":
        if time_text is not None or fires_at is not None or error is not None:
            raise ValueError("Invalid persisted alarm state.")
    else:
        if not isinstance(time_text, str) or not TIME_PATTERN.fullmatch(time_text):
            raise ValueError("Invalid persisted alarm state.")
        parse_utc(fires_at)
        if status == "failed":
            if not isinstance(error, str) or not 1 <= len(error) <= MAX_ERROR_LENGTH:
                raise ValueError("Invalid persisted alarm state.")
        elif error is not None:
            raise ValueError("Invalid persisted alarm state.")
    return AlarmSnapshot(status, time_text, fires_at, error)


class AlarmStore:
    def __init__(self, path):
        self.path = Path(path) if path else None

    def load(self):
        if self.path is None or not self.path.exists():
            return DISARMED
        try:
            snapshot = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Could not read persisted alarm state.") from error
        return validate_snapshot(snapshot)

    def save(self, snapshot):
        if self.path is None:
            return
        encoded = json.dumps(snapshot.payload(), separators=(",", ":"))
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(encoded)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
            directory = os.open(self.path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
