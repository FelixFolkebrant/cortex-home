import unittest
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from context import build_room_context


TODAY = {
    "status": "available",
    "timeZone": "Europe/Stockholm",
    "current": {"condition": "clearsky_day", "temperatureC": 20.5},
    "forecast": [
        {
            "condition": "partlycloudy_day",
            "date": "2026-07-26",
            "highC": 22.0,
            "lowC": 14.0,
        }
    ],
    "observedAt": "2026-07-26T12:00:00.000Z",
}
MUSIC = {
    "status": "playing",
    "item": {
        "uri": "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
        "type": "track",
        "title": "Never Gonna Give You Up",
        "creators": ["Rick Astley"],
        "collection": "Whenever You Need Somebody",
        "artworkUrl": "https://i.scdn.co/image/first",
        "durationMs": 213573,
    },
    "positionMs": 1200,
    "observedAt": "2026-07-26T12:00:01.000Z",
}
LIGHTING = {
    "status": "available",
    "scenes": ["Bright", "Relax", "Warm"],
    "activeScenes": ["Warm"],
    "observedAt": "2026-07-26T12:00:02.000Z",
}


class ContextTests(unittest.TestCase):
    def test_projects_only_today_when_today_is_active(self):
        context = build_room_context("today", TODAY, MUSIC, LIGHTING)

        self.assertEqual(set(context), {"activeChannel", "channel", "lighting"})
        self.assertEqual(context["activeChannel"], "today")
        self.assertEqual(
            context["channel"],
            {
                "type": "today",
                "available": True,
                "timeZone": "Europe/Stockholm",
                "current": {
                    "condition": "clearsky_day",
                    "temperatureC": 20.5,
                },
                "forecast": [
                    {
                        "condition": "partlycloudy_day",
                        "date": "2026-07-26",
                        "highC": 22.0,
                        "lowC": 14.0,
                    }
                ],
                "observedAt": "2026-07-26T12:00:00.000Z",
            },
        )
        self.assertNotIn("playbackState", context["channel"])

    def test_projects_music_without_provider_or_artwork_fields(self):
        context = build_room_context("music", TODAY, MUSIC, LIGHTING)

        self.assertEqual(context["activeChannel"], "music")
        self.assertEqual(
            context["channel"],
            {
                "type": "music",
                "available": True,
                "playbackState": "playing",
                "itemType": "track",
                "title": "Never Gonna Give You Up",
                "creators": ["Rick Astley"],
                "collection": "Whenever You Need Somebody",
                "positionMs": 1200,
                "durationMs": 213573,
                "observedAt": "2026-07-26T12:00:01.000Z",
            },
        )
        self.assertNotIn("artworkUrl", context["channel"])
        self.assertNotIn("uri", context["channel"])
        self.assertNotIn("forecast", context["channel"])

    def test_projects_lighting(self):
        context = build_room_context("today", TODAY, MUSIC, LIGHTING)

        self.assertEqual(
            context["lighting"],
            {
                "available": True,
                "scenes": ["Bright", "Relax", "Warm"],
                "activeScenes": ["Warm"],
                "observedAt": "2026-07-26T12:00:02.000Z",
            },
        )

    def test_unavailable_snapshots_stay_small(self):
        context = build_room_context(
            "music",
            TODAY,
            {
                "status": "unavailable",
                "item": None,
                "positionMs": 0,
                "observedAt": "2026-07-26T12:00:03.000Z",
            },
            {
                "status": "unavailable",
                "scenes": [],
                "activeScenes": [],
                "observedAt": "2026-07-26T12:00:04.000Z",
            },
        )

        self.assertEqual(
            context["channel"],
            {
                "type": "music",
                "available": False,
                "playbackState": "unavailable",
                "observedAt": "2026-07-26T12:00:03.000Z",
            },
        )
        self.assertEqual(
            context["lighting"],
            {
                "available": False,
                "scenes": [],
                "activeScenes": [],
                "observedAt": "2026-07-26T12:00:04.000Z",
            },
        )

        today_context = build_room_context(
            "today",
            {
                "status": "unavailable",
                "timeZone": "Europe/Stockholm",
                "current": None,
                "forecast": [],
                "observedAt": "2026-07-26T12:00:05.000Z",
            },
            MUSIC,
            LIGHTING,
        )
        self.assertEqual(
            today_context["channel"],
            {
                "type": "today",
                "available": False,
                "timeZone": "Europe/Stockholm",
                "current": None,
                "forecast": [],
                "observedAt": "2026-07-26T12:00:05.000Z",
            },
        )

    def test_invalid_inputs_fail_closed_without_forwarding_unknown_fields(self):
        context = build_room_context(
            "headlines",
            {**TODAY, "provider": "met.no"},
            {**MUSIC, "endpointToken": "secret"},
            {**LIGHTING, "bridgeId": "secret"},
        )

        self.assertEqual(context["activeChannel"], "today")
        self.assertEqual(context["channel"], {"type": "today", "available": False})
        self.assertEqual(
            context["lighting"],
            {"available": False, "scenes": [], "activeScenes": []},
        )

    def test_returned_nested_values_are_isolated_copies(self):
        context = build_room_context("music", TODAY, MUSIC, LIGHTING)

        context["channel"]["creators"].append("Mutated")
        context["lighting"]["scenes"].append("Mutated")
        context["lighting"]["activeScenes"].clear()

        self.assertEqual(MUSIC["item"]["creators"], ["Rick Astley"])
        self.assertEqual(LIGHTING["scenes"], ["Bright", "Relax", "Warm"])
        self.assertEqual(LIGHTING["activeScenes"], ["Warm"])


if __name__ == "__main__":
    unittest.main()
