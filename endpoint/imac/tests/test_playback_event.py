import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "files"))

from cortex_playback_event import (
    load_state,
    normalize_event,
    process_event,
    report,
    unavailable,
)


TRACK_ENVIRONMENT = {
    "PLAYER_EVENT": "track_changed",
    "TRACK_ID": "4uLU6hMCjMI75M1A2tKUQC",
    "URI": "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
    "ITEM_TYPE": "Track",
    "NAME": "Never Gonna Give You Up",
    "ARTISTS": "Rick Astley",
    "ALBUM": "Whenever You Need Somebody",
    "COVERS": "https://i.scdn.co/image/first\nhttps://i.scdn.co/image/second",
    "DURATION_MS": "213573",
    "USER_NAME": "private-account",
    "CLIENT_NAME": "private-phone",
}


class PlaybackEventTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.state_path = Path(self.temporary_directory.name) / "state.json"

    def test_normalizes_track_metadata_without_private_fields(self):
        snapshot = normalize_event(TRACK_ENVIRONMENT, unavailable())

        self.assertEqual(
            snapshot,
            {
                "status": "paused",
                "item": {
                    "uri": "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
                    "type": "track",
                    "title": "Never Gonna Give You Up",
                    "creators": ["Rick Astley"],
                    "collection": "Whenever You Need Somebody",
                    "artworkUrl": "https://i.scdn.co/image/first",
                    "durationMs": 213573,
                },
                "positionMs": 0,
            },
        )
        self.assertNotIn("private-account", json.dumps(snapshot))
        self.assertNotIn("private-phone", json.dumps(snapshot))

    def test_normalizes_episode_metadata(self):
        environment = {
            "PLAYER_EVENT": "track_changed",
            "TRACK_ID": "episode-id",
            "URI": "spotify:episode:episode-id",
            "ITEM_TYPE": "Episode",
            "NAME": "An Episode",
            "SHOW_NAME": "A Podcast",
            "COVERS": "https://i.scdn.co/image/episode",
            "DURATION_MS": "3600000",
        }

        snapshot = normalize_event(environment, unavailable())

        self.assertEqual(snapshot["item"]["type"], "episode")
        self.assertEqual(snapshot["item"]["creators"], ["A Podcast"])
        self.assertEqual(snapshot["item"]["collection"], "A Podcast")

    def test_updates_play_pause_resume_and_seek(self):
        snapshot = normalize_event(TRACK_ENVIRONMENT, unavailable())
        events = [
            ("playing", "1200", "playing"),
            ("paused", "2400", "paused"),
            ("playing", "2400", "playing"),
            ("seeked", "45000", "playing"),
        ]

        for event, position, expected_status in events:
            with self.subTest(event=event):
                snapshot = normalize_event(
                    {
                        "PLAYER_EVENT": event,
                        "TRACK_ID": TRACK_ENVIRONMENT["TRACK_ID"],
                        "POSITION_MS": position,
                    },
                    snapshot,
                )
                self.assertEqual(snapshot["status"], expected_status)
                self.assertEqual(snapshot["positionMs"], int(position))

    def test_replaces_playing_with_terminal_states(self):
        playing = normalize_event(TRACK_ENVIRONMENT, unavailable())
        playing["status"] = "playing"

        for event, status in [
            ("stopped", "stopped"),
            ("end_of_track", "stopped"),
            ("unavailable", "unavailable"),
            ("session_disconnected", "unavailable"),
        ]:
            with self.subTest(event=event):
                snapshot = normalize_event({"PLAYER_EVENT": event}, playing)
                self.assertEqual(snapshot, {**unavailable(), "status": status})

    def test_unknown_or_incomplete_events_cannot_replace_state_with_playing(self):
        playing = normalize_event(TRACK_ENVIRONMENT, unavailable())
        playing["status"] = "playing"

        self.assertIsNone(
            normalize_event({"PLAYER_EVENT": "volume_changed"}, playing)
        )
        self.assertEqual(
            normalize_event(
                {
                    "PLAYER_EVENT": "playing",
                    "TRACK_ID": "another-track",
                    "POSITION_MS": "100",
                },
                playing,
            ),
            unavailable(),
        )
        self.assertEqual(
            normalize_event({"PLAYER_EVENT": "track_changed"}, playing),
            unavailable(),
        )

    def test_reporting_failure_preserves_state_for_next_event_recovery(self):
        def fail(_snapshot):
            raise RuntimeError("coordinator unavailable")

        with self.assertRaises(RuntimeError):
            process_event(TRACK_ENVIRONMENT, self.state_path, fail)

        saved = load_state(self.state_path)
        self.assertEqual(saved["item"]["title"], "Never Gonna Give You Up")

        reported = []
        processed = process_event(
            {
                "PLAYER_EVENT": "playing",
                "TRACK_ID": TRACK_ENVIRONMENT["TRACK_ID"],
                "POSITION_MS": "500",
            },
            self.state_path,
            reported.append,
        )

        self.assertTrue(processed)
        self.assertEqual(reported[0]["status"], "playing")
        self.assertEqual(reported[0]["positionMs"], 500)

    def test_damaged_runtime_state_recovers_as_unavailable(self):
        self.state_path.write_text(
            '{"status":"playing","item":{"uri":"spotify:track:id"},'
            '"positionMs":0}'
        )

        self.assertEqual(load_state(self.state_path), unavailable())

    def test_posts_only_the_normalized_snapshot(self):
        coordinator_url = Path(self.temporary_directory.name) / "coordinator-url"
        coordinator_url.write_text("http://coordinator.local:8080\n")
        captured = {}

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data)
            captured["timeout"] = timeout
            return Response()

        report(unavailable(), coordinator_url, opener)

        self.assertEqual(
            captured["url"],
            "http://coordinator.local:8080/api/observations/music/playback",
        )
        self.assertEqual(captured["body"], unavailable())
        self.assertEqual(captured["timeout"], 2)


if __name__ == "__main__":
    unittest.main()
