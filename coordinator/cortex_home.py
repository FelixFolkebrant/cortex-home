#!/usr/bin/env python3

import argparse
import json
import mimetypes
import queue
import re
import secrets
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from hue import (
    HueAdapter,
    HueSceneError,
    HueSceneTimeout,
    HueSceneUnavailable,
)


ACTION = "endpoint.identify"
SCENE_ACTION = "room.scene.activate"
ALLOWED_ACTIONS = {ACTION, SCENE_ACTION}
MAX_BODY_BYTES = 4096
MAX_COLLECTION_LENGTH = 512
MAX_CREATORS = 16
MAX_CREATOR_LENGTH = 256
MAX_DURATION_MS = 86_400_000
MAX_TITLE_LENGTH = 512
MAX_URI_LENGTH = 96
MAX_URL_LENGTH = 2048
MAX_REQUESTS = 128
PLAYBACK_ITEM_KEYS = {
    "artworkUrl",
    "collection",
    "creators",
    "durationMs",
    "title",
    "type",
    "uri",
}
PLAYBACK_KEYS = {"item", "positionMs", "status"}
PLAYBACK_STATUSES = {"paused", "playing", "stopped", "unavailable"}
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
CLIENT_ENTRY_PATTERN = re.compile(r'<script\b[^>]*\bsrc="(?P<src>/assets/[^"]+)"')
SPOTIFY_URI_PATTERN = re.compile(
    r"^spotify:(?P<type>track|episode):[A-Za-z0-9]{1,64}$"
)


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass
class PendingRequest:
    request_id: str
    action: str
    endpoint_token: str | None = None
    state: str = "accepted"
    error: str | None = None
    code: str | None = None
    http_status: int = HTTPStatus.OK
    finished: threading.Event = field(default_factory=threading.Event)

    def payload(self):
        payload = {
            "requestId": self.request_id,
            "action": self.action,
            "status": self.state,
        }
        if self.code:
            payload["code"] = self.code
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass
class EndpointConnection:
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    events: queue.Queue = field(default_factory=queue.Queue)

    def send(self, event, data):
        self.events.put((event, data))

    def close(self):
        self.events.put(None)


