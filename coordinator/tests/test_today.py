import json
import tempfile
import unittest
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from today import (
    LOCATIONFORECAST_URL,
    TIME_ZONE,
    USER_AGENT,
    TodayAdapter,
    TodayUnavailable,
)


def forecast():
    entries = []
    for day, temperatures, condition in (
        ("2026-07-26", (18.2, 21.8), "partlycloudy_day"),
        ("2026-07-27", (15.1, 19.9), "rainshowers_day"),
        ("2026-07-28", (12.4, 17.6), "clearsky_day"),
    ):
        for hour, temperature in zip((10, 14), temperatures):
            entries.append(
                {
                    "time": f"{day}T{hour:02}:00:00Z",
                    "data": {
                        "instant": {"details": {"air_temperature": temperature}},
                        "next_1_hours": {
                            "summary": {"symbol_code": condition},
                        },
                    },
                }
            )
    entries.append(
        {
            "time": "2026-07-29T12:00:00Z",
            "data": {"instant": {"details": {"air_temperature": 24.1}}},
        }
    )
    return {"properties": {"timeseries": entries}}


class Response:
    def __init__(self, payload, expires, last_modified="Sun, 26 Jul 2026 09:00:00 GMT"):
        self.status = 200
        self.payload = json.dumps(payload).encode()
        self.headers = Message()
        self.headers["Expires"] = expires
        self.headers["Last-Modified"] = last_modified

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size):
        return self.payload


class TodayAdapterTests(unittest.TestCase):
    def setUp(self):
        self.cache = tempfile.TemporaryDirectory()
        self.addCleanup(self.cache.cleanup)
        self.cache_path = Path(self.cache.name, "locationforecast.json")
        self.now = datetime(2026, 7, 26, 10, tzinfo=timezone.utc)

    def test_normalizes_linkoping_current_conditions_and_three_days(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return Response(forecast(), "Sun, 26 Jul 2026 11:00:00 GMT")

        summary = TodayAdapter(
            self.cache_path,
            lambda _summary: None,
            opener=opener,
            now=lambda: self.now,
        ).refresh()

        self.assertEqual(summary["status"], "available")
        self.assertEqual(summary["timeZone"], TIME_ZONE)
        self.assertEqual(
            summary["current"],
            {"condition": "partly_cloudy", "temperatureC": 18},
        )
        self.assertEqual(
            summary["forecast"],
            [
                {
                    "condition": "partly_cloudy",
                    "date": "2026-07-26",
                    "highC": 22,
                    "lowC": 18,
                },
                {
                    "condition": "rain",
                    "date": "2026-07-27",
                    "highC": 20,
                    "lowC": 15,
                },
                {
                    "condition": "clear",
                    "date": "2026-07-28",
                    "highC": 18,
                    "lowC": 12,
                },
            ],
        )
        request, timeout = requests[0]
        self.assertEqual(request.full_url, LOCATIONFORECAST_URL)
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertEqual(request.get_header("Accept-encoding"), "gzip, deflate")
        self.assertEqual(timeout, 10)

    def test_uses_an_unexpired_cached_response_without_a_request(self):
        adapter = TodayAdapter(
            self.cache_path,
            lambda _summary: None,
            opener=lambda *_args, **_kwargs: self.fail("unexpected request"),
            now=lambda: self.now,
        )
        adapter._write_cache(
            {
                "expires": "Sun, 26 Jul 2026 11:00:00 GMT",
                "forecast": forecast(),
                "lastModified": "Sun, 26 Jul 2026 09:00:00 GMT",
            }
        )

        summary = adapter.refresh()

        self.assertEqual(summary["status"], "available")

    def test_revalidates_an_expired_cached_response(self):
        requests = []

        def opener(request, timeout):
            requests.append(request)
            return Response(forecast(), "Sun, 26 Jul 2026 12:00:00 GMT")

        adapter = TodayAdapter(
            self.cache_path,
            lambda _summary: None,
            opener=opener,
            now=lambda: self.now,
        )
        adapter._write_cache(
            {
                "expires": "Sun, 26 Jul 2026 09:00:00 GMT",
                "forecast": forecast(),
                "lastModified": "Sun, 26 Jul 2026 08:00:00 GMT",
            }
        )

        adapter.refresh()

        self.assertEqual(
            requests[0].get_header("If-modified-since"),
            "Sun, 26 Jul 2026 08:00:00 GMT",
        )

    def test_rejects_a_deprecated_response(self):
        class DeprecatedResponse(Response):
            def __init__(self):
                super().__init__(forecast(), "Sun, 26 Jul 2026 11:00:00 GMT")
                self.status = 203

        adapter = TodayAdapter(
            self.cache_path,
            lambda _summary: None,
            opener=lambda *_args, **_kwargs: DeprecatedResponse(),
            now=lambda: self.now,
        )

        with self.assertRaises(TodayUnavailable):
            adapter.refresh()


if __name__ == "__main__":
    unittest.main()
