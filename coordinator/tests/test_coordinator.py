import http.client
import io
import json
import queue
import threading
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from cortex_home import (
    ACTION,
    CHANNEL_ACTION,
    CHANNELS,
    SCENE_ACTION,
    ApiError,
    Coordinator,
    CortexHomeServer,
)
from agent_runtime import AgentError
from hue import HueSceneError, HueSceneTimeout, HueSceneUnavailable
from speech import WaveAudio


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
AVAILABLE_LIGHTING = {
    "status": "available",
    "scenes": ["Bright", "Relax", "Warm"],
    "activeScenes": ["Warm"],
}


def wave_audio(samples=b"\0\0" * 160):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(samples)
    data = output.getvalue()
    return WaveAudio(data, 16_000, len(samples) // 2)


class FakeRecognizer:
    def __init__(self, transcript="What is on screen?"):
        self.transcript = transcript
        self.audio = None

    def transcribe(self, audio):
        self.audio = audio
        return self.transcript


class FakeSynthesizer:
    def __init__(self):
        self.text = None

    def synthesize(self, text):
        self.text = text
        return wave_audio()


class FakeAgent:
    def __init__(self, answer="It is clear and 21 degrees."):
        self.answer_text = answer
        self.request = None

    def answer(self, request_id, transcript, context, cancelled):
        self.request = (request_id, transcript, context)
        if cancelled.is_set():
            raise AgentError("cancelled")
        return self.answer_text


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = Coordinator(action_timeout=0.1)
        self.endpoint = self.coordinator.connect_endpoint()
        snapshots = self.initial_snapshots(self.endpoint)
        lighting = snapshots["room.lighting"]
        self.assertEqual(lighting["status"], "unavailable")

    def initial_snapshots(self, endpoint):
        snapshots = {}
        for _index in range(4):
            event, payload = endpoint.events.get(timeout=1)
            snapshots[event] = payload
        self.assertEqual(
            set(snapshots),
            {"music.playback", "channel.active", "today.summary", "room.lighting"},
        )
        return snapshots

    def submit_in_background(self, request_id="request-1"):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.coordinator.submit, request_id, ACTION)
        self.addCleanup(executor.shutdown)
        return future

    def submit_scene_in_background(
        self,
        request_id="scene-request-1",
        scene="Relax",
    ):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.coordinator.submit,
            request_id,
            SCENE_ACTION,
            None,
            scene,
        )
        self.addCleanup(executor.shutdown)
        return future

    def make_scenes_available(self, active_scenes=None):
        self.coordinator.report_lighting(
            {
                **AVAILABLE_LIGHTING,
                "activeScenes": active_scenes or [],
            }
        )
        self.endpoint.events.get(timeout=1)

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
        self.assertEqual(raised.exception.code, "action_busy")
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

        snapshot = self.initial_snapshots(endpoint)["music.playback"]

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
        snapshot = self.initial_snapshots(endpoint)["music.playback"]
        self.assertEqual(snapshot["status"], "playing")
        self.assertEqual(snapshot["item"]["title"], "Never Gonna Give You Up")

    def test_sends_and_publishes_only_changed_lighting_snapshots(self):
        snapshot = self.coordinator.report_lighting(AVAILABLE_LIGHTING)

        self.assertEqual(
            set(snapshot),
            {"status", "scenes", "activeScenes", "observedAt"},
        )
        self.assertEqual(snapshot["status"], "available")
        self.assertEqual(snapshot["scenes"], ["Bright", "Relax", "Warm"])
        self.assertEqual(snapshot["activeScenes"], ["Warm"])
        self.assertRegex(
            snapshot["observedAt"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$",
        )
        event, published = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "room.lighting")
        self.assertEqual(published, snapshot)

        self.assertEqual(
            self.coordinator.report_lighting(AVAILABLE_LIGHTING),
            snapshot,
        )
        with self.assertRaises(queue.Empty):
            self.endpoint.events.get_nowait()

        custom = self.coordinator.report_lighting(
            {**AVAILABLE_LIGHTING, "activeScenes": []}
        )
        event, published = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "room.lighting")
        self.assertEqual(published, custom)

        invalid_snapshots = [
            {},
            {"status": "unknown", "scenes": [], "activeScenes": []},
            {"status": "available", "scenes": [], "activeScenes": []},
            {
                "status": "available",
                "scenes": ["Warm", "warm"],
                "activeScenes": [],
            },
            {
                "status": "available",
                "scenes": ["Warm", "Bright"],
                "activeScenes": [],
            },
            {"status": "available", "scenes": ["Warm"], "activeScenes": ["Missing"]},
            {
                "status": "available",
                "scenes": ["Bright", "Warm"],
                "activeScenes": ["Warm", "Bright"],
            },
            {"status": "unavailable", "scenes": ["Warm"], "activeScenes": []},
        ]
        for lighting in invalid_snapshots:
            with self.subTest(lighting=lighting):
                with self.assertRaises(ValueError):
                    self.coordinator.report_lighting(lighting)

    def test_activates_a_scene_and_publishes_observed_completion(self):
        self.make_scenes_available()

        def activate(scene, _timeout):
            self.assertEqual(scene, "Relax")
            self.coordinator.report_lighting(
                {**AVAILABLE_LIGHTING, "activeScenes": [scene]}
            )

        self.coordinator.set_scene_activator(activate)
        future = self.submit_scene_in_background()

        event, accepted = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "action.status")
        self.assertEqual(accepted["action"], SCENE_ACTION)
        self.assertEqual(accepted["scene"], "Relax")
        self.assertEqual(accepted["status"], "accepted")
        event, lighting = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "room.lighting")
        self.assertEqual(lighting["activeScenes"], ["Relax"])
        event, completed = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "action.status")
        self.assertEqual(completed["status"], "completed")

        status, payload = future.result(timeout=1)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload, completed)

    def test_scene_action_does_not_require_the_endpoint(self):
        self.make_scenes_available()
        self.coordinator.disconnect_endpoint(self.endpoint.token)
        calls = []
        self.coordinator.set_scene_activator(
            lambda scene, timeout: calls.append((scene, timeout))
        )

        status, payload = self.coordinator.submit(
            "scene-without-endpoint",
            SCENE_ACTION,
            scene="Bright",
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(
            calls,
            [("Bright", self.coordinator.action_timeout)],
        )

    def test_rejects_missing_unknown_and_misplaced_scene_arguments(self):
        self.make_scenes_available()
        cases = [
            (
                ("missing-scene", SCENE_ACTION),
                "invalid_scene",
            ),
            (
                ("unknown-scene", SCENE_ACTION, None, "Missing"),
                "invalid_scene",
            ),
            (
                ("scene-on-channel", CHANNEL_ACTION, "today", "Warm"),
                "invalid_action_arguments",
            ),
        ]

        for arguments, expected_code in cases:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ApiError) as raised:
                    self.coordinator.submit(*arguments)
                self.assertEqual(raised.exception.code, expected_code)

    def test_selects_a_channel_after_publishing_matching_state(self):
        status, payload = self.coordinator.submit(
            "today-to-camera",
            CHANNEL_ACTION,
            "camera",
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(
            payload,
            {
                "requestId": "today-to-camera",
                "action": CHANNEL_ACTION,
                "status": "completed",
            },
        )
        event, accepted = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "action.status")
        self.assertEqual(accepted["status"], "accepted")
        event, channel = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "channel.active")
        self.assertEqual(channel, {"active": "camera"})
        event, completed = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "action.status")
        self.assertEqual(completed, payload)

    def test_context_tracks_active_channel_and_isolates_nested_values(self):
        self.coordinator.report_playback(PLAYING_OBSERVATION)
        self.endpoint.events.get(timeout=1)
        self.coordinator.report_lighting(AVAILABLE_LIGHTING)
        self.endpoint.events.get(timeout=1)

        self.coordinator.submit("today-to-music", CHANNEL_ACTION, "music")
        for _index in range(3):
            self.endpoint.events.get(timeout=1)

        context = self.coordinator.context()
        self.assertEqual(context["activeChannel"], "music")
        self.assertEqual(context["channel"]["type"], "music")
        self.assertEqual(context["channel"]["title"], "Never Gonna Give You Up")
        self.assertNotIn("artworkUrl", context["channel"])

        context["channel"]["creators"].append("Mutated")
        context["lighting"]["scenes"].append("Mutated")
        self.assertEqual(
            self.coordinator.playback["item"]["creators"],
            ["Rick Astley"],
        )
        self.assertEqual(
            self.coordinator.lighting["scenes"],
            ["Bright", "Relax", "Warm"],
        )

    def test_selects_a_channel_without_an_endpoint_and_rejects_invalid_values(self):
        self.coordinator.disconnect_endpoint(self.endpoint.token)
        self.assertEqual(CHANNELS, {"today", "music", "camera"})

        status, payload = self.coordinator.submit(
            "select-without-endpoint",
            CHANNEL_ACTION,
            "camera",
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(self.coordinator.channel, {"active": "camera"})
        for channel in (None, "news", True):
            with self.subTest(channel=channel):
                with self.assertRaises(ApiError) as raised:
                    self.coordinator.submit("invalid-channel", CHANNEL_ACTION, channel)
                self.assertEqual(raised.exception.code, "invalid_channel")
                self.assertEqual(self.coordinator.channel, {"active": "camera"})

    def test_endpoint_disconnect_does_not_fail_a_scene_action(self):
        self.make_scenes_available()
        started = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)

        def activate(_scene, _timeout):
            started.set()
            release.wait(1)

        self.coordinator.set_scene_activator(activate)
        future = self.submit_scene_in_background()
        event, accepted = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "action.status")
        self.assertEqual(accepted["status"], "accepted")
        self.assertTrue(started.wait(1))

        self.coordinator.disconnect_endpoint(self.endpoint.token)
        release.set()

        status, payload = future.result(timeout=1)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["status"], "completed")

    def test_scene_action_returns_distinct_adapter_failures(self):
        self.make_scenes_available()
        cases = [
            (
                HueSceneUnavailable,
                HTTPStatus.SERVICE_UNAVAILABLE,
                "scene_unavailable",
            ),
            (HueSceneTimeout, HTTPStatus.GATEWAY_TIMEOUT, "scene_timeout"),
            (HueSceneError, HTTPStatus.BAD_GATEWAY, "scene_failed"),
        ]

        for index, (error, expected_status, expected_code) in enumerate(cases):
            with self.subTest(code=expected_code):
                def fail(_scene, _timeout, error=error):
                    raise error

                self.coordinator.set_scene_activator(fail)
                status, payload = self.coordinator.submit(
                    f"failed-scene-{index}",
                    SCENE_ACTION,
                    scene="Relax",
                )
                self.assertEqual(status, expected_status)
                self.assertEqual(payload["status"], "failed")
                self.assertEqual(payload["code"], expected_code)

                event, accepted = self.endpoint.events.get(timeout=1)
                self.assertEqual(event, "action.status")
                self.assertEqual(accepted["status"], "accepted")
                event, failed = self.endpoint.events.get(timeout=1)
                self.assertEqual(event, "action.status")
                self.assertEqual(failed["code"], expected_code)

    def test_serializes_endpoint_and_scene_actions(self):
        self.make_scenes_available()
        started = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)

        def activate(_scene, _timeout):
            started.set()
            release.wait(1)

        self.coordinator.set_scene_activator(activate)
        future = self.submit_scene_in_background()
        self.endpoint.events.get(timeout=1)
        self.assertTrue(started.wait(1))

        with self.assertRaises(ApiError) as raised:
            self.coordinator.submit("overlapping-identify", ACTION)
        self.assertEqual(raised.exception.code, "action_busy")

        release.set()
        future.result(timeout=1)

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


