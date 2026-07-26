import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1]))

from verify_scene import VerificationError, verify


class FakeCoordinator:
    def __init__(self):
        self.health = {
            "status": "ok",
            "endpoint": "connected",
            "hue": "connected",
        }
        self.action_status = 200
        self.action_result = None
        self.requests = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/health":
            self.send_error(404)
            return
        self.send_json(200, self.server.state.health)

    def do_POST(self):
        if self.path != "/api/actions":
            self.send_error(404)
            return
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        self.server.state.requests.append(request)
        result = self.server.state.action_result or {
            **request,
            "status": "completed",
        }
        self.send_json(self.server.state.action_status, result)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        pass


class VerifySceneTests(unittest.TestCase):
    def setUp(self):
        self.state = FakeCoordinator()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.state = self.state
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def test_verifies_health_and_observed_scene_completion(self):
        output = []

        verify(
            self.base_url,
            "Relax",
            request_id="scene-test-1",
            output=output.append,
        )

        self.assertEqual(
            self.state.requests,
            [
                {
                    "requestId": "scene-test-1",
                    "action": "room.scene.activate",
                    "scene": "Relax",
                }
            ],
        )
        self.assertIn("endpoint connected", output[0])
        self.assertEqual(
            output[-1],
            "PASS: Hue reported Relax active after the scene request.",
        )

    def test_accepts_a_disconnected_endpoint(self):
        self.state.health["endpoint"] = "disconnected"

        verify(
            self.base_url,
            "Bright",
            request_id="scene-test-2",
            output=lambda _line: None,
        )

        self.assertEqual(len(self.state.requests), 1)

    def test_stops_before_the_action_when_hue_is_unavailable(self):
        self.state.health["hue"] = "unreachable"

        with self.assertRaisesRegex(VerificationError, "health is not connected"):
            verify(self.base_url, "Relax", request_id="scene-test-3")

        self.assertEqual(self.state.requests, [])

    def test_reports_the_safe_action_failure(self):
        self.state.action_status = 504
        self.state.action_result = {
            "status": "failed",
            "code": "scene_timeout",
            "error": "The Relax scene did not report completion in time.",
        }

        with self.assertRaisesRegex(
            VerificationError,
            "HTTP 504: scene_timeout",
        ):
            verify(
                self.base_url,
                "Relax",
                request_id="scene-test-4",
                output=lambda _line: None,
            )


if __name__ == "__main__":
    unittest.main()
