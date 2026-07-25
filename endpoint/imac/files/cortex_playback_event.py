#!/usr/bin/env python3

import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


COORDINATOR_URL_FILE = Path("/etc/cortex-endpoint/coordinator-url")
MAX_DURATION_MS = 86_400_000
REPORT_PATH = "/api/observations/music/playback"
STATE_FILE_NAME = "cortex-playback.json"
ITEM_KEYS = {
    "artworkUrl",
    "collection",
    "creators",
    "durationMs",
    "title",
    "type",
    "uri",
}
SNAPSHOT_KEYS = {"item", "positionMs", "status"}


def unavailable():
    return {"status": "unavailable", "item": None, "positionMs": 0}


def loaded_item(environment):
    item_type = environment.get("ITEM_TYPE")
    if item_type == "Track":
        normalized_type = "track"
        creators = split_values(environment.get("ARTISTS"))
        collection = environment.get("ALBUM")
    elif item_type == "Episode":
        normalized_type = "episode"
        creators = split_values(environment.get("SHOW_NAME"))
        collection = environment.get("SHOW_NAME")
    else:
        raise ValueError("unsupported item type")

    uri = environment.get("URI")
    expected_prefix = f"spotify:{normalized_type}:"
    covers = split_values(environment.get("COVERS"))
    duration_ms = parse_position(environment.get("DURATION_MS"))

    if (
        not isinstance(uri, str)
        or not uri.startswith(expected_prefix)
        or not environment.get("NAME")
        or not creators
        or not collection
        or not covers
        or duration_ms < 1
        or duration_ms > MAX_DURATION_MS
    ):
        raise ValueError("incomplete item metadata")

    return {
        "uri": uri,
        "type": normalized_type,
        "title": environment["NAME"],
        "creators": creators,
        "collection": collection,
        "artworkUrl": covers[0],
        "durationMs": duration_ms,
    }


def normalize_event(environment, previous):
    event = environment.get("PLAYER_EVENT")

    if event == "track_changed":
        try:
            item = loaded_item(environment)
        except ValueError:
            return unavailable()
        return {"status": "paused", "item": item, "positionMs": 0}

    if event in {"end_of_track", "stopped"}:
        return {"status": "stopped", "item": None, "positionMs": 0}

    if event in {"session_disconnected", "unavailable"}:
        return unavailable()

    if event == "loading":
        if current_item_matches(previous, environment.get("TRACK_ID")):
            return {
                "status": "paused",
                "item": previous["item"],
                "positionMs": previous["positionMs"],
            }
        return unavailable()

    if event not in {"paused", "playing", "position_correction", "seeked"}:
        return None

    if not current_item_matches(previous, environment.get("TRACK_ID")):
        return unavailable()

    try:
        position_ms = parse_position(environment.get("POSITION_MS"))
    except ValueError:
        return unavailable()

    item = previous["item"]
    if position_ms > item["durationMs"]:
        return unavailable()

    status = previous["status"]
    if event == "paused":
        status = "paused"
    elif event == "playing":
        status = "playing"
    elif status not in {"paused", "playing"}:
        return unavailable()

    return {"status": status, "item": item, "positionMs": position_ms}


def current_item_matches(snapshot, track_id):
    item = snapshot.get("item") if isinstance(snapshot, dict) else None
    uri = item.get("uri") if isinstance(item, dict) else None
    return isinstance(track_id, str) and isinstance(uri, str) and uri.endswith(
        f":{track_id}"
    )


def split_values(value):
    if not isinstance(value, str):
        return []
    return [part for part in value.splitlines() if part]


def parse_position(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError("invalid position")
    return int(value)


def load_state(path):
    try:
        snapshot = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return unavailable()
    if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_KEYS:
        return unavailable()

    status = snapshot["status"]
    if isinstance(status, str) and status in {"stopped", "unavailable"}:
        if snapshot["item"] is None and snapshot["positionMs"] == 0:
            return snapshot
        return unavailable()

    item = snapshot["item"]
    if (
        not isinstance(status, str)
        or status not in {"paused", "playing"}
        or not isinstance(snapshot["positionMs"], int)
        or isinstance(snapshot["positionMs"], bool)
        or snapshot["positionMs"] < 0
        or not isinstance(item, dict)
        or set(item) != ITEM_KEYS
        or not isinstance(item["durationMs"], int)
        or isinstance(item["durationMs"], bool)
        or not 1 <= item["durationMs"] <= MAX_DURATION_MS
        or snapshot["positionMs"] > item["durationMs"]
    ):
        return unavailable()
    return snapshot


def save_state(path, snapshot):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(snapshot, temporary, separators=(",", ":"))
            temporary.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)


def report(snapshot, coordinator_url_file=COORDINATOR_URL_FILE, opener=urlopen):
    lines = coordinator_url_file.read_text().splitlines()
    if not lines:
        raise ValueError("missing coordinator URL")
    coordinator_url = lines[0].rstrip("/")
    if not coordinator_url.startswith("http://"):
        raise ValueError("invalid coordinator URL")

    body = json.dumps(snapshot, separators=(",", ":")).encode()
    request = Request(
        f"{coordinator_url}{REPORT_PATH}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener(request, timeout=2) as response:
        if response.status != 200:
            raise RuntimeError("playback report was rejected")


def process_event(environment, state_path, sender=report):
    previous = load_state(state_path)
    snapshot = normalize_event(environment, previous)
    if snapshot is None:
        return False

    save_state(state_path, snapshot)
    sender(snapshot)
    return True


def main():
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] != "unavailable"):
        print("Usage: cortex-playback-event [unavailable]", file=sys.stderr)
        return 2

    state_path = Path(os.environ.get("TMPDIR", "/run/raspotify")) / STATE_FILE_NAME
    environment = (
        {"PLAYER_EVENT": "unavailable"} if len(sys.argv) == 2 else os.environ
    )

    try:
        process_event(environment, state_path)
    except (OSError, RuntimeError, ValueError):
        print("Playback reporting failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
