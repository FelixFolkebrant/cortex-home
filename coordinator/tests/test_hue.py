import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys


sys.path.insert(0, str(Path(__file__).parents[1]))

from hue import (
    HueAdapter,
    HueAuthenticationError,
    HueSceneControl,
    HueSceneError,
    HueSceneTimeout,
    HueSceneUnavailable,
    normalize_scene_status,
    resolve_scene,
    summarize_v2,
)


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
        self.lighting = []

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
            self.lighting.append,
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

        async def connector(
            config,
            status,
            publish_inventory,
            _publish_lighting,
            _publish_activator,
            stop_event,
        ):
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

        async def connector(
            _config,
            status,
            _inventory,
            _lighting,
            _activator,
            stop_event,
        ):
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

        async def connector(
            _config,
            status,
            _inventory,
            _lighting,
            _activator,
            stop_event,
        ):
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

    def test_activates_the_resolved_scene_from_the_adapter_thread(self):
        self.write_config()
        scene = make_scene()
        scenes = FakeScenes(scene, emit_on_recall=True)
        bridge = SimpleNamespace(scenes=scenes)

        async def connector(
            _config,
            status,
            _inventory,
            publish_lighting,
            publish_activator,
            stop_event,
        ):
            control = HueSceneControl(bridge, scene, publish_lighting)
            scenes.subscribe(control.observe, id_filter=scene.id)
            control.observe("update", scene)
            publish_activator(control.activate)
            status("connected")
            while not stop_event.is_set():
                await asyncio.sleep(0.01)

        adapter = self.start_adapter(connector)
        self.wait_for("connected")
        adapter.activate_scene(0.1)

        self.assertEqual(scenes.recalled, ["scene-secret-id"])
        self.assertEqual(adapter.snapshot()["lighting"], "active")

    def test_rejects_scene_activation_while_unavailable(self):
        adapter = self.start_adapter(None)
        self.wait_for("unconfigured")

        with self.assertRaises(HueSceneUnavailable):
            adapter.activate_scene(0.1)


def make_scene(name="Warm", group_id="room-secret-id", active="inactive"):
    return SimpleNamespace(
        id="scene-secret-id",
        metadata=SimpleNamespace(name=name),
        group=SimpleNamespace(rid=group_id),
        status=SimpleNamespace(active=SimpleNamespace(value=active)),
    )


class FakeScenes:
    def __init__(self, scene, emit_on_recall=False, error=None, delay=0):
        self.items = [scene]
        self.scene = scene
        self.emit_on_recall = emit_on_recall
        self.error = error
        self.delay = delay
        self.callback = None
        self.recalled = []

    def subscribe(self, callback, id_filter=None):
        self.callback = callback
        self.id_filter = id_filter

    async def recall(self, scene_id):
        self.recalled.append(scene_id)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        if self.emit_on_recall:
            self.scene.status.active.value = "static"
            self.callback("update", self.scene)


