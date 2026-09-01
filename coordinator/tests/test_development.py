import io
import subprocess
import threading
import unittest
import wave
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from cortex_home import CHANNEL_ACTION, SCENE_ACTION, ApiError
from development import (
    DEVELOPMENT_ANSWER,
    DEVELOPMENT_LIGHTING,
    DEVELOPMENT_PLAYBACK,
    DEVELOPMENT_TODAY,
    ROOM_SCENARIO,
    UNAVAILABLE_SCENARIO,
    development_coordinator,
    development_server,
)
from speech import read_synthesis


def capture_audio():
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\0\0" * 1_600)
    return output.getvalue()


class DevelopmentCoordinatorTests(unittest.TestCase):
    def initial_snapshots(self, coordinator):
        endpoint = coordinator.connect_endpoint()
        snapshots = {}
        for _index in range(5):
            event, payload = endpoint.events.get(timeout=1)
            snapshots[event] = payload
        return endpoint, snapshots

    def test_room_scenario_uses_deterministic_available_state(self):
        coordinator = development_coordinator(ROOM_SCENARIO)
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
                "channel-1", CHANNEL_ACTION, channel="music"
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
            self.assertEqual(read_synthesis(answer).duration_ms, 200)
            self.assertEqual(
                coordinator.agent.answer("id", "text", {}, threading.Event()),
                DEVELOPMENT_ANSWER,
            )
        finally:
            coordinator.close()

    def test_unavailable_scenario_has_no_scene_activator(self):
        coordinator = development_coordinator(UNAVAILABLE_SCENARIO)
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
        )
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
        finally:
            server.server_close()
            server.coordinator.close()

    def test_production_installer_does_not_copy_development_runtime(self):
        coordinator_directory = Path(__file__).parents[1]
        self.assertNotIn("development.py", coordinator_directory.joinpath("install").read_text())
        self.assertNotIn("development.py", coordinator_directory.joinpath("install-host").read_text())

    def test_launcher_starts_only_the_development_runtime(self):
        coordinator_directory = Path(__file__).parents[1]
        launcher = coordinator_directory.joinpath("develop")
        result = subprocess.run(["sh", "-n", launcher], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        source = launcher.read_text()
        self.assertIn('python3 "$script_dir/development.py" "$@" &', source)
        self.assertIn('trap cleanup EXIT', source)
        self.assertIn("trap 'exit 0' HUP INT TERM", source)
        self.assertIn('pnpm --dir "$script_dir/client" dev &', source)
        self.assertIn('while kill -0 "$client_pid" 2>/dev/null; do', source)
        self.assertIn('wait "$client_pid"', source)


if __name__ == "__main__":
    unittest.main()
