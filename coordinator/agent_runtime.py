import json
import os
import queue
import signal
import subprocess
import threading
import time
from pathlib import Path


MAX_AGENT_OUTPUT_BYTES = 2_048
MAX_ANSWER_CHARACTERS = 1_000


class AgentError(Exception):
    def __init__(self, code="agent_failed"):
        super().__init__(code)
        self.code = code


class NodeAgent:
    def __init__(
        self,
        node,
        child,
        api_key,
        timeout=20,
        stop_timeout=0.5,
        popen=subprocess.Popen,
    ):
        self.node = Path(node)
        self.child = Path(child)
        self.api_key = api_key
        self.timeout = timeout
        self.stop_timeout = stop_timeout
        self.popen = popen
        self.lock = threading.Lock()
        self.stop_lock = threading.Lock()
        self.process = None
        self.closed = False

        if not isinstance(api_key, str) or not api_key:
            raise AgentError("agent_unconfigured")

    def answer(
        self,
        request_id,
        transcript,
        context,
        cancelled,
        session_id=None,
        turn_epoch=None,
    ):
        request = {
            "requestId": request_id,
            "transcript": transcript,
            "context": context,
        }
        if session_id is not None or turn_epoch is not None:
            if not isinstance(session_id, str) or not isinstance(turn_epoch, int):
                raise AgentError("invalid_request")
            request["sessionId"] = session_id
            request["turnEpoch"] = turn_epoch
        payload = json.dumps(request, separators=(",", ":"))
        environment = {
            "LANG": "C.UTF-8",
            "OPENROUTER_API_KEY": self.api_key,
        }
        if certificate := os.environ.get("NODE_EXTRA_CA_CERTS"):
            environment["NODE_EXTRA_CA_CERTS"] = certificate

        with self.lock:
            if self.closed:
                raise AgentError("cancelled")
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
                raise AgentError("agent_start_failed") from error
            self.process = process

        started = time.monotonic()
        input_text = f"{payload}\n"
        while True:
            try:
                stdout, stderr = process.communicate(
                    input=input_text,
                    timeout=0.05,
                )
                break
            except subprocess.TimeoutExpired:
                input_text = None
                if cancelled.is_set() or self._is_closed():
                    self._stop(process)
                    raise AgentError("cancelled")
                if time.monotonic() - started >= self.timeout:
                    self._stop(process)
                    raise AgentError("agent_timeout")
            except (OSError, subprocess.SubprocessError) as error:
                self._stop(process)
                raise AgentError("cancelled" if self._is_closed() else "agent_failed") from error

        if cancelled.is_set() or self._is_closed():
            raise AgentError("cancelled")
        if stderr or len(stdout.encode()) > MAX_AGENT_OUTPUT_BYTES:
            raise AgentError("agent_protocol_failed")

        try:
            result = json.loads(stdout)
        except (json.JSONDecodeError, UnicodeError) as error:
            raise AgentError("agent_protocol_failed") from error
        if not isinstance(result, dict):
            raise AgentError("agent_protocol_failed")
        if result.get("status") == "failed":
            code = result.get("code")
            raise AgentError(
                code
                if code
                in {
                    "agent_failed",
                    "cancelled",
                    "invalid_answer",
                    "invalid_request",
                    "provider_payload_failed",
                }
                else "agent_failed"
            )

        answer = result.get("answer")
        expected_keys = {"answer", "requestId", "status"}
        if session_id is not None:
            expected_keys.update({"sessionId", "turnEpoch"})
        if (
            process.returncode != 0
            or set(result) != expected_keys
            or result["status"] != "completed"
            or result["requestId"] != request_id
            or (session_id is not None and result["sessionId"] != session_id)
            or (session_id is not None and result["turnEpoch"] != turn_epoch)
            or not isinstance(answer, str)
            or answer.strip() != answer
            or not 1 <= len(answer) <= MAX_ANSWER_CHARACTERS
        ):
            raise AgentError("agent_protocol_failed")
        return answer

    def start_session(self, session_id):
        if not isinstance(session_id, str) or not session_id:
            raise AgentError("invalid_request")
        with self.lock:
            if self.closed:
                raise AgentError("cancelled")
        return DialogueSession(
            self.node,
            self.child.with_name("dialogue-child.js"),
            self.api_key,
            self.timeout,
            self.stop_timeout,
            self.popen,
        )

    def close(self):
        with self.lock:
            self.closed = True
            process = self.process
        if process:
            self._stop(process)

    def _is_closed(self):
        with self.lock:
            return self.closed

    def _stop(self, process):
        with self.stop_lock:
            if process.poll() is not None:
                self._close_pipes(process)
                return
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
            finally:
                self._close_pipes(process)

    @staticmethod
    def _close_pipes(process):
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe and not pipe.closed:
                pipe.close()


