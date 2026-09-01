#!/usr/bin/env python3

import argparse
import io
import math
import wave
from array import array
from pathlib import Path

from agent_runtime import AgentError
from cortex_home import CortexHomeServer, Coordinator
from speech import CAPTURE_SAMPLE_RATE, WaveAudio
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
DEVELOPMENT_ANSWER = "This is a simulated local answer."


class DevelopmentRecognizer:
    def transcribe(self, _audio):
        return "Test the local room."


class DevelopmentAgent:
    def answer(self, _request_id, _transcript, _context, cancelled):
        if cancelled.is_set():
            raise AgentError("cancelled")
        return DEVELOPMENT_ANSWER


class DevelopmentSynthesizer:
    def synthesize(self, _text):
        frames = round(CAPTURE_SAMPLE_RATE * 0.2)
        samples = array(
            "h",
            (
                round(2_400 * math.sin(2 * math.pi * 440 * frame / CAPTURE_SAMPLE_RATE))
                for frame in range(frames)
            ),
        )
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(CAPTURE_SAMPLE_RATE)
            wav.writeframes(samples.tobytes())
        return WaveAudio(output.getvalue(), CAPTURE_SAMPLE_RATE, frames)


class DevelopmentScenes:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __call__(self, scene, _timeout):
        self.coordinator.report_lighting(
            {**DEVELOPMENT_LIGHTING, "activeScenes": [scene]}
        )


def development_coordinator(scenario=ROOM_SCENARIO):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown development scenario.")

    coordinator = Coordinator(
        action_timeout=1,
        agent=DevelopmentAgent(),
        recognizer=DevelopmentRecognizer(),
        synthesizer=DevelopmentSynthesizer(),
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


def development_server(port, scenario, client_directory):
    return CortexHomeServer(
        ("127.0.0.1", port),
        development_coordinator(scenario),
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
    return parser.parse_args()


def main():
    args = parse_args()
    server = development_server(args.port, args.scenario, args.client)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.coordinator.close()


if __name__ == "__main__":
    main()
