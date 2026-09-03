import io
import json
import os
import subprocess
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


CAPTURE_CHANNELS = 1
CAPTURE_SAMPLE_RATE = 16_000
CAPTURE_SAMPLE_WIDTH = 2
MAX_CAPTURE_SECONDS = 15
MAX_OUTPUT_SECONDS = 60
MAX_TRANSCRIPT_CHARACTERS = 4_096
MAX_SYNTHESIS_CHARACTERS = 1_000
SPEECH_TIMEOUT_SECONDS = 60
SELECTED_RECOGNIZER = "vosk"
SELECTED_SYNTHESIZER = "pocket-tts"


class SpeechError(Exception):
    pass


@dataclass(frozen=True)
class WaveAudio:
    data: bytes
    sample_rate: int
    frames: int

    @property
    def duration_ms(self):
        return round(self.frames * 1000 / self.sample_rate)


@runtime_checkable
class Recognizer(Protocol):
    def transcribe(self, audio: WaveAudio) -> str: ...


@runtime_checkable
class Synthesizer(Protocol):
    def synthesize(self, text: str) -> WaveAudio: ...


def read_capture(data):
    audio = read_wave(data, MAX_CAPTURE_SECONDS)
    if (
        audio.sample_rate != CAPTURE_SAMPLE_RATE
        or wave_channels(data) != CAPTURE_CHANNELS
        or wave_sample_width(data) != CAPTURE_SAMPLE_WIDTH
    ):
        raise SpeechError(
            "Capture must be 16 kHz mono signed 16-bit PCM WAV."
        )
    return audio


def read_synthesis(data):
    audio = read_wave(data, MAX_OUTPUT_SECONDS)
    if wave_channels(data) != 1 or wave_sample_width(data) != 2:
        raise SpeechError("Synthesized audio must be mono signed 16-bit PCM WAV.")
    return audio


def read_wave(data, maximum_seconds):
    if not isinstance(data, bytes):
        raise SpeechError("Audio must be bytes.")

    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            if wav.getcomptype() != "NONE":
                raise SpeechError("Audio must use uncompressed PCM.")
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
            frame_data = wav.readframes(frames)
    except (EOFError, wave.Error) as error:
        raise SpeechError("Audio is not a valid PCM WAV.") from error

    if (
        channels < 1
        or sample_width < 1
        or sample_rate < 8_000
        or sample_rate > 48_000
        or frames < 1
        or frames > sample_rate * maximum_seconds
        or len(frame_data) != frames * channels * sample_width
    ):
        raise SpeechError("Audio shape or duration is invalid.")

    return WaveAudio(data, sample_rate, frames)


def wave_channels(data):
    with wave.open(io.BytesIO(data), "rb") as wav:
        return wav.getnchannels()


def wave_sample_width(data):
    with wave.open(io.BytesIO(data), "rb") as wav:
        return wav.getsampwidth()


def validate_text(text):
    if (
        not isinstance(text, str)
        or text.strip() != text
        or not 1 <= len(text) <= MAX_SYNTHESIS_CHARACTERS
    ):
        raise SpeechError(
            f"Synthesis text must be 1-{MAX_SYNTHESIS_CHARACTERS} characters."
        )
    return text