class DialogueSession:
    _close_pipes = staticmethod(NodeAgent._close_pipes)

    def __init__(self, node, child, api_key, timeout, stop_timeout, popen):
        self.node = Path(node)
        self.child = Path(child)
        self.api_key = api_key
        self.timeout = timeout
        self.stop_timeout = stop_timeout
        self.popen = popen
        self.lock = threading.Lock()
        self.stop_lock = threading.Lock()
        self.events = queue.Queue()
        self.closed = False
        self.process = self._start()
        self.reader = threading.Thread(target=self._read_events, daemon=True)
        self.reader.start()

    def _start(self):
        environment = {"LANG": "C.UTF-8", "OPENROUTER_API_KEY": self.api_key}
        if certificate := os.environ.get("NODE_EXTRA_CA_CERTS"):
            environment["NODE_EXTRA_CA_CERTS"] = certificate
        try:
            return self.popen(
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
            raise AgentError("agent_start_failed") from error

    def _read_events(self):
        try:
            for line in self.process.stdout:
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    self.events.put(("invalid", None))
                    return
                self.events.put(("event", event))
        finally:
            self.events.put(("closed", None))

    def answer(self, request_id, transcript, context, cancelled, on_delta):
        try:
            request = json.dumps(
                {"requestId": request_id, "transcript": transcript, "context": context},
                separators=(",", ":"),
            )
            with self.lock:
                if self.closed or self.process.poll() is not None:
                    raise AgentError("cancelled" if self.closed else "agent_failed")
                try:
                    self.process.stdin.write(f"{request}\n")
                    self.process.stdin.flush()
                except OSError as error:
                    raise AgentError("agent_failed") from error

            started = time.monotonic()
            while True:
                if cancelled.is_set():
                    raise AgentError("cancelled")
                if time.monotonic() - started >= self.timeout:
                    raise AgentError("agent_timeout")
                try:
                    kind, event = self.events.get(timeout=0.05)
                except queue.Empty:
                    continue
                if kind != "event" or not isinstance(event, dict):
                    raise AgentError("agent_protocol_failed")
                if event.get("requestId") != request_id:
                    raise AgentError("agent_protocol_failed")
                if event.get("type") == "delta":
                    delta = event.get("delta")
                    if not isinstance(delta, str) or not delta:
                        raise AgentError("agent_protocol_failed")
                    on_delta(delta)
                    continue
                if event.get("type") == "completed":
                    answer = event.get("answer")
                    if (
                        set(event) != {"answer", "requestId", "status", "type"}
                        or event.get("status") != "completed"
                        or not isinstance(answer, str)
                        or answer.strip() != answer
                        or not 1 <= len(answer) <= MAX_ANSWER_CHARACTERS
                    ):
                        raise AgentError("agent_protocol_failed")
                    return answer
                if event.get("type") == "failed":
                    code = event.get("code")
                    raise AgentError(
                        code
                        if code in {"agent_failed", "cancelled", "invalid_answer", "invalid_request", "provider_payload_failed"}
                        else "agent_failed"
                    )
                raise AgentError("agent_protocol_failed")
        except Exception:
            self.close()
            raise

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            process = self.process
        NodeAgent._stop(self, process)
