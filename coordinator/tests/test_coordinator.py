import http.client
import json
import queue
import threading
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from cortex_home import ACTION, ApiError, Coordinator, CortexHomeServer


PLAYING_OBSERVATION = {
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
}


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = Coordinator(action_timeout=0.1)
        self.endpoint = self.coordinator.connect_endpoint()
        event, _payload = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "music.playback")

    def submit_in_background(self, request_id="request-1"):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.coordinator.submit, request_id, ACTION)
        self.addCleanup(executor.shutdown)
        return future

    def next_identify(self):
        event, payload = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "identify")
        return payload

    def test_completes_with_the_caller_request_id(self):
        future = self.submit_in_background()
        self.assertEqual(self.next_identify()["requestId"], "request-1")

        identifying = self.coordinator.update(
            self.endpoint.token,
            "request-1",
            "identifying",
        )
        self.assertEqual(identifying["status"], "identifying")
        self.coordinator.update(
            self.endpoint.token,
            "request-1",
            "completed",
        )

        status, payload = future.result(timeout=1)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(
            payload,
            {
                "requestId": "request-1",
                "action": ACTION,
                "status": "completed",
            },
        )

    def test_returns_endpoint_failure(self):
        future = self.submit_in_background()
        self.next_identify()
        self.coordinator.update(
            self.endpoint.token,
            "request-1",
            "identifying",
        )
        self.coordinator.update(
            self.endpoint.token,
            "request-1",
            "failed",
            "audio unavailable",
        )

        status, payload = future.result(timeout=1)
        self.assertEqual(status, HTTPStatus.BAD_GATEWAY)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error"], "audio unavailable")

    def test_disconnect_fails_the_active_request(self):
        future = self.submit_in_background()
        self.next_identify()
        self.coordinator.disconnect_endpoint(self.endpoint.token)

        status, payload = future.result(timeout=1)
        self.assertEqual(status, HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(payload["error"], "endpoint disconnected")

    def test_times_out_and_notifies_the_endpoint(self):
        future = self.submit_in_background()
        self.next_identify()

        status, payload = future.result(timeout=1)
        self.assertEqual(status, HTTPStatus.GATEWAY_TIMEOUT)
        self.assertEqual(payload["error"], "action timed out")

        event, result = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "result")
        self.assertEqual(result["requestId"], "request-1")
        self.assertEqual(result["status"], "failed")

    def test_rejects_a_duplicate_request_id(self):
        future = self.submit_in_background()
        self.next_identify()
        self.coordinator.update(
            self.endpoint.token,
            "request-1",
            "identifying",
        )
        self.coordinator.update(
            self.endpoint.token,
            "request-1",
            "completed",
        )
        future.result(timeout=1)

        with self.assertRaises(ApiError) as raised:
            self.coordinator.submit("request-1", ACTION)

        self.assertEqual(raised.exception.status, HTTPStatus.CONFLICT)
        self.assertEqual(raised.exception.code, "duplicate_request_id")

    def test_rejects_a_second_active_request(self):
        future = self.submit_in_background()
        self.next_identify()

        with self.assertRaises(ApiError) as raised:
            self.coordinator.submit("request-2", ACTION)

        self.assertEqual(raised.exception.status, HTTPStatus.CONFLICT)
        self.assertEqual(raised.exception.code, "endpoint_busy")
        self.coordinator.disconnect_endpoint(self.endpoint.token)
        future.result(timeout=1)

    def test_rejects_invalid_request_ids_and_unknown_actions(self):
        for request_id in ("", "space here", "x" * 65, None):
            with self.subTest(request_id=request_id):
                with self.assertRaises(ApiError) as raised:
                    self.coordinator.submit(request_id, ACTION)
                self.assertEqual(raised.exception.code, "invalid_request_id")

        with self.assertRaises(ApiError) as raised:
            self.coordinator.submit("request-2", "endpoint.restart")
        self.assertEqual(raised.exception.code, "unknown_action")

    def test_rejects_invalid_endpoint_callbacks(self):
        future = self.submit_in_background()
        self.next_identify()

        cases = [
            ("", "request-1", "identifying", None, "missing_endpoint_token"),
            ("stale", "request-1", "identifying", None, "stale_endpoint"),
            (
                self.endpoint.token,
                "missing",
                "identifying",
                None,
                "unknown_request",
            ),
            (
                self.endpoint.token,
                "request-1",
                "completed",
                None,
                "invalid_transition",
            ),
            (
                self.endpoint.token,
                "request-1",
                "failed",
                None,
                "missing_error",
            ),
        ]

        for token, request_id, status, error, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(ApiError) as raised:
                    self.coordinator.update(token, request_id, status, error)
                self.assertEqual(raised.exception.code, code)

        self.coordinator.disconnect_endpoint(self.endpoint.token)
        future.result(timeout=1)

    def test_sends_the_current_playback_snapshot_on_connection(self):
        coordinator = Coordinator()
        endpoint = coordinator.connect_endpoint()

        event, snapshot = endpoint.events.get(timeout=1)

        self.assertEqual(event, "music.playback")
        self.assertEqual(snapshot["status"], "unavailable")
        self.assertIsNone(snapshot["item"])
        self.assertEqual(snapshot["positionMs"], 0)
        self.assertRegex(
            snapshot["observedAt"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$",
        )

        coordinator.disconnect_endpoint(endpoint.token)
        coordinator.report_playback(PLAYING_OBSERVATION)
        endpoint = coordinator.connect_endpoint()
        event, snapshot = endpoint.events.get(timeout=1)
        self.assertEqual(event, "music.playback")
        self.assertEqual(snapshot["status"], "playing")
        self.assertEqual(snapshot["item"]["title"], "Never Gonna Give You Up")

    def test_replaces_and_publishes_only_changed_playback(self):
        snapshot = self.coordinator.report_playback(PLAYING_OBSERVATION)

        self.assertEqual(snapshot["status"], "playing")
        self.assertEqual(snapshot["item"]["type"], "track")
        self.assertIn("observedAt", snapshot)
        event, published = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "music.playback")
        self.assertEqual(published, snapshot)

        latest = self.coordinator.report_playback(PLAYING_OBSERVATION)
        self.assertEqual(self.coordinator.playback, latest)
        with self.assertRaises(queue.Empty):
            self.endpoint.events.get_nowait()

        stopped = self.coordinator.report_playback(
            {"status": "stopped", "item": None, "positionMs": 0}
        )
        self.assertEqual(stopped["status"], "stopped")
        self.assertIsNone(stopped["item"])
        event, published = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "music.playback")
        self.assertEqual(published, stopped)

    def test_rejects_malformed_playback_without_replacing_current_state(self):
        accepted = self.coordinator.report_playback(PLAYING_OBSERVATION)
        self.endpoint.events.get(timeout=1)
        invalid_observations = [
            {},
            {**PLAYING_OBSERVATION, "extra": True},
            {**PLAYING_OBSERVATION, "status": "buffering"},
            {**PLAYING_OBSERVATION, "status": []},
            {**PLAYING_OBSERVATION, "positionMs": -1},
            {**PLAYING_OBSERVATION, "positionMs": True},
            {**PLAYING_OBSERVATION, "positionMs": 213574},
            {
                **PLAYING_OBSERVATION,
                "item": {**PLAYING_OBSERVATION["item"], "unknown": True},
            },
            {
                **PLAYING_OBSERVATION,
                "item": {
                    **PLAYING_OBSERVATION["item"],
                    "uri": "spotify:episode:4uLU6hMCjMI75M1A2tKUQC",
                },
            },
            {
                **PLAYING_OBSERVATION,
                "item": {
                    **PLAYING_OBSERVATION["item"],
                    "artworkUrl": "http://example.com/artwork",
                },
            },
            {
                **PLAYING_OBSERVATION,
                "item": {
                    **PLAYING_OBSERVATION["item"],
                    "artworkUrl": "https://[invalid",
                },
            },
            {
                **PLAYING_OBSERVATION,
                "item": {
                    **PLAYING_OBSERVATION["item"],
                    "type": {},
                },
            },
            {"status": "stopped", "item": None, "positionMs": 1},
        ]

        for observation in invalid_observations:
            with self.subTest(observation=observation):
                with self.assertRaises(ApiError) as raised:
                    self.coordinator.report_playback(observation)
                self.assertEqual(raised.exception.code, "invalid_playback")
                self.assertEqual(self.coordinator.playback, accepted)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_directory = tempfile.TemporaryDirectory()
        client_path = Path(cls.client_directory.name)
        client_path.joinpath("assets").mkdir()
        client_path.joinpath("index.html").write_text(
            '<div id="root"></div><script src="/assets/app.js"></script>'
        )
        client_path.joinpath("assets", "app.js").write_text("const ready = true;")
        cls.server = CortexHomeServer(
            ("127.0.0.1", 0),
            Coordinator(action_timeout=0.05),
            client_path,
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)
        cls.client_directory.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1)
        self.addCleanup(connection.close)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = json.loads(response.read())
        return response.status, payload

    @staticmethod
    def read_event(response):
        event = response.readline().decode().strip().removeprefix("event: ")
        data = response.readline().decode().strip().removeprefix("data: ")
        response.readline()
        return event, json.loads(data)

    def test_completes_an_action_over_http(self):
        events_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(events_connection.close)
        events_connection.request("GET", "/api/events")
        events_response = events_connection.getresponse()
        self.assertEqual(events_response.status, HTTPStatus.OK)

        event, ready = self.read_event(events_response)
        self.assertEqual(event, "ready")
        endpoint_token = ready["endpointToken"]
        event, playback = self.read_event(events_response)
        self.assertEqual(event, "music.playback")
        self.assertIn(playback["status"], {"playing", "unavailable"})

        def submit_action():
            connection = http.client.HTTPConnection(
                "127.0.0.1",
                self.port,
                timeout=1,
            )
            try:
                connection.request(
                    "POST",
                    "/api/actions",
                    body=json.dumps(
                        {"requestId": "http-request", "action": ACTION}
                    ),
                    headers={"Content-Type": "application/json"},
                )
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(submit_action)
            event, identify = self.read_event(events_response)
            self.assertEqual(event, "identify")
            self.assertEqual(identify["requestId"], "http-request")

            headers = {
                "Content-Type": "application/json",
                "X-Endpoint-Token": endpoint_token,
            }
            status, payload = self.request(
                "POST",
                "/api/requests/http-request/status",
                body=json.dumps({"status": "identifying"}),
                headers=headers,
            )
            self.assertEqual(status, HTTPStatus.OK)
            self.assertEqual(payload["status"], "identifying")

            status, payload = self.request(
                "POST",
                "/api/requests/http-request/status",
                body=json.dumps({"status": "completed"}),
                headers=headers,
            )
            self.assertEqual(status, HTTPStatus.OK)
            self.assertEqual(payload["status"], "completed")

            status, payload = result.result(timeout=1)
            self.assertEqual(status, HTTPStatus.OK)
            self.assertEqual(payload["requestId"], "http-request")
            self.assertEqual(payload["status"], "completed")

        self.server.coordinator.disconnect_endpoint(endpoint_token)

    def test_serves_the_client_and_health(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1)
        self.addCleanup(connection.close)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read().decode()
        self.assertEqual(response.status, HTTPStatus.OK)
        self.assertIn('<div id="root"></div>', body)
        self.assertEqual(response.getheader("Cache-Control"), "no-store")
        self.assertIn(
            "media-src blob:",
            response.getheader("Content-Security-Policy"),
        )

        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1)
        self.addCleanup(connection.close)
        connection.request("GET", "/assets/app.js")
        response = connection.getresponse()
        self.assertEqual(response.status, HTTPStatus.OK)
        self.assertEqual(response.getheader("Content-Type"), "text/javascript")
        self.assertIn("immutable", response.getheader("Cache-Control"))
        self.assertEqual(response.read(), b"const ready = true;")

        status, payload = self.request("GET", "/api/health")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["status"], "ok")

    def test_rejects_malformed_json(self):
        status, payload = self.request(
            "POST",
            "/api/actions",
            body=b"{",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload["code"], "invalid_json")

    def test_rejects_an_oversized_body(self):
        status, payload = self.request(
            "POST",
            "/api/actions",
            body=b"x" * 4097,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(payload["code"], "invalid_body_size")

    def test_rejects_unknown_fields(self):
        status, payload = self.request(
            "POST",
            "/api/actions",
            body=json.dumps(
                {
                    "requestId": "request-1",
                    "action": ACTION,
                    "extra": True,
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload["code"], "unknown_fields")

    def test_rejects_an_action_when_the_endpoint_is_missing(self):
        status, payload = self.request(
            "POST",
            "/api/actions",
            body=json.dumps(
                {"requestId": "request-without-endpoint", "action": ACTION}
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(payload["code"], "endpoint_unavailable")

    def test_rejects_a_callback_without_an_endpoint_token(self):
        status, payload = self.request(
            "POST",
            "/api/requests/request-1/status",
            body=json.dumps({"status": "identifying"}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(payload["code"], "missing_endpoint_token")

    def test_accepts_and_publishes_a_playback_observation(self):
        events_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(events_connection.close)
        events_connection.request("GET", "/api/events")
        events_response = events_connection.getresponse()
        self.assertEqual(events_response.status, HTTPStatus.OK)
        self.read_event(events_response)
        self.read_event(events_response)

        status, snapshot = self.request(
            "POST",
            "/api/observations/music/playback",
            body=json.dumps(PLAYING_OBSERVATION),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(snapshot["status"], "playing")
        self.assertIn("observedAt", snapshot)
        event, published = self.read_event(events_response)
        self.assertEqual(event, "music.playback")
        self.assertEqual(published, snapshot)

    def test_closes_a_replaced_event_stream_for_reconnection(self):
        first_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(first_connection.close)
        first_connection.request("GET", "/api/events")
        first_response = first_connection.getresponse()
        self.assertEqual(first_response.status, HTTPStatus.OK)
        self.read_event(first_response)
        self.read_event(first_response)

        second_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(second_connection.close)
        second_connection.request("GET", "/api/events")
        second_response = second_connection.getresponse()
        self.assertEqual(second_response.status, HTTPStatus.OK)
        self.read_event(second_response)
        self.read_event(second_response)

        self.assertEqual(first_response.readline(), b"")

    def test_rejects_invalid_playback_over_http(self):
        status, payload = self.request(
            "POST",
            "/api/observations/music/playback",
            body=json.dumps(
                {"status": "playing", "item": None, "positionMs": 0}
            ),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload["code"], "invalid_playback")


if __name__ == "__main__":
    unittest.main()
