import json
import os
import signal
import subprocess
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

        if not isinstance(api_key, str) or not api_key:
            raise AgentError("agent_unconfigured")

    def answer(self, request_id, transcript, context, cancelled):
        payload = json.dumps(
            {
                "requestId": request_id,
                "transcript": transcript,
                "context": context,
            },
            separators=(",", ":"),
        )
        environment = {
            "LANG": "C.UTF-8",
            "OPENROUTER_API_KEY": self.api_key,
        }
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
            raise AgentError("agent_start_failed") from error

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
                if cancelled.is_set():
                    self._stop(process)
                    raise AgentError("cancelled")
                if time.monotonic() - started >= self.timeout:
                    self._stop(process)
                    raise AgentError("agent_timeout")
            except (OSError, subprocess.SubprocessError) as error:
                self._stop(process)
                raise AgentError("agent_failed") from error

        if cancelled.is_set():
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
        if (
            process.returncode != 0
            or set(result) != {"answer", "requestId", "status"}
            or result["status"] != "completed"
            or result["requestId"] != request_id
            or not isinstance(answer, str)
            or answer.strip() != answer
            or not 1 <= len(answer) <= MAX_ANSWER_CHARACTERS
        ):
            raise AgentError("agent_protocol_failed")
        return answer

    def _stop(self, process):
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
