#!/usr/bin/env python3

import argparse
import json
import os
import re
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

from speech import (
    PocketTtsSynthesizer,
    PiperSynthesizer,
    SpeechError,
    VoskRecognizer,
    WhisperCppRecognizer,
    read_capture,
)


WORD_PATTERN = re.compile(r"[a-z0-9']+")
ENDPOINT_PLAYBACK_COMMAND = [
    "sudo",
    "-n",
    "-u",
    "cortex-endpoint",
    "/usr/local/bin/cortex-speech-qualification-playback",
]
os.environ.setdefault("HF_HOME", "/opt/cortex-speech/pocket-cache")
os.environ.setdefault("HF_HUB_OFFLINE", "1")


def words(text):
    if not isinstance(text, str):
        raise SpeechError("Qualification text must be a string.")
    return WORD_PATTERN.findall(text.casefold())


def edit_distance(expected, actual):
    previous = list(range(len(actual) + 1))
    for expected_index, expected_word in enumerate(expected, start=1):
        current = [expected_index]
        for actual_index, actual_word in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[actual_index] + 1,
                    previous[actual_index - 1]
                    + (expected_word != actual_word),
                )
            )
        previous = current
    return previous[-1]


def load_manifest(path, key):
    try:
        manifest = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechError("The private qualification manifest is invalid.") from error

    cases = manifest.get(key) if isinstance(manifest, dict) else None
    if not isinstance(cases, list) or not cases:
        raise SpeechError(f"The manifest needs at least one {key} case.")
    return cases


def model_size(path):
    try:
        if path.is_file():
            return path.stat().st_size
        if path.is_dir():
            return sum(
                item.stat().st_size for item in path.rglob("*") if item.is_file()
            )
    except OSError as error:
        raise SpeechError("A candidate model could not be inspected.") from error
    raise SpeechError("A candidate model path does not exist.")


def resource_summary(started_at, started_usage, model_bytes):
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_seconds = (
        own.ru_utime
        + own.ru_stime
        + children.ru_utime
        + children.ru_stime
        - started_usage
    )
    return {
        "cpuSeconds": round(cpu_seconds, 3),
        "elapsedMs": round((time.monotonic() - started_at) * 1000),
        "modelBytes": model_bytes,
        "peakRssKiB": max(own.ru_maxrss, children.ru_maxrss),
    }


def load_recognizer(args):
    if args.backend == "whisper.cpp":
        return (
            WhisperCppRecognizer(args.whisper_executable, args.model),
            model_size(args.model),
        )

    try:
        from vosk import Model
    except ImportError as error:
        raise SpeechError("Vosk is not installed.") from error
    return VoskRecognizer(Model(str(args.model))), model_size(args.model)


def qualify_recognition(args):
    cases = load_manifest(args.manifest, "recognition")
    started_at = time.monotonic()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    started_usage = usage.ru_utime + usage.ru_stime
    recognizer, size = load_recognizer(args)
    latencies = []
    edits = 0
    expected_words = 0

    for case in cases:
        if not isinstance(case, dict) or set(case) != {"audio", "expected"}:
            raise SpeechError("Each recognition case needs audio and expected.")
        expected = words(case["expected"])
        if not expected:
            raise SpeechError("A recognition reference has no comparable words.")
        try:
            audio = read_capture(Path(case["audio"]).read_bytes())
        except (OSError, TypeError) as error:
            raise SpeechError("A private capture could not be read.") from error

        case_started_at = time.monotonic()
        transcript = recognizer.transcribe(audio)
        latencies.append(round((time.monotonic() - case_started_at) * 1000))
        edits += edit_distance(expected, words(transcript))
        expected_words += len(expected)

    return {
        "backend": args.backend,
        "cases": len(cases),
        "latencyMedianMs": round(statistics.median(latencies)),
        "latencyMaximumMs": max(latencies),
        "wordErrorRate": round(edits / expected_words, 3),
        **resource_summary(started_at, started_usage, size),
    }


def load_synthesizer(args):
    if args.backend == "piper":
        if args.model is None:
            raise SpeechError("Piper qualification requires --model.")
        try:
            from piper import PiperVoice
        except ImportError as error:
            raise SpeechError("Piper is not installed.") from error
        return PiperSynthesizer(PiperVoice.load(str(args.model)))

    try:
        from pocket_tts import TTSModel
    except ImportError as error:
        raise SpeechError("Pocket TTS is not installed.") from error
    model = TTSModel.load_model()
    return PocketTtsSynthesizer(
        model,
        model.get_state_for_audio_prompt(args.voice),
    )


def play(endpoint, audio):
    try:
        result = subprocess.run(
            ["ssh", endpoint, *ENDPOINT_PLAYBACK_COMMAND],
            capture_output=True,
            check=False,
            input=audio.data,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SpeechError("Endpoint playback failed.") from error
    if result.returncode != 0:
        raise SpeechError("Endpoint playback failed.")


def qualify_synthesis(args):
    cases = load_manifest(args.manifest, "synthesis")
    if not all(isinstance(text, str) for text in cases):
        raise SpeechError("Each synthesis case must be text.")
    started_at = time.monotonic()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    started_usage = usage.ru_utime + usage.ru_stime
    synthesizer = load_synthesizer(args)
    latencies = []
    durations = []

    for text in cases:
        case_started_at = time.monotonic()
        audio = synthesizer.synthesize(text)
        latencies.append(round((time.monotonic() - case_started_at) * 1000))
        durations.append(audio.duration_ms)
        if args.endpoint:
            play(args.endpoint, audio)

    size = model_size(args.model) if args.model else model_size(Path(os.environ["HF_HOME"]))
    return {
        "backend": args.backend,
        "cases": len(cases),
        "generationMedianMs": round(statistics.median(latencies)),
        "generationMaximumMs": max(latencies),
        "outputDurationMedianMs": round(statistics.median(durations)),
        "playedThroughEndpoint": bool(args.endpoint),
        **resource_summary(started_at, started_usage, size),
    }


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    recognition = subparsers.add_parser("recognition")
    recognition.add_argument(
        "--backend",
        choices=["vosk", "whisper.cpp"],
        required=True,
    )
    recognition.add_argument("--manifest", type=Path, required=True)
    recognition.add_argument("--model", type=Path, required=True)
    recognition.add_argument(
        "--whisper-executable",
        type=Path,
        default=Path("/opt/cortex-speech/bin/whisper-cli"),
    )
    recognition.set_defaults(run=qualify_recognition)

    synthesis = subparsers.add_parser("synthesis")
    synthesis.add_argument(
        "--backend",
        choices=["piper", "pocket-tts"],
        required=True,
    )
    synthesis.add_argument("--manifest", type=Path, required=True)
    synthesis.add_argument("--model", type=Path)
    synthesis.add_argument("--voice", default="alba")
    synthesis.add_argument("--endpoint")
    synthesis.set_defaults(run=qualify_synthesis)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        summary = args.run(args)
    except SpeechError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
