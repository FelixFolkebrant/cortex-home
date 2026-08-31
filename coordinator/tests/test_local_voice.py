import io
import json
import signal
import subprocess
import threading
import unittest
import wave
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from local_audio import AlsaInput, AlsaOutput, LocalAudioError
from local_voice import (
    LocalAgent,
    LocalVoiceError,
    report_phase,
    run_interaction,
    run_turn_loop,
)
from speech import SpeechError, read_capture, read_synthesis


def wav_bytes(sample_rate=16_000, frames=160):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames)
    return output.getvalue()


class FakeInput:
    def __init__(self, data, cancelled=None):
        self.data = data
        self.cancelled = cancelled
        self.closed = False

    def capture(self, _cancelled):
        if self.cancelled:
            self.cancelled.set()
        return self.data

    def close(self):
        self.closed = True


class FakeOutput:
    def __init__(self, error=None, cancelled=None):
        self.error = error
        self.cancelled = cancelled
        self.played = None
        self.closed = False

    def play(self, data, _cancelled):
        if self.cancelled:
            self.cancelled.set()
            raise LocalAudioError("cancelled")
        if self.error:
            raise self.error
        self.played = data

    def close(self):
        self.closed = True


class FakeRecognizer:
    def __init__(self, error=None, cancelled=None):
        self.error = error
        self.cancelled = cancelled

    def transcribe(self, _audio):
        if self.cancelled:
            self.cancelled.set()
        if self.error:
            raise self.error
        return "Test the development tool."


class FakeSynthesizer:
    def __init__(self, error=None, cancelled=None):
        self.error = error
        self.cancelled = cancelled

    def synthesize(self, _text):
        if self.cancelled:
            self.cancelled.set()
        if self.error:
            raise self.error
        return read_synthesis(wav_bytes(sample_rate=24_000))


class FakeAgent:
    def __init__(self, cancelled=None, action=False):
        self.cancelled = cancelled
        self.action = action

    def answer(self, _transcript, _cancelled, report):
        if self.action:
            report("acting")
        if self.cancelled:
            self.cancelled.set()
        return "The simulated development tool completed."


class ClosedPipe:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class CompletedProcess:
    def __init__(self, stdout):
        self.stdout = ClosedPipe()
        self.stdin = ClosedPipe()
        self.stderr = ClosedPipe()
        self.output = stdout
        self.returncode = 0

    def communicate(self, input=None, timeout=None):
        self.input = input
        self.timeout = timeout
        return self.output, b""

    def poll(self):
        return self.returncode


class AgentProcess(CompletedProcess):
    def __init__(self, response):
        super().__init__("")
        self.response = response

    def communicate(self, input=None, timeout=None):
        self.input = input
        self.timeout = timeout
        return self.response, ""


class CancelledProcess(CompletedProcess):
    def __init__(self, cancelled):
        super().__init__(b"")
        self.cancelled = cancelled
        self.pid = 123_456
        self.returncode = None

    def communicate(self, input=None, timeout=None):
        self.input = input
        self.cancelled.set()
        raise subprocess.TimeoutExpired("faux-audio", timeout)

    def wait(self, timeout=None):
        self.returncode = -15
        return self.returncode


