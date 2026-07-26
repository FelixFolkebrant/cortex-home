#!/usr/bin/env python3

import argparse
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]+$")
MAX_RESPONSE_BYTES = 65_536
SCENE_ACTION = "room.scene.activate"


class VerificationError(Exception):
    pass


def request_json(url, payload=None, timeout=5):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=body,
        headers=headers,
        method="POST" if body else "GET",
    )
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as error:
        raise VerificationError(format_http_error(error)) from error
    except URLError as error:
        raise VerificationError("The coordinator could not be reached.") from error

    with response:
        encoded = response.read(MAX_RESPONSE_BYTES + 1)
        if len(encoded) > MAX_RESPONSE_BYTES:
            raise VerificationError("The coordinator response was too large.")
        try:
            return response.status, json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VerificationError("The coordinator returned invalid JSON.") from error


def format_http_error(error):
    with error:
        try:
            payload = json.loads(error.read(MAX_RESPONSE_BYTES + 1))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}

    code = payload.get("code") if isinstance(payload, dict) else None
    message = payload.get("error") if isinstance(payload, dict) else None
    detail = ": ".join(value for value in (code, message) if isinstance(value, str))
    return f"HTTP {error.code}" + (f": {detail}" if detail else "")


def verify(base_url, request_id=None, output=print):
    status, health = request_json(f"{base_url}/api/health")
    if (
        status != 200
        or not isinstance(health, dict)
        or health.get("status") != "ok"
        or health.get("hue") != "connected"
    ):
        raise VerificationError("Coordinator or Hue health is not connected.")

    output(
        "Health passed: coordinator ok, "
        f"Hue connected, endpoint {health.get('endpoint', 'unknown')}."
    )
    output("Activating Warm in Rum. Watch the lamps and room display now.")

    request_id = request_id or f"warm-verify-{time.time_ns():x}"
    status, result = request_json(
        f"{base_url}/api/actions",
        {
            "requestId": request_id,
            "action": SCENE_ACTION,
        },
        timeout=15,
    )
    expected = {
        "requestId": request_id,
        "action": SCENE_ACTION,
        "status": "completed",
    }
    if status != 200 or result != expected:
        raise VerificationError("The scene action returned an unexpected result.")

    output("PASS: Hue reported Warm active after the scene request.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Verify the deployed Cortex Home Warm scene action."
    )
    parser.add_argument("server_host", help="Local coordinator hostname or IPv4 address")
    return parser.parse_args()


def main():
    args = parse_args()
    if not HOST_PATTERN.fullmatch(args.server_host):
        raise SystemExit("The server host must be an IPv4 address or local hostname.")

    try:
        verify(f"http://{args.server_host}:8080")
    except VerificationError as error:
        raise SystemExit(f"FAIL: {error}") from error


if __name__ == "__main__":
    main()
