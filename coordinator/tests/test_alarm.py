import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from alarm import AlarmSnapshot, AlarmStore, due_state, next_occurrence


class AlarmOccurrenceTests(unittest.TestCase):
    def test_uses_tomorrow_when_the_selected_minute_has_passed(self):
        now = datetime(2026, 7, 27, 19, 31, tzinfo=timezone.utc)

        fires_at = next_occurrence("21:30", now)

        self.assertEqual(
            fires_at,
            datetime(2026, 7, 28, 19, 30, tzinfo=timezone.utc),
        )

    def test_rejects_the_spring_clock_gap(self):
        now = datetime(2026, 3, 29, 0, 30, tzinfo=timezone.utc)

        with self.assertRaises(ValueError):
            next_occurrence("02:30", now)

    def test_chooses_the_earliest_future_autumn_occurrence(self):
        now = datetime(2026, 10, 24, 22, 0, tzinfo=timezone.utc)

        fires_at = next_occurrence("02:30", now)

        self.assertEqual(
            fires_at,
            datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc),
        )

    def test_marks_only_recent_due_alarms_as_ringing(self):
        snapshot = AlarmSnapshot(
            "armed",
            "08:00",
            "2026-07-27T06:00:00Z",
            None,
        )

        self.assertEqual(
            due_state(snapshot, datetime(2026, 7, 27, 6, 15, tzinfo=timezone.utc)).status,
            "ringing",
        )
        self.assertEqual(
            due_state(snapshot, datetime(2026, 7, 27, 6, 15, 1, tzinfo=timezone.utc)).status,
            "missed",
        )


class AlarmStoreTests(unittest.TestCase):
    def test_replaces_the_complete_normalized_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "alarm.json")
            store = AlarmStore(path)
            expected = AlarmSnapshot(
                "armed",
                "07:15",
                "2026-07-28T05:15:00Z",
                None,
            )

            store.save(expected)

            self.assertEqual(store.load(), expected)
            self.assertEqual(json.loads(path.read_text()), expected.payload())

    def test_rejects_an_invalid_persisted_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "alarm.json")
            path.write_text('{"status":"armed"}')

            with self.assertRaises(ValueError):
                AlarmStore(path).load()


if __name__ == "__main__":
    unittest.main()
