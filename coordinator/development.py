#!/usr/bin/env python3

import argparse
import os
from pathlib import Path

from agent_runtime import AgentError, NodeAgent
from cortex_home import CortexHomeServer, Coordinator
from speech import SpeechError, load_selected_speech
from today import TIME_ZONE, unavailable_summary


ROOM_SCENARIO = "room"
UNAVAILABLE_SCENARIO = "unavailable"
SCENARIOS = {ROOM_SCENARIO, UNAVAILABLE_SCENARIO}

DEVELOPMENT_TODAY = {
    "status": "available",
    "timeZone": TIME_ZONE,
    "current": {"condition": "partly_cloudy", "temperatureC": 18},
    "forecast": [
        {"date": "2026-09-01", "condition": "partly_cloudy", "highC": 19, "lowC": 11},
        {"date": "2026-09-02", "condition": "clear", "highC": 21, "lowC": 12},
        {"date": "2026-09-03", "condition": "rain", "highC": 17, "lowC": 10},
    ],
}
DEVELOPMENT_PLAYBACK = {
    "status": "playing",
    "item": {
        "uri": "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
        "type": "track",
        "title": "Development track",
        "creators": ["Cortex Home"],
        "collection": "Local room",
        "artworkUrl": "https://127.0.0.1/development-artwork.jpg",
        "durationMs": 214_000,
    },
    "positionMs": 48_000,
}
DEVELOPMENT_LIGHTING = {
    "status": "available",
    "scenes": ["Bright", "Relax", "Warm low"],
    "activeScenes": ["Relax"],
}
DEVELOPMENT_VOSK_MODEL = (
    Path.home() / ".local" / "share" / "cortex-home" / "vosk-model-small-en-us-0.15"
)


def development_voice_runtime():
    agent = NodeAgent(
        "node",
        Path(__file__).parent / "agent" / "answer-child.ts",
        os.environ.get("OPENROUTER_API_KEY"),
    )
    recognizer, synthesizer = load_selected_speech(DEVELOPMENT_VOSK_MODEL)
    return agent, recognizer, synthesizer


class DevelopmentScenes:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __call__(self, scene, _timeout):
        self.coordinator.report_lighting(
            {**DEVELOPMENT_LIGHTING, "activeScenes": [scene]}
        )


def development_coordinator(
    scenario=ROOM_SCENARIO,
    agent=None,
    recognizer=None,
    synthesizer=None,
):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown development scenario.")
    if agent is None or recognizer is None or synthesizer is None:
        agent, recognizer, synthesizer = development_voice_runtime()

    coordinator = Coordinator(
        action_timeout=1,
        agent=agent,
        recognizer=recognizer,
        synthesizer=synthesizer,
        alarm_state_path=None,
    )
    if scenario == ROOM_SCENARIO:
        coordinator.report_today(DEVELOPMENT_TODAY)
        coordinator.report_playback(DEVELOPMENT_PLAYBACK)
        coordinator.report_lighting(DEVELOPMENT_LIGHTING)
        coordinator.set_scene_activator(DevelopmentScenes(coordinator))
    else:
        coordinator.report_today(unavailable_summary())
        coordinator.report_playback(
            {"status": "unavailable", "item": None, "positionMs": 0}
        )
        coordinator.report_lighting(
            {"status": "unavailable", "scenes": [], "activeScenes": []}
        )
    return coordinator


def development_server(
    port,
    scenario,
    client_directory,
    agent=None,
    recognizer=None,
    synthesizer=None,
):
    return CortexHomeServer(
        ("127.0.0.1", port),
        development_coordinator(scenario, agent, recognizer, synthesizer),
        client_directory,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the loopback-only Cortex Home development coordinator."
    )
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default=ROOM_SCENARIO)
    parser.add_argument(
        "--client",
        type=Path,
        default=Path(__file__).with_name("client"),
    )
    parser.add_argument("--ready-file", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        server = development_server(args.port, args.scenario, args.client)
    except AgentError as error:
        print(f"error: {error.code}", flush=True)
        return 1
    except SpeechError:
        print("error: speech_unavailable", flush=True)
        return 1
    if args.ready_file:
        args.ready_file.touch(exist_ok=False)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.coordinator.close()


if __name__ == "__main__":
    raise SystemExit(main())
