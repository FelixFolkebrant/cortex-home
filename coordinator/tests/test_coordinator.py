import http.client
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from cortex_home import ACTION, ApiError, Coordinator, CortexHomeServer


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = Coordinator(action_timeout=0.1)
        self.endpoint = self.coordinator.connect_endpoint()

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


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client_file = Path(__file__).parents[1] / "client" / "index.html"
        cls.server = CortexHomeServer(
            ("127.0.0.1", 0),
            Coordinator(action_timeout=0.05),
            client_file,
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)

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
        self.assertIn("Room endpoint ready.", body)
        self.assertEqual(response.getheader("Cache-Control"), "no-store")

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


if __name__ == "__main__":
    unittest.main()
