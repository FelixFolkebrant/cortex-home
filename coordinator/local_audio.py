import os
import signal
import subprocess
import threading
import time


POLL_SECONDS = 0.05


class LocalAudioError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _AlsaProcess:
    def __init__(self, command, device, timeout, popen=subprocess.Popen):
        if not isinstance(command, str) or not command:
            raise LocalAudioError("audio_command_missing")
        if (
            not isinstance(device, str)
            or not device
            or device.strip() != device
            or len(device) > 128
        ):
            raise LocalAudioError("audio_device_invalid")
        self.command = command
        self.device = device
        self.timeout = timeout
        self.popen = popen
        self.lock = threading.Lock()
        self.process = None

    def _start(self, arguments, stdin, stdout):
        try:
            process = self.popen(
                arguments,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as error:
            raise LocalAudioError("audio_command_missing") from error
        except OSError as error:
            raise LocalAudioError("audio_device_failed") from error
        with self.lock:
            self.process = process
        return process

    def _communicate(self, process, data, cancelled, timeout_code, failure_code):
        started = time.monotonic()
        input_data = data
        try:
            while True:
                try:
                    stdout, _stderr = process.communicate(
                        input=input_data,
                        timeout=POLL_SECONDS,
                    )
                    break
                except subprocess.TimeoutExpired:
                    input_data = None
                    if cancelled.is_set():
                        raise LocalAudioError("cancelled")
                    if time.monotonic() - started >= self.timeout:
                        raise LocalAudioError(timeout_code)
                except (OSError, subprocess.SubprocessError) as error:
                    raise LocalAudioError(failure_code) from error
            if cancelled.is_set():
                raise LocalAudioError("cancelled")
            if process.returncode != 0:
                raise LocalAudioError(failure_code)
            return stdout
        except KeyboardInterrupt as error:
            raise LocalAudioError("cancelled") from error
        finally:
            self._stop(process)

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
                process.wait(timeout=POLL_SECONDS)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    process.wait(timeout=POLL_SECONDS)
                except subprocess.TimeoutExpired:
                    pass
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe and not pipe.closed:
                pipe.close()


class AlsaInput(_AlsaProcess):
    def __init__(self, command="arecord", device="default", duration=15, **options):
        super().__init__(command, device, duration + 1, **options)
        self.duration = duration

    def capture(self, cancelled):
        if cancelled.is_set():
            raise LocalAudioError("cancelled")
        process = self._start(
            [
                self.command,
                "--device",
                self.device,
                "--channels",
                "1",
                "--duration",
                str(self.duration),
                "--file-type",
                "wav",
                "--format",
                "S16_LE",
                "--rate",
                "16000",
            ],
            subprocess.DEVNULL,
            subprocess.PIPE,
        )
        return self._communicate(
            process,
            None,
            cancelled,
            "capture_timeout",
            "capture_failed",
        )


class AlsaOutput(_AlsaProcess):
    def __init__(self, command="aplay", device="default", timeout=60, **options):
        super().__init__(command, device, timeout, **options)

    def play(self, audio, cancelled):
        if cancelled.is_set():
            raise LocalAudioError("cancelled")
        if not isinstance(audio, bytes):
            raise LocalAudioError("playback_failed")
        process = self._start(
            [self.command, "--device", self.device, "--file-type", "wav"],
            subprocess.PIPE,
            subprocess.DEVNULL,
        )
        self._communicate(
            process,
            audio,
            cancelled,
            "playback_timeout",
            "playback_failed",
        )
