import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from hue import HueAdapter, HueAuthenticationError, summarize_v2


CONFIG = {
    "host": "hue-bridge.local",
    "app_key": "secret-application-key",
    "bridge_id": "001788ABCDEF",
    "supports_v2": True,
}


class HueAdapterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config_path = Path(self.directory.name, "hue.json")
        self.statuses = []

    def write_config(self, payload=CONFIG):
        self.config_path.write_text(json.dumps(payload))

    def wait_for(self, expected):
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if expected in self.statuses:
                return
            time.sleep(0.01)
        self.fail(f"Hue status did not reach {expected}: {self.statuses}")

    def start_adapter(self, connector, retry_seconds=0.01):
        adapter = HueAdapter(
            self.config_path,
            self.statuses.append,
            connector=connector,
            retry_seconds=retry_seconds,
        )
        adapter.start()
        self.addCleanup(adapter.stop)
        return adapter

    def test_missing_configuration_stays_unconfigured(self):
        async def unused_connector(*_args):
            self.fail("Missing configuration must not start the connector")

        adapter = self.start_adapter(unused_connector)
        self.wait_for("unconfigured")

        self.assertEqual(adapter.snapshot()["status"], "unconfigured")

    def test_invalid_configuration_is_distinct(self):
        self.write_config({"host": "bridge.local"})

        adapter = self.start_adapter(None)
        self.wait_for("invalid_configuration")

        self.assertEqual(adapter.snapshot()["status"], "invalid_configuration")

    def test_connects_with_sanitized_inventory(self):
        self.write_config()
        inventory = {
            "generation": "v2",
            "rooms": ["Office"],
            "scenes": ["Read"],
            "remotes": [{"model": "RWL022"}],
        }

        async def connector(config, status, publish_inventory, stop_event):
            self.assertEqual(config.host, CONFIG["host"])
            self.assertEqual(config.app_key, CONFIG["app_key"])
            publish_inventory(inventory)
            status("connected")
            while not stop_event.is_set():
                await asyncio.sleep(0.01)

        adapter = self.start_adapter(connector)
        self.wait_for("connected")
        snapshot = adapter.snapshot()

        self.assertEqual(snapshot["inventory"], inventory)
        self.assertNotIn(CONFIG["host"], json.dumps(snapshot["inventory"]))
        self.assertNotIn(CONFIG["app_key"], json.dumps(snapshot["inventory"]))

    def test_reports_unreachable_then_recovers(self):
        self.write_config()
        attempts = 0

        async def connector(_config, status, _inventory, stop_event):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise OSError("bridge is offline")
            status("connected")
            while not stop_event.is_set():
                await asyncio.sleep(0.01)

        self.start_adapter(connector)
        self.wait_for("unreachable")
        self.wait_for("connected")

        self.assertGreaterEqual(attempts, 2)

    def test_reports_rejected_authentication(self):
        self.write_config()

        async def connector(*_args):
            raise HueAuthenticationError

        self.start_adapter(connector)
        self.wait_for("unauthorized")

        self.assertIn("unauthorized", self.statuses)
        self.assertNotIn("unreachable", self.statuses)

    def test_reports_event_interruption_and_recovery(self):
        self.write_config()

        async def connector(_config, status, _inventory, stop_event):
            status("connected")
            status("event_interrupted")
            status("connected")
            while not stop_event.is_set():
                await asyncio.sleep(0.01)

        self.start_adapter(connector)
        self.wait_for("event_interrupted")
        self.wait_for("connected")

        self.assertEqual(
            self.statuses[:4],
            ["connecting", "connected", "event_interrupted", "connected"],
        )


class HueInventoryTests(unittest.TestCase):
    def test_summarizes_remote_capabilities_without_resource_ids(self):
        device = SimpleNamespace(
            id="device-secret-id",
            metadata=SimpleNamespace(name="Office remote"),
            product_data=SimpleNamespace(
                product_name="Hue dimmer switch",
                model_id="RWL022",
            ),
        )
        button = SimpleNamespace(
            id="button-secret-id",
            metadata=SimpleNamespace(control_id=1),
            button=SimpleNamespace(
                event_values=[
                    SimpleNamespace(value="short_release"),
                    SimpleNamespace(value="initial_press"),
                ]
            ),
        )
        button_controller = SimpleNamespace(
            items=[button],
            get_device=lambda _button_id: device,
        )
        bridge = SimpleNamespace(
            host="bridge-secret.local",
            groups=SimpleNamespace(
                room=SimpleNamespace(
                    items=[
                        SimpleNamespace(
                            id="room-secret-id",
                            metadata=SimpleNamespace(name="Office"),
                        )
                    ]
                )
            ),
            scenes=SimpleNamespace(
                items=[
                    SimpleNamespace(
                        id="scene-secret-id",
                        metadata=SimpleNamespace(name="Read"),
                    )
                ]
            ),
            sensors=SimpleNamespace(button=button_controller),
        )

        inventory = summarize_v2(bridge)
        encoded = json.dumps(inventory)

        self.assertEqual(inventory["generation"], "v2")
        self.assertEqual(inventory["rooms"], ["Office"])
        self.assertEqual(inventory["scenes"], ["Read"])
        self.assertEqual(inventory["remotes"][0]["model"], "RWL022")
        self.assertEqual(
            inventory["remotes"][0]["controls"][0]["events"],
            ["initial_press", "short_release"],
        )
        self.assertNotIn("secret", encoded)


if __name__ == "__main__":
    unittest.main()
