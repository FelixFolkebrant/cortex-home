import io
import os
import subprocess
import threading
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from cortex_home import DISPLAY_MODE_ACTION, SCENE_ACTION, ApiError
from development import (
    DEVELOPMENT_LIGHTING,
    DEVELOPMENT_PLAYBACK,
    DEVELOPMENT_TODAY,
    DEVELOPMENT_VOSK_MODEL,
    ROOM_SCENARIO,
    UNAVAILABLE_SCENARIO,
    development_coordinator,
    development_server,
    development_voice_runtime,
)
from speech import WaveAudio, read_synthesis


def capture_audio():
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\0\0" * 1_600)
    return output.getvalue()


class DevelopmentTestDialogue:
    def answer(self, _request_id, _transcript, _context, _cancelled, on_delta):
        on_delta("A local test answer.")
        return "A local test answer."

    def close(self):
        pass


class DevelopmentTestAgent:
    def answer(self, _request_id, _transcript, _context, cancelled, **_session):
        if cancelled.is_set():
            raise RuntimeError("cancelled")
        return "A local test answer."

    def start_session(self, _session_id):
        return DevelopmentTestDialogue()


class DevelopmentTestRecognizer:
    def transcribe(self, _audio):
        return "Test the local room."


class DevelopmentTestSynthesizer:
    def synthesize(self, _text):
        return WaveAudio(capture_audio(), 16_000, 1_600)