class Coordinator:
    def __init__(self, action_timeout=10, scene_activator=None):
        self.action_timeout = action_timeout
        self.scene_activator = scene_activator
        self.lock = threading.RLock()
        self.endpoint = None
        self.active_request_id = None
        self.requests = OrderedDict()
        self.playback = {
            "status": "unavailable",
            "item": None,
            "positionMs": 0,
            "observedAt": utc_timestamp(),
        }
        self.hue_status = "unconfigured"
        self.lighting = {
            "scene": "Warm",
            "status": "unavailable",
            "observedAt": utc_timestamp(),
        }

    def connect_endpoint(self):
        with self.lock:
            previous = self.endpoint
            if previous:
                self._fail_active_locked(
                    previous.token,
                    "endpoint connection was replaced",
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                previous.close()

            self.endpoint = EndpointConnection()
            self.endpoint.send("music.playback", self.playback)
            self.endpoint.send("room.lighting", self.lighting)
            return self.endpoint

    def disconnect_endpoint(self, token):
        with self.lock:
            if not self.endpoint or self.endpoint.token != token:
                return

            self.endpoint = None
            self._fail_active_locked(
                token,
                "endpoint disconnected",
                HTTPStatus.SERVICE_UNAVAILABLE,
            )

    def submit(self, request_id, action):
        self._validate_request_id(request_id)
        if action not in ALLOWED_ACTIONS:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "unknown_action",
                "The action is not allowed.",
            )

        with self.lock:
            if request_id in self.requests:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "duplicate_request_id",
                    "The request ID has already been used.",
                )
            if self.active_request_id:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "action_busy",
                    "The room is already handling an action.",
                )
            if action == ACTION and not self.endpoint:
                raise ApiError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "endpoint_unavailable",
                    "The room endpoint is not connected.",
                )

            endpoint_token = self.endpoint.token if action == ACTION else None
            pending = PendingRequest(request_id, action, endpoint_token)
            self.requests[request_id] = pending
            self.active_request_id = request_id
            self._trim_requests_locked()
            if action == ACTION:
                self.endpoint.send(
                    "identify",
                    {"requestId": request_id, "action": ACTION},
                )
            elif self.endpoint:
                self.endpoint.send("action.status", pending.payload())

        if action == SCENE_ACTION:
            return self._activate_scene(pending)

        if not pending.finished.wait(self.action_timeout):
            with self.lock:
                if not pending.finished.is_set():
                    self._finish_locked(
                        pending,
                        "failed",
                        "action timed out",
                        HTTPStatus.GATEWAY_TIMEOUT,
                        code="action_timeout",
                        notify_endpoint=True,
                    )

        return pending.http_status, pending.payload()

    def update(self, endpoint_token, request_id, status, error=None):
        if not endpoint_token:
            raise ApiError(
                HTTPStatus.UNAUTHORIZED,
                "missing_endpoint_token",
                "The endpoint token is required.",
            )

        with self.lock:
            if not self.endpoint or self.endpoint.token != endpoint_token:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "stale_endpoint",
                    "The endpoint connection is no longer active.",
                )

            pending = self.requests.get(request_id)
            if not pending or pending.endpoint_token != endpoint_token:
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    "unknown_request",
                    "No active request matches this endpoint and request ID.",
                )
            if pending.finished.is_set():
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "request_finished",
                    "The request already reached a terminal state.",
                )

            if status == "identifying" and pending.state == "accepted":
                pending.state = status
            elif status == "completed" and pending.state == "identifying":
                self._finish_locked(
                    pending,
                    status,
                    None,
                    HTTPStatus.OK,
                )
            elif status == "failed" and pending.state in {"accepted", "identifying"}:
                if not isinstance(error, str) or not error.strip():
                    raise ApiError(
                        HTTPStatus.BAD_REQUEST,
                        "missing_error",
                        "A failed endpoint status requires an error.",
                    )
                self._finish_locked(
                    pending,
                    status,
                    error.strip()[:160],
                    HTTPStatus.BAD_GATEWAY,
                )
            else:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "invalid_transition",
                    f"Cannot change {pending.state} to {status}.",
                )

            return pending.payload()

    def is_endpoint_connected(self):
        with self.lock:
            return self.endpoint is not None

    def set_hue_status(self, status):
        with self.lock:
            self.hue_status = status

    def set_scene_activator(self, activator):
        self.scene_activator = activator

    def report_lighting(self, status):
        if status not in {"active", "inactive", "unavailable"}:
            raise ValueError(f"Unknown room lighting status: {status}")

        with self.lock:
            if status == self.lighting["status"]:
                return self.lighting
            self.lighting = {
                "scene": "Warm",
                "status": status,
                "observedAt": utc_timestamp(),
            }
            if self.endpoint:
                self.endpoint.send("room.lighting", self.lighting)
            return self.lighting

    def health(self):
        with self.lock:
            return {
                "status": "ok",
                "endpoint": (
                    "connected" if self.endpoint is not None else "disconnected"
                ),
                "hue": self.hue_status,
            }

    def report_playback(self, observation):
        observation = validate_playback(observation)

        with self.lock:
            changed = any(
                self.playback[key] != observation[key] for key in PLAYBACK_KEYS
            )
            self.playback = {**observation, "observedAt": utc_timestamp()}
            if changed and self.endpoint:
                self.endpoint.send("music.playback", self.playback)
            return self.playback

    def _fail_active_locked(self, endpoint_token, error, http_status):
        if not self.active_request_id:
            return

        pending = self.requests[self.active_request_id]
        if pending.endpoint_token == endpoint_token and not pending.finished.is_set():
            self._finish_locked(pending, "failed", error, http_status)

    def _activate_scene(self, pending):
        try:
            if self.scene_activator is None:
                raise HueSceneUnavailable
            self.scene_activator(self.action_timeout)
        except HueSceneUnavailable:
            result = (
                "scene_unavailable",
                "The Warm scene is unavailable.",
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except HueSceneTimeout:
            result = (
                "scene_timeout",
                "The Warm scene did not report completion in time.",
                HTTPStatus.GATEWAY_TIMEOUT,
            )
        except HueSceneError:
            result = (
                "scene_failed",
                "The Hue bridge rejected the Warm scene action.",
                HTTPStatus.BAD_GATEWAY,
            )
        else:
            with self.lock:
                self._finish_locked(pending, "completed", None, HTTPStatus.OK)
            return pending.http_status, pending.payload()

        code, error, http_status = result
        with self.lock:
            self._finish_locked(
                pending,
                "failed",
                error,
                http_status,
                code=code,
            )
        return pending.http_status, pending.payload()

    def _finish_locked(
        self,
        pending,
        state,
        error,
        http_status,
        code=None,
        notify_endpoint=False,
    ):
        pending.state = state
        pending.error = error
        pending.code = code
        pending.http_status = http_status
        if self.active_request_id == pending.request_id:
            self.active_request_id = None
        pending.finished.set()

        if pending.action == SCENE_ACTION and self.endpoint:
            self.endpoint.send("action.status", pending.payload())
        elif (
            notify_endpoint
            and self.endpoint
            and self.endpoint.token == pending.endpoint_token
        ):
            self.endpoint.send("result", pending.payload())

    def _trim_requests_locked(self):
        while len(self.requests) > MAX_REQUESTS:
            oldest_id, oldest = next(iter(self.requests.items()))
            if not oldest.finished.is_set():
                break
            del self.requests[oldest_id]

    @staticmethod
    def _validate_request_id(request_id):
        if not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(
            request_id
        ):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_request_id",
                "requestId must be 1-64 URL-safe characters.",
            )


class CortexHomeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, coordinator, client_directory):
        self.coordinator = coordinator
        self.client_directory = Path(client_directory).resolve()
        self.client_entry = find_client_entry(self.client_directory)
        super().__init__(server_address, CortexHomeHandler)


class CortexHomeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._serve_static("index.html")
        elif path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                self.server.coordinator.health(),
            )
        elif path == "/api/events":
            self._serve_events()
        elif path.startswith("/assets/"):
            self._serve_static(path.removeprefix("/"))
        else:
            self._send_error(
                ApiError(HTTPStatus.NOT_FOUND, "not_found", "Route not found.")
            )

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/actions":
                body = self._read_json({"requestId", "action"})
                status, payload = self.server.coordinator.submit(
                    body.get("requestId"),
                    body.get("action"),
                )
                self._send_json(status, payload)
                return

            if path == "/api/observations/music/playback":
                body = self._read_json(PLAYBACK_KEYS)
                payload = self.server.coordinator.report_playback(body)
                self._send_json(HTTPStatus.OK, payload)
                return

            match = re.fullmatch(r"/api/requests/([^/]+)/status", path)
            if match:
                body = self._read_json({"status", "error"})
                request_id = match.group(1)
                if not REQUEST_ID_PATTERN.fullmatch(request_id):
                    raise ApiError(
                        HTTPStatus.BAD_REQUEST,
                        "invalid_request_id",
                        "The request path contains an invalid request ID.",
                    )
                payload = self.server.coordinator.update(
                    self.headers.get("X-Endpoint-Token"),
                    request_id,
                    body.get("status"),
                    body.get("error"),
                )
                self._send_json(HTTPStatus.OK, payload)
                return

            raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "Route not found.")
        except ApiError as error:
            self._send_error(error)

    def _serve_static(self, relative_path):
        file_path = (self.server.client_directory / relative_path).resolve()
        if (
            not file_path.is_relative_to(self.server.client_directory)
            or not file_path.is_file()
        ):
            self._send_error(
                ApiError(HTTPStatus.NOT_FOUND, "not_found", "Asset not found.")
            )
            return

        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_error(
                ApiError(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "client_unavailable",
                    "The endpoint client could not be loaded.",
                )
            )
            return

        content_type, _ = mimetypes.guess_type(file_path)
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            content_type or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if file_path.name == "index.html":
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "connect-src 'self'; "
                "img-src 'self' data: https:; "
                "media-src blob:; "
                "script-src 'self'; "
                "style-src 'self'",
            )
        else:
            self.send_header(
                "Cache-Control",
                "public, max-age=31536000, immutable",
            )
        self.end_headers()
        self.wfile.write(body)

    def _serve_events(self):
        endpoint = self.server.coordinator.connect_endpoint()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            ready = {"endpointToken": endpoint.token}
            if self.server.client_entry:
                ready["clientEntry"] = self.server.client_entry
            self._write_event("ready", ready)
            while True:
                try:
                    item = endpoint.events.get(timeout=2)
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    continue

                if item is None:
                    return

                event, data = item
                self._write_event(event, data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.close_connection = True
            self.server.coordinator.disconnect_endpoint(endpoint.token)

    def _write_event(self, event, data):
        encoded = json.dumps(data, separators=(",", ":"))
        self.wfile.write(f"event: {event}\ndata: {encoded}\n\n".encode())
        self.wfile.flush()

    def _read_json(self, allowed_keys):
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            raise ApiError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "invalid_content_type",
                "Content-Type must be application/json.",
            )

        content_length = self.headers.get("Content-Length")
        try:
            length = int(content_length)
        except (TypeError, ValueError):
            raise ApiError(
                HTTPStatus.LENGTH_REQUIRED,
                "missing_content_length",
                "A valid Content-Length is required.",
            )
        if length < 1 or length > MAX_BODY_BYTES:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "invalid_body_size",
                f"JSON bodies must be 1-{MAX_BODY_BYTES} bytes.",
            )

        try:
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_json",
                "The request body must contain valid UTF-8 JSON.",
            )

        if not isinstance(body, dict):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_json_shape",
                "The JSON body must be an object.",
            )

        unknown_keys = set(body) - allowed_keys
        if unknown_keys:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "unknown_fields",
                "The JSON body contains unknown fields.",
            )
        return body

    def _send_error(self, error):
        self._send_json(
            error.status,
            {"status": "error", "code": error.code, "error": error.message},
        )

    def _send_json(self, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def validate_playback(observation):
    if not isinstance(observation, dict) or set(observation) != PLAYBACK_KEYS:
        raise invalid_playback()

    status = observation["status"]
    item = observation["item"]
    position_ms = observation["positionMs"]

    if (
        not isinstance(status, str)
        or status not in PLAYBACK_STATUSES
        or not bounded_integer(position_ms, 0, MAX_DURATION_MS)
    ):
        raise invalid_playback()

    if status in {"stopped", "unavailable"}:
        if item is not None or position_ms != 0:
            raise invalid_playback()
        return {"status": status, "item": None, "positionMs": 0}

    if not isinstance(item, dict) or set(item) != PLAYBACK_ITEM_KEYS:
        raise invalid_playback()

    item_type = item["type"]
    uri = item["uri"]
    uri_match = (
        SPOTIFY_URI_PATTERN.fullmatch(uri)
        if bounded_string(uri, 1, MAX_URI_LENGTH)
        else None
    )
    creators = item["creators"]
    artwork_url = item["artworkUrl"]
    parsed_artwork_url = parse_artwork_url(artwork_url)

    if (
        not isinstance(item_type, str)
        or item_type not in {"episode", "track"}
        or not uri_match
        or uri_match.group("type") != item_type
        or not bounded_string(item["title"], 1, MAX_TITLE_LENGTH)
        or not isinstance(creators, list)
        or not 1 <= len(creators) <= MAX_CREATORS
        or not all(
            bounded_string(creator, 1, MAX_CREATOR_LENGTH)
            for creator in creators
        )
        or not bounded_string(item["collection"], 1, MAX_COLLECTION_LENGTH)
        or not parsed_artwork_url
        or parsed_artwork_url.scheme != "https"
        or not parsed_artwork_url.hostname
        or parsed_artwork_url.username is not None
        or parsed_artwork_url.password is not None
        or not bounded_integer(item["durationMs"], 1, MAX_DURATION_MS)
        or position_ms > item["durationMs"]
    ):
        raise invalid_playback()

    return {
        "status": status,
        "item": {
            "uri": uri,
            "type": item_type,
            "title": item["title"],
            "creators": list(creators),
            "collection": item["collection"],
            "artworkUrl": artwork_url,
            "durationMs": item["durationMs"],
        },
        "positionMs": position_ms,
    }


def bounded_integer(value, minimum, maximum):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def bounded_string(value, minimum, maximum):
    return (
        isinstance(value, str)
        and value.strip() == value
        and minimum <= len(value) <= maximum
    )


def parse_artwork_url(value):
    if not bounded_string(value, 1, MAX_URL_LENGTH):
        return None
    try:
        return urlparse(value)
    except ValueError:
        return None


def find_client_entry(client_directory):
    try:
        index = client_directory.joinpath("index.html").read_text()
    except (OSError, UnicodeError):
        return None

    match = CLIENT_ENTRY_PATTERN.search(index)
    return match.group("src") if match else None


def invalid_playback():
    return ApiError(
        HTTPStatus.BAD_REQUEST,
        "invalid_playback",
        "The playback observation does not match the accepted schema.",
    )


def utc_timestamp():
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--client",
        type=Path,
        default=Path(__file__).with_name("client"),
    )
    parser.add_argument("--action-timeout", type=float, default=10)
    parser.add_argument(
        "--hue-config",
        type=Path,
        default=Path("/etc/cortex-home/hue.json"),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    coordinator = Coordinator(action_timeout=args.action_timeout)
    hue = HueAdapter(
        args.hue_config,
        coordinator.set_hue_status,
        coordinator.report_lighting,
    )
    coordinator.set_scene_activator(hue.activate_scene)
    server = CortexHomeServer(
        (args.host, args.port),
        coordinator,
        args.client,
    )
    hue.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        hue.stop()


if __name__ == "__main__":
    main()
