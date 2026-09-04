import unittest
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from context import build_answer_context, build_room_context


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
    def test_answer_context_contains_both_home_regions(self):
        context = build_answer_context(TODAY, MUSIC)

        self.assertEqual(set(context), {"home"})
        self.assertEqual(set(context["home"]), {"today", "music"})
        self.assertEqual(context["home"]["today"]["current"]["temperatureC"], 20.5)
        self.assertEqual(
            context["home"]["music"]["title"], "Never Gonna Give You Up"
        )
        self.assertNotIn("artworkUrl", context["home"]["music"])
        self.assertNotIn("uri", context["home"]["music"])

    def test_room_context_adds_internal_lighting_observation(self):
        context = build_room_context(TODAY, MUSIC, LIGHTING)

        self.assertEqual(set(context), {"home", "lighting"})
        self.assertEqual(
            context["lighting"],
            {
                "available": True,
                "scenes": ["Bright", "Relax", "Warm"],
                "activeScenes": ["Warm"],
                "observedAt": "2026-07-26T12:00:02.000Z",
            },
        )

    def test_unavailable_home_regions_stay_small(self):
        context = build_room_context(
            {
                "status": "unavailable",
                "timeZone": "Europe/Stockholm",
                "current": None,
                "forecast": [],
                "observedAt": "2026-07-26T12:00:05.000Z",
            },
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
            context["home"]["today"],
            {
                "type": "today",
                "available": False,
                "timeZone": "Europe/Stockholm",
                "current": None,
                "forecast": [],
                "observedAt": "2026-07-26T12:00:05.000Z",
            },
        )
        self.assertEqual(
            context["home"]["music"],
            {
                "type": "music",
                "available": False,
                "playbackState": "unavailable",
                "observedAt": "2026-07-26T12:00:03.000Z",
            },
        )

    def test_invalid_inputs_fail_closed_without_forwarding_unknown_fields(self):
        context = build_room_context(
            {**TODAY, "provider": "met.no"},
            {**MUSIC, "endpointToken": "secret"},
            {**LIGHTING, "bridgeId": "secret"},
        )

        self.assertEqual(
            context["home"],
            {
                "today": {"type": "today", "available": False},
                "music": {"type": "music", "available": False},
            },
        )
        self.assertEqual(
            context["lighting"],
            {"available": False, "scenes": [], "activeScenes": []},
        )

    def test_returned_nested_values_are_isolated_copies(self):
        context = build_room_context(TODAY, MUSIC, LIGHTING)

        context["home"]["music"]["creators"].append("Mutated")
        context["lighting"]["scenes"].append("Mutated")
        context["lighting"]["activeScenes"].clear()

        self.assertEqual(MUSIC["item"]["creators"], ["Rick Astley"])
        self.assertEqual(LIGHTING["scenes"], ["Bright", "Relax", "Warm"])
        self.assertEqual(LIGHTING["activeScenes"], ["Warm"])


if __name__ == "__main__":
    unittest.main()