class WhisperCppRecognizer:
    def __init__(self, executable, model, threads=4, runner=subprocess.run):
        self.executable = Path(executable)
        self.model = Path(model)
        self.threads = threads
        self.runner = runner

    def transcribe(self, audio):
        audio = read_capture(audio.data)
        descriptor = os.memfd_create("cortex-speech-capture")
        try:
            remaining = memoryview(audio.data)
            while remaining:
                written = os.write(descriptor, remaining)
                if written == 0:
                    raise OSError("Anonymous speech input could not be written.")
                remaining = remaining[written:]
            os.lseek(descriptor, 0, os.SEEK_SET)
            result = self.runner(
                [
                    str(self.executable),
                    "--model",
                    str(self.model),
                    "--file",
                    f"/proc/self/fd/{descriptor}",
                    "--language",
                    "en",
                    "--threads",
                    str(self.threads),
                    "--no-timestamps",
                ],
                capture_output=True,
                check=False,
                pass_fds=(descriptor,),
                text=True,
                timeout=SPEECH_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise SpeechError("whisper.cpp recognition failed.") from error
        finally:
            os.close(descriptor)

        if result.returncode != 0:
            raise SpeechError("whisper.cpp recognition failed.")

        transcript = result.stdout.strip()
        if not 1 <= len(transcript) <= MAX_TRANSCRIPT_CHARACTERS:
            raise SpeechError("whisper.cpp returned an invalid transcript.")
        return transcript


class VoskRecognizer:
    def __init__(self, model, recognizer_type=None):
        if recognizer_type is None:
            try:
                from vosk import KaldiRecognizer
            except ImportError as error:
                raise SpeechError("Vosk is not installed.") from error
            recognizer_type = KaldiRecognizer
        self.model = model
        self.recognizer_type = recognizer_type

    def transcribe(self, audio):
        audio = read_capture(audio.data)
        with wave.open(io.BytesIO(audio.data), "rb") as wav:
            pcm = wav.readframes(wav.getnframes())

        try:
            recognizer = self.recognizer_type(
                self.model,
                CAPTURE_SAMPLE_RATE,
            )
            recognizer.AcceptWaveform(pcm)
            result = json.loads(recognizer.FinalResult())
        except (RuntimeError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise SpeechError("Vosk recognition failed.") from error

        transcript = result.get("text")
        if (
            not isinstance(transcript, str)
            or not 1 <= len(transcript) <= MAX_TRANSCRIPT_CHARACTERS
        ):
            raise SpeechError("Vosk returned an invalid transcript.")
        return transcript

    def partial_transcribe(self, audio):
        audio = read_capture(audio.data)
        with wave.open(io.BytesIO(audio.data), "rb") as wav:
            pcm = wav.readframes(wav.getnframes())

        try:
            recognizer = self.recognizer_type(self.model, CAPTURE_SAMPLE_RATE)
            recognizer.AcceptWaveform(pcm)
            result = json.loads(recognizer.PartialResult())
        except (RuntimeError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise SpeechError("Vosk recognition failed.") from error

        transcript = result.get("partial")
        if not isinstance(transcript, str):
            raise SpeechError("Vosk returned an invalid partial transcript.")
        return transcript.strip()[:MAX_TRANSCRIPT_CHARACTERS]


class PiperSynthesizer:
    def __init__(self, voice):
        self.voice = voice

    def synthesize(self, text):
        text = validate_text(text)
        output = io.BytesIO()
        try:
            with wave.open(output, "wb") as wav:
                self.voice.synthesize_wav(text, wav)
        except (OSError, RuntimeError, ValueError, wave.Error) as error:
            raise SpeechError("Piper synthesis failed.") from error
        return read_synthesis(output.getvalue())


class PocketTtsSynthesizer:
    def __init__(self, model, voice_state):
        self.model = model
        self.voice_state = voice_state

    def synthesize(self, text):
        text = validate_text(text)
        try:
            samples = self.model.generate_audio(self.voice_state, text)
            values = samples.detach().cpu().tolist()
            sample_rate = int(self.model.sample_rate)
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise SpeechError("Pocket TTS synthesis failed.") from error

        pcm = array(
            "h",
            (
                round(max(-1, min(1, float(sample))) * 32767)
                for sample in values
            ),
        )
        output = io.BytesIO()
        try:
            with wave.open(output, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(pcm.tobytes())
        except (OverflowError, TypeError, ValueError, wave.Error) as error:
            raise SpeechError("Pocket TTS synthesis failed.") from error
        return read_synthesis(output.getvalue())


def load_selected_speech(vosk_model, pocket_voice="alba"):
    try:
        from pocket_tts import TTSModel
        from vosk import Model, SetLogLevel
    except ImportError as error:
        raise SpeechError("Selected speech engines are not installed.") from error

    try:
        SetLogLevel(-1)
        recognizer = VoskRecognizer(Model(str(vosk_model)))
        model = TTSModel.load_model()
        voice_state = model.get_state_for_audio_prompt(pocket_voice)
    except Exception as error:
        raise SpeechError("Selected speech engines could not be loaded.") from error
    return recognizer, PocketTtsSynthesizer(model, voice_state)
