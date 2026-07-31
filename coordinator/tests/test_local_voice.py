import io
import json
import subprocess
import threading
import unittest
import wave
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from local_audio import AlsaInput, AlsaOutput, LocalAudioError
from local_voice import LocalAgent, LocalVoiceError, run_interaction
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
    def __init__(self, data):
        self.data = data
        self.closed = False

    def capture(self, _cancelled):
        return self.data

    def close(self):
        self.closed = True


class FakeOutput:
    def __init__(self, error=None):
        self.error = error
        self.played = None
        self.closed = False

    def play(self, data, _cancelled):
        if self.error:
            raise self.error
        self.played = data

    def close(self):
        self.closed = True


class FakeRecognizer:
    def __init__(self, error=None):
        self.error = error

    def transcribe(self, _audio):
        if self.error:
            raise self.error
        return "Test the development tool."


class FakeSynthesizer:
    def __init__(self, error=None):
        self.error = error

    def synthesize(self, _text):
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


class LocalVoiceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
