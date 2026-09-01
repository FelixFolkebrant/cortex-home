import os
import stat
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from agent_runtime import AgentError, NodeAgent


class NodeAgentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.child = self.root / "answer-child.js"
        self.child.write_text("")

    def executable(self, body):
        path = self.root / f"fake-node-{len(list(self.root.glob('fake-node-*')))}"
        path.write_text(f"#!/usr/bin/env python3\n{body}")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def agent(self, body, **options):
        return NodeAgent(
            self.executable(body),
            self.child,
            "private-test-key",
            **options,
        )

    def test_returns_one_matching_bounded_answer(self):
        agent = self.agent(
            "import json, sys\n"
            "request = json.loads(sys.stdin.read())\n"
            "assert request['transcript'] == 'What is playing?'\n"
            "assert request['context']['activeChannel'] == 'music'\n"
            "print(json.dumps({'status': 'completed', "
            "'requestId': request['requestId'], 'answer': 'A test track.'}))\n"
        )

        answer = agent.answer(
            "voice-1",
            "What is playing?",
            {"activeChannel": "music"},
            threading.Event(),
        )

        self.assertEqual(answer, "A test track.")

    def test_rejects_stderr_malformed_and_mismatched_output(self):
        cases = [
            "import sys\nsys.stderr.write('private')\nprint('{}')\n",
            "print('not json')\n",
            "print('{\"status\":\"completed\",\"requestId\":\"wrong\","
            "\"answer\":\"No\"}')\n",
            "print('{\"status\":\"completed\",\"requestId\":\"voice-1\","
            "\"answer\":\" padded \"}')\n",
        ]

        for body in cases:
            with self.subTest(body=body):
                with self.assertRaises(AgentError) as raised:
                    self.agent(body).answer(
                        "voice-1",
                        "Question",
                        {"activeChannel": "today"},
                        threading.Event(),
                    )
                self.assertEqual(raised.exception.code, "agent_protocol_failed")

    def test_maps_only_known_content_free_child_failures(self):
        for supplied, expected in [
            ("invalid_answer", "invalid_answer"),
            ("private-provider-detail", "agent_failed"),
        ]:
            with self.subTest(code=supplied):
                body = (
                    "import json, sys\n"
                    "sys.stdin.read()\n"
                    f"print(json.dumps({{'status': 'failed', 'code': '{supplied}'}}))\n"
                    "raise SystemExit(1)\n"
                )
                with self.assertRaises(AgentError) as raised:
                    self.agent(body).answer(
                        "voice-1",
                        "Question",
                        {"activeChannel": "today"},
                        threading.Event(),
                    )
                self.assertEqual(raised.exception.code, expected)

    def test_cancellation_terminates_the_process_group(self):
        marker = self.root / "started"
        agent = self.agent(
            "import pathlib, sys, time\n"
            "sys.stdin.read()\n"
            f"pathlib.Path({str(marker)!r}).write_text('started')\n"
            "time.sleep(30)\n",
            timeout=5,
        )
        cancelled = threading.Event()

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(
                agent.answer,
                "voice-cancel",
                "Question",
                {"activeChannel": "today"},
                cancelled,
            )
            for _index in range(100):
                if marker.exists():
                    break
                threading.Event().wait(0.01)
            self.assertTrue(marker.exists())
            cancelled.set()
            with self.assertRaises(AgentError) as raised:
                result.result(timeout=2)

        self.assertEqual(raised.exception.code, "cancelled")

    def test_timeout_terminates_the_child(self):
        with self.assertRaises(AgentError) as raised:
            self.agent(
                "import sys, time\nsys.stdin.read()\ntime.sleep(30)\n",
                timeout=0.05,
            ).answer(
                "voice-timeout",
                "Question",
                {"activeChannel": "today"},
                threading.Event(),
            )
        self.assertEqual(raised.exception.code, "agent_timeout")

    def test_parent_close_terminates_the_process_group(self):
        marker = self.root / "started"
        agent = self.agent(
            "import pathlib, sys, time\n"
            "sys.stdin.read()\n"
            f"pathlib.Path({str(marker)!r}).write_text('started')\n"
            "time.sleep(30)\n",
            timeout=5,
        )

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(
                agent.answer,
                "voice-shutdown",
                "Question",
                {"activeChannel": "today"},
                threading.Event(),
            )
            for _index in range(100):
                if marker.exists():
                    break
                threading.Event().wait(0.01)
            self.assertTrue(marker.exists())
            agent.close()
            with self.assertRaises(AgentError) as raised:
                result.result(timeout=2)

        self.assertEqual(raised.exception.code, "cancelled")
        with self.assertRaises(AgentError) as closed:
            agent.answer(
                "voice-after-shutdown",
                "Question",
                {"activeChannel": "today"},
                threading.Event(),
            )
        self.assertEqual(closed.exception.code, "cancelled")

    def test_requires_a_protected_key_before_start(self):
        with self.assertRaises(AgentError) as raised:
            NodeAgent("/node", self.child, "")
        self.assertEqual(raised.exception.code, "agent_unconfigured")

    def test_child_receives_only_the_required_environment(self):
        agent = self.agent(
            "import json, os, sys\n"
            "request = json.loads(sys.stdin.read())\n"
            "assert set(os.environ) <= {'LANG', 'LC_CTYPE', 'OPENROUTER_API_KEY'}\n"
            "assert os.environ['OPENROUTER_API_KEY'] == 'private-test-key'\n"
            "print(json.dumps({'status': 'completed', "
            "'requestId': request['requestId'], 'answer': 'Safe.'}))\n"
        )

        self.assertEqual(
            agent.answer(
                "voice-env",
                "Question",
                {"activeChannel": "today"},
                threading.Event(),
            ),
            "Safe.",
        )

    def test_one_session_child_streams_multiple_turns_until_closed(self):
        agent = self.agent(
            "import json, sys\n"
            "for line in sys.stdin:\n"
            " request = json.loads(line)\n"
            " print(json.dumps({'type': 'delta', 'requestId': request['requestId'], 'delta': 'Early. '}), flush=True)\n"
            " print(json.dumps({'type': 'completed', 'status': 'completed', 'requestId': request['requestId'], 'answer': 'Early.'}), flush=True)\n"
        )
        session = agent.start_session("voice-session-1")
        deltas = []
        try:
            self.assertEqual(
                session.answer("voice-1", "Question", {}, threading.Event(), deltas.append),
                "Early.",
            )
            self.assertEqual(
                session.answer("voice-2", "Follow-up", {}, threading.Event(), deltas.append),
                "Early.",
            )
        finally:
            session.close()
        self.assertEqual(deltas, ["Early. ", "Early. "])

    def test_session_timeout_closes_the_child(self):
        session = self.agent(
            "import sys, time\n"
            "for _line in sys.stdin:\n"
            " time.sleep(30)\n",
            timeout=0.05,
        ).start_session("voice-session-timeout")

        with self.assertRaises(AgentError) as raised:
            session.answer(
                "voice-timeout",
                "Question",
                {},
                threading.Event(),
                lambda _delta: None,
            )

        self.assertEqual(raised.exception.code, "agent_timeout")
        self.assertTrue(session.closed)
        self.assertIsNotNone(session.process.poll())


if __name__ == "__main__":
    unittest.main()