class LocalVoiceTests(unittest.TestCase):
    def test_reports_ready_as_a_content_free_local_phase(self):
        self.assertIsNone(report_phase("ready"))

    def test_turn_loop_returns_to_ready_for_each_local_turn(self):
        waits = iter([None, None, EOFError()])
        phases = []
        turns = []

        def wait():
            result = next(waits)
            if isinstance(result, BaseException):
                raise result

        run_turn_loop(
            wait,
            lambda cancelled: turns.append(cancelled.is_set()),
            phases.append,
        )

        self.assertEqual(turns, [False, False])
        self.assertEqual(phases, ["ready", "completed", "ready", "completed", "ready"])

    def test_turn_loop_recovers_with_a_fresh_scope_after_cancellation(self):
        waits = iter([None, None, EOFError()])
        phases = []
        turns = []

        def wait():
            result = next(waits)
            if isinstance(result, BaseException):
                raise result

        def run(cancelled):
            turns.append(cancelled)
            if len(turns) == 1:
                raise LocalVoiceError("cancelled")

        with redirect_stdout(io.StringIO()) as output:
            run_turn_loop(wait, run, phases.append)

        self.assertIsNot(turns[0], turns[1])
        self.assertFalse(turns[1].is_set())
        self.assertEqual(
            phases,
            ["ready", "cancelled", "ready", "completed", "ready"],
        )
        self.assertEqual(output.getvalue(), "error: cancelled\n")

    def test_turn_loop_exits_cleanly_when_ready_input_is_interrupted(self):
        phases = []

        run_turn_loop(
            lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            lambda _cancelled: self.fail("No turn should start."),
            phases.append,
        )

        self.assertEqual(phases, ["ready"])

    def test_answer_only_runs_content_free_phases_and_plays_audio(self):
        phases = []
        output = FakeOutput()
        run_interaction(
            FakeInput(wav_bytes()),
            output,
            FakeRecognizer(),
            FakeSynthesizer(),
            FakeAgent(),
            threading.Event(),
            phases.append,
        )

        self.assertEqual(
            phases,
            ["listening", "transcribing", "thinking", "speaking"],
        )
        self.assertTrue(output.played.startswith(b"RIFF"))

    def test_tool_continuation_reports_acting_before_local_playback(self):
        phases = []
        run_interaction(
            FakeInput(wav_bytes()),
            FakeOutput(),
            FakeRecognizer(),
            FakeSynthesizer(),
            FakeAgent(action=True),
            threading.Event(),
            phases.append,
        )

        self.assertEqual(
            phases,
            ["listening", "transcribing", "thinking", "acting", "speaking"],
        )

    def test_speech_and_audio_failures_are_terminal_and_do_not_play(self):
        cases = [
            (FakeInput(b"invalid"), FakeRecognizer(), FakeSynthesizer(), "capture_invalid"),
            (
                FakeInput(wav_bytes()),
                FakeRecognizer(SpeechError("private")),
                FakeSynthesizer(),
                "recognition_failed",
            ),
            (
                FakeInput(wav_bytes()),
                FakeRecognizer(),
                FakeSynthesizer(SpeechError("private")),
                "synthesis_failed",
            ),
            (
                FakeInput(wav_bytes()),
                FakeRecognizer(),
                FakeSynthesizer(),
                "playback_failed",
            ),
        ]
        for input_boundary, recognizer, synthesizer, expected in cases:
            with self.subTest(expected=expected):
                output = FakeOutput(
                    LocalAudioError("playback_failed")
                    if expected == "playback_failed"
                    else None
                )
                with self.assertRaises(LocalVoiceError) as raised:
                    run_interaction(
                        input_boundary,
                        output,
                        recognizer,
                        synthesizer,
                        FakeAgent(),
                        threading.Event(),
                        lambda _phase: None,
                    )
                self.assertEqual(raised.exception.code, expected)
                self.assertIsNone(output.played)

    def test_late_agent_answer_is_ignored_after_cancellation(self):
        cancelled = threading.Event()
        output = FakeOutput()

        with self.assertRaises(LocalVoiceError) as raised:
            run_interaction(
                FakeInput(wav_bytes()),
                output,
                FakeRecognizer(),
                FakeSynthesizer(),
                FakeAgent(cancelled=cancelled),
                cancelled,
                lambda _phase: None,
            )

        self.assertEqual(raised.exception.code, "cancelled")
        self.assertIsNone(output.played)

    def test_cancellation_rejects_results_from_every_local_phase(self):
        cases = [
            lambda cancelled: (
                FakeInput(wav_bytes(), cancelled=cancelled),
                FakeRecognizer(),
                FakeSynthesizer(),
                FakeAgent(),
                FakeOutput(),
            ),
            lambda cancelled: (
                FakeInput(wav_bytes()),
                FakeRecognizer(cancelled=cancelled),
                FakeSynthesizer(),
                FakeAgent(),
                FakeOutput(),
            ),
            lambda cancelled: (
                FakeInput(wav_bytes()),
                FakeRecognizer(),
                FakeSynthesizer(),
                FakeAgent(cancelled=cancelled),
                FakeOutput(),
            ),
            lambda cancelled: (
                FakeInput(wav_bytes()),
                FakeRecognizer(),
                FakeSynthesizer(cancelled=cancelled),
                FakeAgent(),
                FakeOutput(),
            ),
            lambda cancelled: (
                FakeInput(wav_bytes()),
                FakeRecognizer(),
                FakeSynthesizer(),
                FakeAgent(),
                FakeOutput(cancelled=cancelled),
            ),
        ]

        for phase, collaborators in enumerate(cases):
            with self.subTest(phase=phase):
                cancelled = threading.Event()
                input_boundary, recognizer, synthesizer, agent, output = collaborators(
                    cancelled
                )
                with self.assertRaises(LocalVoiceError) as raised:
                    run_interaction(
                        input_boundary,
                        output,
                        recognizer,
                        synthesizer,
                        agent,
                        cancelled,
                        lambda _phase: None,
                    )

                self.assertEqual(raised.exception.code, "cancelled")
                self.assertIsNone(output.played)

    def test_alsa_boundaries_release_faux_process_pipes(self):
        capture_process = CompletedProcess(wav_bytes())
        input_boundary = AlsaInput(popen=lambda *_args, **_options: capture_process)
        self.assertEqual(read_capture(input_boundary.capture(threading.Event())).frames, 160)
        self.assertTrue(capture_process.stdout.closed)

        playback_process = CompletedProcess(b"")
        output_boundary = AlsaOutput(popen=lambda *_args, **_options: playback_process)
        output_boundary.play(wav_bytes(), threading.Event())
        self.assertTrue(playback_process.stdin.closed)
        self.assertTrue(playback_process.stdout.closed)

    def test_cancelled_alsa_boundaries_stop_processes_and_release_pipes(self):
        for boundary_name in ("capture", "playback"):
            with self.subTest(boundary=boundary_name):
                cancelled = threading.Event()
                process = CancelledProcess(cancelled)
                boundary = (
                    AlsaInput(popen=lambda *_args, **_options: process)
                    if boundary_name == "capture"
                    else AlsaOutput(popen=lambda *_args, **_options: process)
                )

                with patch("local_audio.os.killpg") as killpg:
                    with self.assertRaises(LocalAudioError) as raised:
                        if boundary_name == "capture":
                            boundary.capture(cancelled)
                        else:
                            boundary.play(wav_bytes(), cancelled)

                self.assertEqual(raised.exception.code, "cancelled")
                killpg.assert_called_once_with(process.pid, signal.SIGTERM)
                self.assertTrue(process.stdin.closed)
                self.assertTrue(process.stdout.closed)
                self.assertTrue(process.stderr.closed)

    def test_alsa_rejects_invalid_devices_before_starting_a_process(self):
        with self.assertRaises(LocalAudioError) as raised:
            AlsaInput(device=" bad")
        self.assertEqual(raised.exception.code, "audio_device_invalid")

    def test_local_agent_rejects_a_stale_child_response(self):
        process = AgentProcess(
            json.dumps(
                {
                    "answer": "This must not be accepted.",
                    "requestId": "local-stale",
                    "status": "completed",
                }
            )
        )
        agent = LocalAgent(
            "node",
            "child.js",
            "private-test-key",
            popen=lambda *_arguments, **_options: process,
        )

        with self.assertRaises(LocalVoiceError) as raised:
            agent.answer("Question", threading.Event(), lambda _phase: None)

        self.assertEqual(raised.exception.code, "agent_protocol_failed")
        self.assertTrue(process.stdout.closed)

    def test_local_agent_uses_a_fresh_request_id_after_cancellation(self):
        first_cancelled = threading.Event()
        processes = [
            CancelledProcess(first_cancelled),
            AgentProcess(
                json.dumps(
                    {
                        "answer": "Second answer.",
                        "requestId": "local-second",
                        "status": "completed",
                    }
                )
            ),
        ]
        pending = iter(processes)
        agent = LocalAgent(
            "node",
            "child.js",
            "private-test-key",
            popen=lambda *_arguments, **_options: next(pending),
        )

        with (
            patch("local_voice.os.killpg") as killpg,
            patch("local_voice.secrets.token_hex", side_effect=["first", "second"]),
        ):
            with self.assertRaises(LocalVoiceError) as raised:
                agent.answer(
                    "Cancelled question",
                    first_cancelled,
                    lambda _phase: None,
                )
            self.assertEqual(
                agent.answer("Fresh question", threading.Event(), lambda _phase: None),
                "Second answer.",
            )

        self.assertEqual(raised.exception.code, "cancelled")
        killpg.assert_called_once_with(processes[0].pid, signal.SIGTERM)
        requests = [json.loads(process.input) for process in processes]
        self.assertEqual(
            [request["requestId"] for request in requests],
            ["local-first", "local-second"],
        )


if __name__ == "__main__":
    unittest.main()