class DevelopmentCoordinatorTests(unittest.TestCase):
    def coordinator(self, scenario=ROOM_SCENARIO):
        return development_coordinator(
            scenario,
            DevelopmentTestAgent(),
            DevelopmentTestRecognizer(),
            DevelopmentTestSynthesizer(),
        )

    def initial_snapshots(self, coordinator):
        endpoint = coordinator.connect_endpoint()
        snapshots = {}
        for _index in range(5):
            event, payload = endpoint.events.get(timeout=1)
            snapshots[event] = payload
        return endpoint, snapshots

    def test_room_scenario_uses_deterministic_available_state(self):
        coordinator = self.coordinator()
        try:
            endpoint, snapshots = self.initial_snapshots(coordinator)

            self.assertEqual(
                snapshots["today.summary"]["current"], DEVELOPMENT_TODAY["current"]
            )
            self.assertEqual(
                snapshots["music.playback"]["item"], DEVELOPMENT_PLAYBACK["item"]
            )
            self.assertEqual(
                snapshots["room.lighting"]["activeScenes"], ["Relax"]
            )
            self.assertEqual(
                snapshots["room.lighting"]["scenes"], DEVELOPMENT_LIGHTING["scenes"]
            )
            self.assertEqual(snapshots["alarm.state"]["status"], "disarmed")

            status, result = coordinator.submit(
                "camera-1", DISPLAY_MODE_ACTION, mode="camera"
            )
            self.assertEqual(status, 200)
            self.assertEqual(result["status"], "completed")

            status, result = coordinator.submit(
                "scene-1", SCENE_ACTION, scene="Warm low"
            )
            self.assertEqual(status, 200)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(coordinator.lighting["activeScenes"], ["Warm low"])

            answer = coordinator.interact(endpoint.token, "voice-1", capture_audio())
            self.assertEqual(read_synthesis(answer).duration_ms, 100)
        finally:
            coordinator.close()

    def test_room_scenario_accepts_a_session_turn(self):
        coordinator = self.coordinator()
        try:
            endpoint, _snapshots = self.initial_snapshots(coordinator)
            coordinator.start_voice_session(endpoint.token, "development-session")
            endpoint.events.get(timeout=1)

            interaction = coordinator.stream_interaction(
                endpoint.token,
                "development-turn-1",
                capture_audio(),
                "development-session",
                1,
            )
            self.assertEqual(interaction["requestId"], "development-turn-1")

            events = []
            while True:
                event, _payload = endpoint.events.get(timeout=1)
                events.append(event)
                if event == "agent.audio.complete":
                    break

            self.assertEqual(
                events,
                [
                    "voice.session",
                    "agent.interaction",
                    "agent.interaction",
                    "agent.audio",
                    "agent.audio.complete",
                ],
            )
            self.assertEqual(coordinator.active_voice_session.epoch, 1)
        finally:
            coordinator.close()

    def test_unavailable_scenario_has_no_scene_activator(self):
        coordinator = self.coordinator(UNAVAILABLE_SCENARIO)
        try:
            _endpoint, snapshots = self.initial_snapshots(coordinator)

            self.assertEqual(snapshots["today.summary"]["status"], "unavailable")
            self.assertEqual(snapshots["music.playback"]["status"], "unavailable")
            self.assertEqual(snapshots["room.lighting"]["status"], "unavailable")
            self.assertIsNone(coordinator.scene_activator)

            with self.assertRaises(ApiError) as raised:
                coordinator.submit("scene-1", SCENE_ACTION, scene="Warm low")
            self.assertEqual(raised.exception.code, "invalid_scene")
        finally:
            coordinator.close()

    def test_server_is_bound_to_loopback(self):
        server = development_server(
            0,
            ROOM_SCENARIO,
            Path(__file__).parents[1] / "client",
            DevelopmentTestAgent(),
            DevelopmentTestRecognizer(),
            DevelopmentTestSynthesizer(),
        )
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
        finally:
            server.server_close()
            server.coordinator.close()

    def test_production_installer_does_not_copy_development_runtime(self):
        coordinator_directory = Path(__file__).parents[1]
        role_directory = coordinator_directory.parent / "ops" / "roles" / "coordinator"
        role_source = "\n".join(
            path.read_text()
            for path in role_directory.rglob("*.yml")
        )

        self.assertNotIn("development.py", role_source)

    def test_launcher_starts_only_the_development_runtime(self):
        coordinator_directory = Path(__file__).parents[1]
        launcher = coordinator_directory.joinpath("develop")
        result = subprocess.run(["sh", "-n", launcher], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        source = launcher.read_text()
        self.assertIn('project_dir=$(dirname -- "$script_dir")', source)
        self.assertIn('python="$project_dir/.venv/bin/python"', source)
        self.assertIn('if [ ! -x "$python" ]; then', source)
        self.assertIn('ready_directory=$(mktemp -d)', source)
        self.assertIn('ready_file=$ready_directory/coordinator-ready', source)
        self.assertIn('"$python" "$script_dir/development.py" --ready-file "$ready_file" "$@" &', source)
        self.assertIn('if [ -f "$ready_file" ]; then', source)
        self.assertIn('trap cleanup EXIT', source)
        self.assertIn("trap 'exit 0' HUP INT TERM", source)
        self.assertIn(
            'pnpm --dir "$script_dir/client" exec vite --host 127.0.0.1 --strictPort &',
            source,
        )
        self.assertIn('while kill -0 "$client_pid" 2>/dev/null; do', source)
        self.assertIn('wait "$client_pid"', source)

    def test_development_voice_uses_the_real_agent_and_speech_runtimes(self):
        with (
            patch.dict(os.environ, {"OPENROUTER_API_KEY": "private-key"}, clear=True),
            patch("development.NodeAgent", return_value="agent") as node_agent,
            patch(
                "development.load_selected_speech",
                return_value=("recognizer", "synthesizer"),
            ) as selected_speech,
        ):
            runtime = development_voice_runtime()

        self.assertEqual(runtime, ("agent", "recognizer", "synthesizer"))
        node_agent.assert_called_once_with(
            "node",
            Path(__file__).parents[1] / "agent" / "answer-child.ts",
            "private-key",
        )
        selected_speech.assert_called_once_with(DEVELOPMENT_VOSK_MODEL)


if __name__ == "__main__":
    unittest.main()
