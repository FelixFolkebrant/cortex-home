#!/usr/bin/env python3

import argparse
import json
import os
import secrets
import signal
import subprocess
import threading
import time
from pathlib import Path

from local_audio import AlsaInput, AlsaOutput, LocalAudioError
from speech import (
    MAX_CAPTURE_SECONDS,
    SpeechError,
    load_selected_speech,
    read_capture,
    read_synthesis,
)


LOCAL_CONTEXT = {
    "home": {
        "music": {"available": False, "type": "music"},
        "today": {"available": False, "type": "today"},
    }
}
MAX_AGENT_OUTPUT_BYTES = 2_048
MAX_ANSWER_CHARACTERS = 1_000
PHASES = {
    "ready",
    "listening",
    "transcribing",
    "thinking",
    "acting",
    "speaking",
    "completed",
    "failed",
    "cancelled",
}


class LocalVoiceError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class LocalAgent:
    def __init__(
        self,
        node,
        child,
        api_key,
        timeout=20,
        stop_timeout=0.5,
        popen=subprocess.Popen,
    ):
        if not isinstance(api_key, str) or not api_key:
            raise LocalVoiceError("agent_unconfigured")
        self.node = Path(node)
        self.child = Path(child)
        self.api_key = api_key
        self.timeout = timeout
        self.stop_timeout = stop_timeout
        self.popen = popen
        self.lock = threading.Lock()
        self.process = None

    def answer(self, transcript, cancelled, report):
        request_id = f"local-{secrets.token_hex(12)}"
        payload = json.dumps(
            {
                "context": LOCAL_CONTEXT,
                "requestId": request_id,
                "transcript": transcript,
            },
            separators=(",", ":"),
        )
        environment = {"LANG": "C.UTF-8", "OPENROUTER_API_KEY": self.api_key}
        if certificate := os.environ.get("NODE_EXTRA_CA_CERTS"):
            environment["NODE_EXTRA_CA_CERTS"] = certificate
        try:
            process = self.popen(
                [str(self.node), str(self.child)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=environment,
                start_new_session=True,
            )
        except OSError as error:
            raise LocalVoiceError("agent_start_failed") from error
        with self.lock:
            self.process = process

        started = time.monotonic()
        input_text = f"{payload}\n"
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(input=input_text, timeout=0.05)
                    break
                except subprocess.TimeoutExpired:
                    input_text = None
                    if cancelled.is_set():
                        raise LocalVoiceError("cancelled")
                    if time.monotonic() - started >= self.timeout:
                        raise LocalVoiceError("agent_timeout")
                except (OSError, subprocess.SubprocessError) as error:
                    raise LocalVoiceError("agent_failed") from error
            if cancelled.is_set():
                raise LocalVoiceError("cancelled")
            self._report_events(stderr, report)
            if len(stdout.encode()) > MAX_AGENT_OUTPUT_BYTES:
                raise LocalVoiceError("agent_protocol_failed")
            try:
                result = json.loads(stdout)
            except (json.JSONDecodeError, UnicodeError) as error:
                raise LocalVoiceError("agent_protocol_failed") from error
            if not isinstance(result, dict):
                raise LocalVoiceError("agent_protocol_failed")
            if result.get("status") == "failed":
                code = result.get("code")
                raise LocalVoiceError(
                    code
                    if code
                    in {
                        "agent_failed",
                        "cancelled",
                        "invalid_answer",
                        "invalid_request",
                        "invalid_tool_request",
                        "provider_payload_failed",
                        "tool_failed",
                    }
                    else "agent_failed"
                )
            answer = result.get("answer")
            if (
                process.returncode != 0
                or set(result) != {"answer", "requestId", "status"}
                or result["status"] != "completed"
                or result["requestId"] != request_id
                or not isinstance(answer, str)
                or answer.strip() != answer
                or not 1 <= len(answer) <= MAX_ANSWER_CHARACTERS
            ):
                raise LocalVoiceError("agent_protocol_failed")
            return answer
        except KeyboardInterrupt as error:
            raise LocalVoiceError("cancelled") from error
        finally:
            self._stop(process)

    @staticmethod
    def _report_events(stderr, report):
        if not isinstance(stderr, str):
            raise LocalVoiceError("agent_protocol_failed")
        events = stderr.splitlines()
        if events not in ([], ['{"phase":"acting"}']):
            raise LocalVoiceError("agent_protocol_failed")
        if events:
            report("acting")

    def close(self):
        with self.lock:
            process = self.process
        if process:
            self._stop(process)

    def _stop(self, process):
        with self.lock:
            if self.process is process:
                self.process = None
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=self.stop_timeout)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    process.wait(timeout=self.stop_timeout)
                except subprocess.TimeoutExpired:
                    pass
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe and not pipe.closed:
                pipe.close()


