import io
import json
import subprocess
import sys
import unittest
import wave
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parents[1]))

from speech import (
    CAPTURE_SAMPLE_RATE,
    MAX_CAPTURE_SECONDS,
    PocketTtsSynthesizer,
    PiperSynthesizer,
    Recognizer,
    SELECTED_RECOGNIZER,
    SELECTED_SYNTHESIZER,
    SpeechError,
    Synthesizer,
    VoskRecognizer,
    WaveAudio,
    WhisperCppRecognizer,
    read_capture,
    load_selected_speech,
)
from qualify_speech import edit_distance, play, words


def wav_bytes(
    frames=1600,
    channels=1,
    sample_rate=CAPTURE_SAMPLE_RATE,
    sample_width=2,
):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00" * frames * channels * sample_width)
    return output.getvalue()


class SpeechTests(unittest.TestCase):
    def test_qualification_accuracy_is_content_free_word_error_rate(self):
        expected = words("Activate Warm, please.")
        actual = words("activate bright please")

        self.assertEqual(expected, ["activate", "warm", "please"])
        self.assertEqual(edit_distance(expected, actual), 1)

    def test_accepts_only_the_bounded_browser_capture_shape(self):
        audio = read_capture(wav_bytes())

        self.assertEqual(audio.sample_rate, 16_000)
        self.assertEqual(audio.frames, 1600)
        self.assertEqual(audio.duration_ms, 100)

        invalid = [
            b"not-wave",
            wav_bytes(frames=0),
            wav_bytes(channels=2),
            wav_bytes(sample_rate=44_100),
            wav_bytes(sample_width=1),
            wav_bytes(frames=CAPTURE_SAMPLE_RATE * MAX_CAPTURE_SECONDS + 1),
        ]
        for data in invalid:
            with self.subTest(length=len(data)):
                with self.assertRaises(SpeechError):
                    read_capture(data)

    def test_selected_roles_are_explicit(self):
        self.assertEqual(SELECTED_RECOGNIZER, "vosk")
        self.assertEqual(SELECTED_SYNTHESIZER, "pocket-tts")
        candidates = json.loads(
            (Path(__file__).parents[1] / "speech-candidates.json").read_text()
        )
        self.assertEqual(
            candidates["selected"],
            {
                "recognizer": SELECTED_RECOGNIZER,
                "synthesizer": SELECTED_SYNTHESIZER,
            },
        )
        self.assertEqual(
            candidates["capture"],
            {
                "container": "WAV",
                "encoding": "signed 16-bit little-endian PCM",
                "sampleRate": 16_000,
                "channels": 1,
                "maximumSeconds": 15,
            },
        )

    def test_whisper_installer_builds_a_runnable_executable(self):
        installer = (
            Path(__file__).parents[1] / "install-speech-host"
        ).read_text()

        self.assertIn("-DBUILD_SHARED_LIBS=OFF", installer)
        self.assertIn(
            'ldd "$install_root/bin/whisper-cli" | grep -q "not found"',
            installer,
        )

    def test_whisper_uses_anonymous_memory_and_bounded_command(self):
        calls = []

        def runner(arguments, **options):
            calls.append((arguments, options))
            input_path = Path(arguments[arguments.index("--file") + 1])
            self.assertTrue(input_path.read_bytes().startswith(b"RIFF"))
            return SimpleNamespace(returncode=0, stdout="hello room\n")

        recognizer = WhisperCppRecognizer(
            "/opt/whisper/whisper-cli",
            "/opt/whisper/base.en-q5_1.bin",
            runner=runner,
        )
        audio = read_capture(wav_bytes())

        self.assertIsInstance(recognizer, Recognizer)
        self.assertEqual(recognizer.transcribe(audio), "hello room")
        arguments, options = calls[0]
        self.assertIn("--no-timestamps", arguments)
        self.assertEqual(options["timeout"], 60)
        self.assertEqual(len(options["pass_fds"]), 1)

    def test_whisper_fails_without_exposing_backend_output(self):
        def runner(*_arguments, **_options):
            return SimpleNamespace(
                returncode=1,
                stdout="private transcript",
                stderr="host details",
            )

        recognizer = WhisperCppRecognizer("whisper-cli", "model", runner=runner)

        with self.assertRaisesRegex(SpeechError, "recognition failed"):
            recognizer.transcribe(read_capture(wav_bytes()))

    def test_vosk_uses_pcm_frames_and_rejects_empty_results(self):
        received = {}

        class FakeRecognizer:
            def __init__(self, model, sample_rate):
                received["model"] = model
                received["sample_rate"] = sample_rate

            def AcceptWaveform(self, pcm):
                received["pcm"] = pcm

            def FinalResult(self):
                return '{"text":"turn on warm"}'

        recognizer = VoskRecognizer("model", FakeRecognizer)
        transcript = recognizer.transcribe(read_capture(wav_bytes(frames=10)))

        self.assertEqual(transcript, "turn on warm")
        self.assertEqual(received["sample_rate"], 16_000)
        self.assertEqual(len(received["pcm"]), 20)

    def test_vosk_returns_a_bounded_partial_result(self):
        class FakeRecognizer:
            def __init__(self, _model, _sample_rate):
                pass

            def AcceptWaveform(self, _pcm):
                pass

            def PartialResult(self):
                return '{"partial":"turn on the warm light"}'

        recognizer = VoskRecognizer("model", FakeRecognizer)

        self.assertEqual(
            recognizer.partial_transcribe(read_capture(wav_bytes(frames=10))),
            "turn on the warm light",
        )

    def test_piper_implements_the_synthesizer_contract(self):
        class FakeVoice:
            def synthesize_wav(self, text, wav):
                self.text = text
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(22_050)
                wav.writeframes(b"\x00\x00" * 2205)

        voice = FakeVoice()
        synthesizer = PiperSynthesizer(voice)
        audio = synthesizer.synthesize("The room is ready.")

        self.assertIsInstance(synthesizer, Synthesizer)
        self.assertEqual(voice.text, "The room is ready.")
        self.assertEqual(audio.sample_rate, 22_050)
        self.assertEqual(audio.duration_ms, 100)

    def test_pocket_tts_implements_the_same_contract(self):
        class Samples:
            def detach(self):
                return self

            def cpu(self):
                return self

            def tolist(self):
                return [-1.0, 0.0, 1.0]

        class FakeModel:
            sample_rate = 24_000

            def generate_audio(self, voice_state, text):
                self.arguments = (voice_state, text)
                return Samples()

        model = FakeModel()
        synthesizer = PocketTtsSynthesizer(model, "alba-state")
        audio = synthesizer.synthesize("The room is ready.")

        self.assertEqual(model.arguments, ("alba-state", "The room is ready."))
        self.assertEqual(audio.sample_rate, 24_000)
        self.assertEqual(audio.frames, 3)

    def test_backend_timeouts_and_invalid_text_fail_explicitly(self):
        def timeout(*_arguments, **_options):
            raise subprocess.TimeoutExpired("whisper-cli", 60)

        recognizer = WhisperCppRecognizer("whisper-cli", "model", runner=timeout)
        with self.assertRaisesRegex(SpeechError, "recognition failed"):
            recognizer.transcribe(read_capture(wav_bytes()))

        synthesizer = PiperSynthesizer(SimpleNamespace())
        for text in ["", " padded ", "x" * 1001]:
            with self.subTest(text_length=len(text)):
                with self.assertRaises(SpeechError):
                    synthesizer.synthesize(text)

    def test_selected_loader_hides_a_backend_model_exception(self):
        class BrokenModel:
            def __init__(self, _path):
                raise Exception("private model path")

        log_levels = []
        pocket_tts = ModuleType("pocket_tts")
        pocket_tts.TTSModel = SimpleNamespace()
        vosk = ModuleType("vosk")
        vosk.Model = BrokenModel
        vosk.SetLogLevel = log_levels.append

        with patch.dict(sys.modules, {"pocket_tts": pocket_tts, "vosk": vosk}):
            with self.assertRaisesRegex(SpeechError, "could not be loaded"):
                load_selected_speech("not-a-model")

        self.assertEqual(log_levels, [-1])

    def test_endpoint_playback_targets_the_kiosk_audio_session(self):
        audio = read_capture(wav_bytes())

        with patch("qualify_speech.subprocess.run") as runner:
            runner.return_value = SimpleNamespace(returncode=0)
            play("imac@imac.local", audio)

        runner.assert_called_once_with(
            [
                "ssh",
                "imac@imac.local",
                "sudo",
                "-n",
                "-u",
                "cortex-endpoint",
                "/usr/local/bin/cortex-speech-qualification-playback",
            ],
            capture_output=True,
            check=False,
            input=audio.data,
            timeout=60,
        )


if __name__ == "__main__":
    unittest.main()