class AgentInteractionTests(unittest.TestCase):
    def setUp(self):
        self.recognizer = FakeRecognizer()
        self.synthesizer = FakeSynthesizer()
        self.agent = FakeAgent()
        self.coordinator = Coordinator(
            action_timeout=0.1,
            agent=self.agent,
            playback_timeout=0.05,
            recognizer=self.recognizer,
            synthesizer=self.synthesizer,
        )
        self.endpoint = self.coordinator.connect_endpoint()
        for _index in range(4):
            self.endpoint.events.get(timeout=1)
        self.addCleanup(self.coordinator.close)

    def next_phase(self, phase):
        event, payload = self.endpoint.events.get(timeout=1)
        self.assertEqual(event, "agent.interaction")
        self.assertEqual(payload["phase"], phase)
        return payload

    def test_runs_one_ephemeral_contextual_answer_and_playback_lifecycle(self):
        audio = self.coordinator.interact(
            self.endpoint.token,
            "voice-1",
            wave_audio().data,
        )

        self.assertEqual(audio, wave_audio().data)
        self.assertIsNotNone(self.recognizer.audio)
        self.assertEqual(self.synthesizer.text, self.agent.answer_text)
        request_id, transcript, context = self.agent.request
        self.assertEqual(request_id, "voice-1")
        self.assertEqual(transcript, self.recognizer.transcript)
        self.assertEqual(context["activeChannel"], "today")
        self.next_phase("transcribing")
        self.next_phase("thinking")

        speaking = self.coordinator.update_interaction(
            self.endpoint.token,
            "voice-1",
            "speaking",
        )
        self.assertEqual(speaking["phase"], "speaking")
        self.next_phase("speaking")
        completed = self.coordinator.update_interaction(
            self.endpoint.token,
            "voice-1",
            "completed",
        )
        self.assertEqual(completed["phase"], "completed")
        self.next_phase("completed")
        self.assertIsNone(self.coordinator.active_interaction)

    def test_rejects_invalid_audio_with_content_free_failed_phase(self):
        with self.assertRaises(ApiError) as raised:
            self.coordinator.interact(
                self.endpoint.token,
                "voice-invalid",
                b"not audio",
            )

        self.assertEqual(raised.exception.code, "invalid_audio")
        self.next_phase("transcribing")
        failure = self.next_phase("failed")
        self.assertEqual(set(failure), {"phase", "requestId"})
        self.assertIsNone(self.agent.request)

    def test_requires_the_current_endpoint_token(self):
        for token, code in [(None, "missing_endpoint_token"), ("stale", "stale_endpoint")]:
            with self.subTest(code=code):
                with self.assertRaises(ApiError) as raised:
                    self.coordinator.interact(
                        token,
                        f"voice-{code}",
                        wave_audio().data,
                    )
                self.assertEqual(raised.exception.code, code)

    def test_cancellation_aborts_the_child_and_discards_late_results(self):
        started = threading.Event()

        class BlockingAgent:
            def answer(_self, _request_id, _transcript, _context, cancelled):
                started.set()
                cancelled.wait(1)
                raise AgentError("cancelled")

        self.coordinator.agent = BlockingAgent()
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(
                self.coordinator.interact,
                self.endpoint.token,
                "voice-cancel",
                wave_audio().data,
            )
            self.assertTrue(started.wait(1))
            self.next_phase("transcribing")
            self.next_phase("thinking")
            cancelled = self.coordinator.cancel_interaction(
                self.endpoint.token,
                "voice-cancel",
            )
            self.assertEqual(cancelled["phase"], "failed")
            self.next_phase("failed")
            with self.assertRaises(ApiError) as raised:
                result.result(timeout=1)

        self.assertEqual(raised.exception.code, "interaction_cancelled")
        self.assertIsNone(self.synthesizer.text)

    def test_disconnect_cancels_only_the_owning_interaction(self):
        started = threading.Event()

        class BlockingRecognizer:
            def transcribe(_self, _audio):
                started.set()
                threading.Event().wait(0.05)
                return "late transcript"

        self.coordinator.recognizer = BlockingRecognizer()
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(
                self.coordinator.interact,
                self.endpoint.token,
                "voice-disconnect",
                wave_audio().data,
            )
            self.assertTrue(started.wait(1))
            self.next_phase("transcribing")
            self.coordinator.disconnect_endpoint(self.endpoint.token)
            with self.assertRaises(ApiError) as raised:
                result.result(timeout=1)

        self.assertEqual(raised.exception.code, "interaction_cancelled")
        self.assertTrue(
            self.coordinator.interactions["voice-disconnect"].cancelled.is_set()
        )

    def test_playback_timeout_fails_and_releases_the_room(self):
        self.coordinator.interact(
            self.endpoint.token,
            "voice-timeout",
            wave_audio().data,
        )
        self.next_phase("transcribing")
        self.next_phase("thinking")
        self.next_phase("failed")

        self.assertIsNone(self.coordinator.active_interaction)
        self.assertEqual(
            self.coordinator.interactions["voice-timeout"].phase,
            "failed",
        )

    def test_terminal_updates_are_idempotent_but_other_transitions_fail(self):
        self.coordinator.interact(
            self.endpoint.token,
            "voice-terminal",
            wave_audio().data,
        )
        self.next_phase("transcribing")
        self.next_phase("thinking")
        self.coordinator.update_interaction(
            self.endpoint.token,
            "voice-terminal",
            "speaking",
        )
        self.next_phase("speaking")
        self.coordinator.update_interaction(
            self.endpoint.token,
            "voice-terminal",
            "completed",
        )
        self.next_phase("completed")

        repeated = self.coordinator.update_interaction(
            self.endpoint.token,
            "voice-terminal",
            "completed",
        )
        self.assertEqual(repeated["phase"], "completed")
        with self.assertRaises(ApiError) as raised:
            self.coordinator.update_interaction(
                self.endpoint.token,
                "voice-terminal",
                "failed",
            )
        self.assertEqual(raised.exception.code, "interaction_finished")

    def test_voice_and_room_actions_share_one_busy_boundary(self):
        started = threading.Event()

        class BlockingRecognizer:
            def transcribe(_self, _audio):
                started.set()
                threading.Event().wait(0.05)
                return "Question"

        self.coordinator.recognizer = BlockingRecognizer()
        with ThreadPoolExecutor(max_workers=1) as executor:
            interaction = executor.submit(
                self.coordinator.interact,
                self.endpoint.token,
                "voice-busy",
                wave_audio().data,
            )
            self.assertTrue(started.wait(1))
            with self.assertRaises(ApiError) as raised:
                self.coordinator.submit(
                    "action-during-voice",
                    CHANNEL_ACTION,
                    "music",
                )
            self.assertEqual(raised.exception.code, "action_busy")
            self.coordinator.cancel_interaction(
                self.endpoint.token,
                "voice-busy",
            )
            with self.assertRaises(ApiError):
                interaction.result(timeout=1)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_directory = tempfile.TemporaryDirectory()
        client_path = Path(cls.client_directory.name)
        client_path.joinpath("assets").mkdir()
        client_path.joinpath("index.html").write_text(
            '<div id="root"></div>'
            '<script type="module" src="/assets/app.js"></script>'
        )
        client_path.joinpath("assets", "app.js").write_text("const ready = true;")
        cls.server = CortexHomeServer(
            ("127.0.0.1", 0),
            Coordinator(
                action_timeout=0.05,
                agent=FakeAgent(),
                playback_timeout=1,
                recognizer=FakeRecognizer(),
                synthesizer=FakeSynthesizer(),
            ),
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
        status, _headers, body = self.request_raw(
            method,
            path,
            body=body,
            headers=headers,
        )
        return status, json.loads(body)

    def request_raw(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1)
        self.addCleanup(connection.close)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        response_headers = dict(response.getheaders())
        payload = response.read()
        return response.status, response_headers, payload

    @staticmethod
    def read_event(response):
        event = response.readline().decode().strip().removeprefix("event: ")
        data = response.readline().decode().strip().removeprefix("data: ")
        response.readline()
        return event, json.loads(data)

    def read_initial_events(self, response):
        event, ready = self.read_event(response)
        self.assertEqual(event, "ready")
        snapshots = {}
        for _index in range(4):
            event, payload = self.read_event(response)
            snapshots[event] = payload
        self.assertEqual(
            set(snapshots),
            {"music.playback", "channel.active", "today.summary", "room.lighting"},
        )
        return ready, snapshots

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

        ready, snapshots = self.read_initial_events(events_response)
        self.assertEqual(ready["clientEntry"], "/assets/app.js")
        endpoint_token = ready["endpointToken"]
        playback = snapshots["music.playback"]
        self.assertIn(playback["status"], {"playing", "unavailable"})
        lighting = snapshots["room.lighting"]
        self.assertIn(
            lighting["status"],
            {"available", "unavailable"},
        )

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

    def test_completes_an_agent_interaction_over_http(self):
        events_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(events_connection.close)
        events_connection.request("GET", "/api/events")
        events_response = events_connection.getresponse()
        ready, _snapshots = self.read_initial_events(events_response)
        headers = {
            "Content-Type": "audio/wav",
            "X-Endpoint-Token": ready["endpointToken"],
        }

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(
                self.request_raw,
                "POST",
                "/api/agent/interactions/http-voice",
                wave_audio().data,
                headers,
            )
            event, transcribing = self.read_event(events_response)
            self.assertEqual(event, "agent.interaction")
            self.assertEqual(transcribing, {
                "requestId": "http-voice",
                "phase": "transcribing",
            })
            event, thinking = self.read_event(events_response)
            self.assertEqual(event, "agent.interaction")
            self.assertEqual(thinking["phase"], "thinking")
            status, response_headers, body = result.result(timeout=1)

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(response_headers["Content-Type"], "audio/wav")
        self.assertEqual(response_headers["Cache-Control"], "no-store")
        self.assertEqual(body, wave_audio().data)

        status_headers = {
            "Content-Type": "application/json",
            "X-Endpoint-Token": ready["endpointToken"],
        }
        status, payload = self.request(
            "POST",
            "/api/agent/interactions/http-voice/status",
            body=json.dumps({"phase": "speaking"}),
            headers=status_headers,
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["phase"], "speaking")
        event, speaking = self.read_event(events_response)
        self.assertEqual(event, "agent.interaction")
        self.assertEqual(speaking["phase"], "speaking")

        status, payload = self.request(
            "POST",
            "/api/agent/interactions/http-voice/status",
            body=json.dumps({"phase": "completed"}),
            headers=status_headers,
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["phase"], "completed")
        event, completed = self.read_event(events_response)
        self.assertEqual(event, "agent.interaction")
        self.assertEqual(completed["phase"], "completed")
        self.server.coordinator.disconnect_endpoint(ready["endpointToken"])

    def test_agent_http_boundary_requires_auth_and_exact_audio(self):
        status, payload = self.request(
            "POST",
            "/api/agent/interactions/http-no-token",
            body=wave_audio().data,
            headers={"Content-Type": "audio/wav"},
        )
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(payload["code"], "missing_endpoint_token")

        status, payload = self.request(
            "POST",
            "/api/agent/interactions/http-wrong-type",
            body=b"{}",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(payload["code"], "invalid_content_type")

        status, payload = self.request(
            "POST",
            "/api/agent/interactions/http-too-large",
            body=b"x" * (480_045),
            headers={"Content-Type": "audio/wav"},
        )
        self.assertEqual(status, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(payload["code"], "invalid_body_size")

    def test_cancels_an_agent_interaction_over_http(self):
        events_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(events_connection.close)
        events_connection.request("GET", "/api/events")
        events_response = events_connection.getresponse()
        ready, _snapshots = self.read_initial_events(events_response)
        started = threading.Event()

        class BlockingAgent:
            def answer(_self, _request_id, _transcript, _context, cancelled):
                started.set()
                cancelled.wait(1)
                raise AgentError("cancelled")

        previous = self.server.coordinator.agent
        self.server.coordinator.agent = BlockingAgent()
        self.addCleanup(setattr, self.server.coordinator, "agent", previous)
        token_header = {"X-Endpoint-Token": ready["endpointToken"]}

        def submit_interaction():
            return self.request_raw(
                "POST",
                "/api/agent/interactions/http-cancel",
                body=wave_audio().data,
                headers={
                    **token_header,
                    "Content-Type": "audio/wav",
                },
            )

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(submit_interaction)
            self.assertTrue(started.wait(1))
            self.read_event(events_response)
            self.read_event(events_response)
            status, payload = self.request(
                "DELETE",
                "/api/agent/interactions/http-cancel",
                headers=token_header,
            )
            self.assertEqual(status, HTTPStatus.OK)
            self.assertEqual(payload["phase"], "failed")
            event, failed = self.read_event(events_response)
            self.assertEqual(event, "agent.interaction")
            self.assertEqual(failed["phase"], "failed")
            status, response_headers, body = result.result(timeout=1)

        self.assertEqual(status, HTTPStatus.CONFLICT)
        self.assertEqual(response_headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(body)["code"], "interaction_cancelled")
        self.server.coordinator.disconnect_endpoint(ready["endpointToken"])

    def test_completes_a_scene_action_over_http(self):
        self.server.coordinator.report_lighting(AVAILABLE_LIGHTING)
        events_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(events_connection.close)
        events_connection.request("GET", "/api/events")
        events_response = events_connection.getresponse()
        self.assertEqual(events_response.status, HTTPStatus.OK)
        self.read_initial_events(events_response)

        self.server.coordinator.set_scene_activator(
            lambda scene, _timeout: self.server.coordinator.report_lighting(
                {**AVAILABLE_LIGHTING, "activeScenes": [scene]}
            )
        )
        self.addCleanup(self.server.coordinator.set_scene_activator, None)

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
                        {
                            "requestId": "http-scene-request",
                            "action": SCENE_ACTION,
                            "scene": "Relax",
                        }
                    ),
                    headers={"Content-Type": "application/json"},
                )
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(submit_action)
            event, accepted = self.read_event(events_response)
            self.assertEqual(event, "action.status")
            self.assertEqual(accepted["status"], "accepted")
            self.assertEqual(accepted["scene"], "Relax")

            event, lighting = self.read_event(events_response)
            self.assertEqual(event, "room.lighting")
            self.assertEqual(lighting["activeScenes"], ["Relax"])

            event, completed = self.read_event(events_response)
            self.assertEqual(event, "action.status")
            self.assertEqual(completed["status"], "completed")

            status, payload = result.result(timeout=1)
            self.assertEqual(status, HTTPStatus.OK)
            self.assertEqual(payload, completed)

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
        self.assertIn(
            "img-src 'self' data: https:",
            response.getheader("Content-Security-Policy"),
        )
        self.assertIn(
            "connect-src 'self'",
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
        self.assertEqual(payload["hue"], "unconfigured")

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

    def test_selects_a_channel_over_http(self):
        status, payload = self.request(
            "POST",
            "/api/actions",
            body=json.dumps(
                {
                    "requestId": "http-select-camera",
                    "action": CHANNEL_ACTION,
                    "channel": "camera",
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(self.server.coordinator.channel, {"active": "camera"})

        status, payload = self.request(
            "POST",
            "/api/actions",
            body=json.dumps(
                {
                    "requestId": "http-invalid-channel",
                    "action": CHANNEL_ACTION,
                    "channel": "news",
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(payload["code"], "invalid_channel")
        self.assertEqual(self.server.coordinator.channel, {"active": "camera"})

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
        self.read_initial_events(events_response)

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
        self.read_initial_events(first_response)

        second_connection = http.client.HTTPConnection(
            "127.0.0.1",
            self.port,
            timeout=1,
        )
        self.addCleanup(second_connection.close)
        second_connection.request("GET", "/api/events")
        second_response = second_connection.getresponse()
        self.assertEqual(second_response.status, HTTPStatus.OK)
        self.read_initial_events(second_response)

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