def run_interaction(input_boundary, output_boundary, recognizer, synthesizer, agent, cancelled, report):
    if cancelled.is_set():
        raise LocalVoiceError("cancelled")
    report("listening")
    try:
        capture = read_capture(input_boundary.capture(cancelled))
    except LocalAudioError as error:
        raise LocalVoiceError(error.code) from error
    except SpeechError as error:
        raise LocalVoiceError("capture_invalid") from error

    if cancelled.is_set():
        raise LocalVoiceError("cancelled")
    report("transcribing")
    try:
        transcript = recognizer.transcribe(capture)
    except SpeechError as error:
        raise LocalVoiceError("recognition_failed") from error

    if cancelled.is_set():
        raise LocalVoiceError("cancelled")
    report("thinking")
    try:
        answer = agent.answer(transcript, cancelled, report)
    except LocalVoiceError:
        raise

    if cancelled.is_set():
        raise LocalVoiceError("cancelled")
    report("speaking")
    try:
        synthesized = read_synthesis(synthesizer.synthesize(answer).data)
    except (AttributeError, SpeechError) as error:
        raise LocalVoiceError("synthesis_failed") from error
    if cancelled.is_set():
        raise LocalVoiceError("cancelled")
    try:
        output_boundary.play(synthesized.data, cancelled)
    except LocalAudioError as error:
        raise LocalVoiceError(error.code) from error


def report_phase(phase):
    if phase not in PHASES:
        raise LocalVoiceError("phase_failed")
    print(phase, flush=True)


def run_turn_loop(wait, run, report):
    while True:
        report("ready")
        try:
            wait()
        except (EOFError, KeyboardInterrupt):
            return

        cancelled = threading.Event()
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, lambda _signum, _frame: cancelled.set())
        try:
            run(cancelled)
        except LocalVoiceError as error:
            report("cancelled" if error.code == "cancelled" else "failed")
            print(f"error: {error.code}", flush=True)
        else:
            report("completed")
        finally:
            signal.signal(signal.SIGINT, previous_handler)


def arguments():
    parser = argparse.ArgumentParser(
        description="Run one local Cortex Home development voice interaction."
    )
    parser.add_argument("--vosk-model", required=True, type=Path)
    parser.add_argument("--input-device", default="default")
    parser.add_argument("--output-device", default="default")
    parser.add_argument("--node", default="node")
    parser.add_argument(
        "--agent-child",
        default=Path(__file__).parent / "agent" / "local-agent-child.ts",
        type=Path,
    )
    return parser.parse_args()


def main():
    args = arguments()
    input_boundary = AlsaInput(device=args.input_device, duration=MAX_CAPTURE_SECONDS)
    output_boundary = AlsaOutput(device=args.output_device)
    try:
        recognizer, synthesizer = load_selected_speech(args.vosk_model)
        agent = LocalAgent(args.node, args.agent_child, os.environ.get("OPENROUTER_API_KEY"))
        run_turn_loop(
            lambda: input("Press Enter to speak. Ctrl+C cancels the active turn.\n"),
            lambda cancelled: run_interaction(
                input_boundary,
                output_boundary,
                recognizer,
                synthesizer,
                agent,
                cancelled,
                report_phase,
            ),
            report_phase,
        )
    except SpeechError:
        report_phase("failed")
        print("error: speech_unavailable", flush=True)
        return 1
    finally:
        input_boundary.close()
        output_boundary.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