class HueSceneTests(unittest.TestCase):
    def make_bridge(self, rooms=None, scenes=None):
        if rooms is None:
            rooms = [
                SimpleNamespace(
                    id="room-secret-id",
                    metadata=SimpleNamespace(name="Rum"),
                )
            ]
        if scenes is None:
            scenes = [make_scene()]
        return SimpleNamespace(
            groups=SimpleNamespace(
                room=SimpleNamespace(items=rooms)
            ),
            scenes=SimpleNamespace(items=scenes),
        )

    def test_resolves_one_warm_scene_belonging_to_rum(self):
        scene = make_scene()

        self.assertIs(resolve_scene(self.make_bridge(scenes=[scene])), scene)

    def test_rejects_missing_ambiguous_and_wrong_room_targets(self):
        cases = [
            self.make_bridge(rooms=[]),
            self.make_bridge(
                rooms=[
                    SimpleNamespace(
                        id="room-secret-id",
                        metadata=SimpleNamespace(name="Rum"),
                    ),
                    SimpleNamespace(
                        id="other-room-id",
                        metadata=SimpleNamespace(name="Rum"),
                    ),
                ]
            ),
            self.make_bridge(scenes=[make_scene(name="Relax")]),
            self.make_bridge(scenes=[make_scene(group_id="other-room-id")]),
            self.make_bridge(scenes=[make_scene(), make_scene()]),
        ]

        for bridge in cases:
            with self.subTest(bridge=bridge):
                self.assertIsNone(resolve_scene(bridge))

    def test_normalizes_only_static_and_dynamic_scene_status_as_active(self):
        self.assertEqual(normalize_scene_status(make_scene(active="static")), "active")
        self.assertEqual(
            normalize_scene_status(make_scene(active="dynamic_palette")),
            "active",
        )
        self.assertEqual(normalize_scene_status(make_scene()), "inactive")
        self.assertEqual(
            normalize_scene_status(SimpleNamespace(status=None)),
            "inactive",
        )

    def test_completes_from_a_later_active_observation(self):
        async def exercise():
            scene = make_scene()
            scenes = FakeScenes(scene)
            lighting = []
            control = HueSceneControl(
                SimpleNamespace(scenes=scenes),
                scene,
                lighting.append,
            )
            scenes.subscribe(control.observe, id_filter=scene.id)
            control.observe("update", scene)

            activation = asyncio.create_task(control.activate_async(0.1))
            await asyncio.sleep(0)
            scene.status.active.value = "static"
            scenes.callback("update", scene)
            await activation

            self.assertEqual(lighting, ["inactive", "active"])
            self.assertEqual(scenes.recalled, ["scene-secret-id"])

        asyncio.run(exercise())

    def test_requires_a_new_observation_when_the_scene_is_already_active(self):
        async def exercise():
            scene = make_scene(active="static")
            scenes = FakeScenes(scene, emit_on_recall=True)
            control = HueSceneControl(
                SimpleNamespace(scenes=scenes),
                scene,
                lambda _status: None,
            )
            scenes.subscribe(control.observe, id_filter=scene.id)
            control.observe("update", scene)

            await control.activate_async(0.1)

            self.assertEqual(scenes.recalled, ["scene-secret-id"])

        asyncio.run(exercise())

    def test_times_out_without_an_active_observation(self):
        async def exercise():
            scene = make_scene()
            control = HueSceneControl(
                SimpleNamespace(scenes=FakeScenes(scene)),
                scene,
                lambda _status: None,
            )

            with self.assertRaises(HueSceneTimeout):
                await control.activate_async(0.01)

        asyncio.run(exercise())

    def test_timeout_includes_the_recall_request(self):
        async def exercise():
            scene = make_scene()
            control = HueSceneControl(
                SimpleNamespace(scenes=FakeScenes(scene, delay=0.1)),
                scene,
                lambda _status: None,
            )

            with self.assertRaises(HueSceneTimeout):
                await control.activate_async(0.01)

        asyncio.run(exercise())

    def test_reports_recall_failure(self):
        async def exercise():
            scene = make_scene()
            control = HueSceneControl(
                SimpleNamespace(
                    scenes=FakeScenes(scene, error=OSError("rejected"))
                ),
                scene,
                lambda _status: None,
            )

            with self.assertRaises(HueSceneError):
                await control.activate_async(0.1)

        asyncio.run(exercise())

    def test_interruption_fails_pending_activation_and_recovers_observation(self):
        async def exercise():
            scene = make_scene()
            scenes = FakeScenes(scene)
            lighting = []
            control = HueSceneControl(
                SimpleNamespace(scenes=scenes),
                scene,
                lighting.append,
            )

            activation = asyncio.create_task(control.activate_async(0.1))
            await asyncio.sleep(0)
            control.unavailable()
            with self.assertRaises(HueSceneUnavailable):
                await activation

            scene.status.active.value = "static"
            control.observe("update", scene)
            self.assertTrue(control.available)
            self.assertEqual(lighting, ["unavailable", "active"])

        asyncio.run(exercise())


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
