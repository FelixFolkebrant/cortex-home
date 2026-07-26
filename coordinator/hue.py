import asyncio
import json
import re
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


CONFIG_KEYS = {"app_key", "bridge_id", "host", "supports_v2"}
HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]+$")
ROOM_NAME = "Rum"
HUE_STATUSES = {
    "connected",
    "connecting",
    "event_interrupted",
    "invalid_configuration",
    "unauthorized",
    "unconfigured",
    "unreachable",
}


class HueAuthenticationError(Exception):
    pass


class HueConfigurationError(Exception):
    pass


class HueSceneError(Exception):
    pass


class HueSceneTimeout(Exception):
    pass


class HueSceneUnavailable(Exception):
    pass


@dataclass(frozen=True)
class HueConfig:
    host: str
    app_key: str
    bridge_id: str
    supports_v2: bool


def load_config(path):
    try:
        payload = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HueConfigurationError from error

    if (
        not isinstance(payload, dict)
        or set(payload) != CONFIG_KEYS
        or not isinstance(payload["host"], str)
        or not HOST_PATTERN.fullmatch(payload["host"])
        or not isinstance(payload["app_key"], str)
        or not payload["app_key"]
        or not isinstance(payload["bridge_id"], str)
        or not payload["bridge_id"]
        or payload["supports_v2"] is not True
    ):
        raise HueConfigurationError

    return HueConfig(**payload)


def summarize_v2(bridge):
    rooms = sorted(room.metadata.name for room in bridge.groups.room.items)
    scenes = sorted(scene.metadata.name for scene in bridge.scenes.items)
    remotes = {}

    for button in bridge.sensors.button.items:
        device = bridge.sensors.button.get_device(button.id)
        if device is None:
            continue

        key = (
            device.metadata.name,
            device.product_data.product_name,
            device.product_data.model_id,
        )
        feature = button.button
        events = feature.event_values if feature else None
        remotes.setdefault(key, []).append(
            {
                "control": button.metadata.control_id,
                "events": sorted(
                    event.value for event in events or [] if event.value != "unknown"
                ),
            }
        )

    return {
        "generation": "v2",
        "rooms": rooms,
        "scenes": scenes,
        "remotes": [
            {
                "name": name,
                "product": product,
                "model": model,
                "controls": sorted(controls, key=lambda item: item["control"]),
            }
            for (name, product, model), controls in sorted(remotes.items())
        ],
    }


def unavailable_lighting():
    return {
        "status": "unavailable",
        "scenes": [],
        "activeScenes": [],
    }


def resolve_scenes(bridge):
    rooms = [
        room
        for room in bridge.groups.room.items
        if room.metadata.name == ROOM_NAME
    ]
    if len(rooms) != 1:
        return None

    scenes = [
        scene
        for scene in bridge.scenes.items
        if scene.group.rid == rooms[0].id
    ]
    names = [getattr(scene.metadata, "name", None) for scene in scenes]
    folded_names = [
        name.casefold() for name in names if isinstance(name, str) and name
    ]
    if (
        not scenes
        or len(folded_names) != len(scenes)
        or len(set(folded_names)) != len(folded_names)
    ):
        return None

    return sorted(scenes, key=lambda scene: scene.metadata.name.casefold())


def is_scene_active(scene):
    active = getattr(getattr(scene, "status", None), "active", None)
    value = getattr(active, "value", active)
    return value in {"static", "dynamic_palette"}


class HueSceneControl:
    def __init__(
        self,
        bridge,
        publish_lighting,
        publish_activator=lambda _activator: None,
    ):
        self.bridge = bridge
        self.publish_lighting = publish_lighting
        self.publish_activator = publish_activator
        self.loop = asyncio.get_running_loop()
        self.waiters = {}
        self.scenes = {}
        self.available = False

    def observe(self, _event_type, _scene):
        self.refresh()

    def refresh(self):
        scenes = resolve_scenes(self.bridge)
        if scenes is None:
            self.unavailable()
            return

        self.scenes = {scene.metadata.name: scene for scene in scenes}
        self.available = True
        active_scenes = [
            name for name, scene in self.scenes.items() if is_scene_active(scene)
        ]
        self.publish_lighting(
            {
                "status": "available",
                "scenes": list(self.scenes),
                "activeScenes": active_scenes,
            }
        )
        self.publish_activator(self.activate)

        for observation, target in tuple(self.waiters.items()):
            if observation.done():
                continue
            if target not in self.scenes:
                observation.set_exception(HueSceneUnavailable())
            elif target in active_scenes:
                observation.set_result(None)

    def unavailable(self):
        self.available = False
        self.scenes = {}
        self.publish_activator(None)
        self.publish_lighting(unavailable_lighting())
        for observation in tuple(self.waiters):
            if not observation.done():
                observation.set_exception(HueSceneUnavailable())

    async def activate_async(self, scene_name, timeout):
        scene = self.scenes.get(scene_name)
        if not self.available or scene is None:
            raise HueSceneUnavailable

        observation = self.loop.create_future()
        self.waiters[observation] = scene_name
        try:
            try:
                async with asyncio.timeout(timeout):
                    try:
                        await self.bridge.scenes.recall(scene.id)
                    except asyncio.CancelledError:
                        raise
                    except Exception as error:
                        observation.cancel()
                        raise HueSceneError from error
                    await observation
            except TimeoutError as error:
                raise HueSceneTimeout from error
        finally:
            self.waiters.pop(observation, None)
            if not observation.done():
                observation.cancel()

    def activate(self, scene_name, timeout):
        future = asyncio.run_coroutine_threadsafe(
            self.activate_async(scene_name, timeout),
            self.loop,
        )
        try:
            future.result(timeout=timeout + 1)
        except FutureTimeoutError as error:
            future.cancel()
            raise HueSceneTimeout from error


async def connect_hue(
    config,
    publish_status,
    publish_inventory,
    publish_lighting,
    publish_activator,
    stop_event,
):
    from aiohue import HueBridgeV2
    from aiohue.errors import Unauthorized
    from aiohue.util import normalize_bridge_id
    from aiohue.v2.controllers.events import EventType

    bridge = HueBridgeV2(config.host, config.app_key)
    scene_control = None

    try:
        def handle_connection(event_type, _data):
            if event_type == EventType.DISCONNECTED:
                publish_status("event_interrupted")
                if scene_control:
                    scene_control.unavailable()
            elif event_type in {EventType.CONNECTED, EventType.RECONNECTED}:
                if scene_control:
                    scene_control.refresh()
                publish_status("connected")

        bridge.events.subscribe(
            handle_connection,
            (
                EventType.CONNECTED,
                EventType.DISCONNECTED,
                EventType.RECONNECTED,
            ),
        )

        await bridge.initialize()
        if normalize_bridge_id(bridge.bridge_id) != config.bridge_id:
            raise HueConfigurationError

        publish_inventory(summarize_v2(bridge))
        scene_control = HueSceneControl(
            bridge,
            publish_lighting,
            publish_activator,
        )
        bridge.scenes.subscribe(scene_control.observe)
        scene_control.refresh()
        if bridge.events.connected:
            publish_status("connected")

        while not stop_event.is_set():
            await asyncio.sleep(0.2)
    except Unauthorized as error:
        raise HueAuthenticationError from error
    finally:
        publish_activator(None)
        if scene_control:
            scene_control.unavailable()
        else:
            publish_lighting(unavailable_lighting())
        with suppress(Exception):
            await bridge.close()


class HueAdapter:
    def __init__(
        self,
        config_path,
        on_status,
        on_lighting=lambda _status: None,
        connector=connect_hue,
        retry_seconds=2,
    ):
        self.config_path = Path(config_path)
        self.on_status = on_status
        self.on_lighting = on_lighting
        self.connector = connector
        self.retry_seconds = retry_seconds
        self.stop_event = threading.Event()
        self.thread = None
        self.lock = threading.Lock()
        self.status = "unconfigured"
        self.inventory = None
        self.lighting = unavailable_lighting()
        self.activator = None

    def start(self):
        if self.thread is not None:
            raise RuntimeError("Hue adapter already started")
        self.thread = threading.Thread(target=self._run, name="hue-adapter")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=max(self.retry_seconds + 1, 2))
            if self.thread.is_alive():
                raise RuntimeError("Hue adapter did not stop")

    def snapshot(self):
        with self.lock:
            return {
                "status": self.status,
                "inventory": self.inventory,
                "lighting": self.lighting,
            }

    def activate_scene(self, scene_name, timeout):
        with self.lock:
            activator = self.activator
            available = self.status == "connected" and activator is not None
        if not available:
            raise HueSceneUnavailable
        activator(scene_name, timeout)

    def _publish_status(self, status):
        if status not in HUE_STATUSES:
            raise ValueError(f"Unknown Hue status: {status}")
        with self.lock:
            self.status = status
            if status != "connected":
                self.activator = None
        self.on_status(status)
        if status != "connected":
            self._publish_lighting(unavailable_lighting())

    def _publish_inventory(self, inventory):
        with self.lock:
            self.inventory = inventory

    def _publish_lighting(self, lighting):
        scenes = lighting.get("scenes") if isinstance(lighting, dict) else None
        active_scenes = (
            lighting.get("activeScenes") if isinstance(lighting, dict) else None
        )
        if (
            not isinstance(lighting, dict)
            or set(lighting) != {"status", "scenes", "activeScenes"}
            or lighting["status"] not in {"available", "unavailable"}
            or not isinstance(scenes, list)
            or not all(isinstance(scene, str) and scene for scene in scenes)
            or scenes != sorted(scenes, key=str.casefold)
            or len({scene.casefold() for scene in scenes}) != len(scenes)
            or not isinstance(active_scenes, list)
            or not all(isinstance(scene, str) for scene in active_scenes)
            or active_scenes
            != [scene for scene in scenes if scene in active_scenes]
            or (
                lighting["status"] == "unavailable"
                and (scenes or active_scenes)
            )
            or (
                lighting["status"] == "available"
                and not scenes
            )
        ):
            raise ValueError("Invalid Hue lighting snapshot")
        with self.lock:
            if lighting == self.lighting:
                return
            self.lighting = {
                "status": lighting["status"],
                "scenes": list(lighting["scenes"]),
                "activeScenes": list(lighting["activeScenes"]),
            }
        self.on_lighting(self.lighting)

    def _publish_activator(self, activator):
        with self.lock:
            self.activator = activator

    def _run(self):
        try:
            config = load_config(self.config_path)
        except FileNotFoundError:
            self._publish_status("unconfigured")
            return
        except HueConfigurationError:
            self._publish_status("invalid_configuration")
            return

        while not self.stop_event.is_set():
            self._publish_status("connecting")
            try:
                asyncio.run(
                    self.connector(
                        config,
                        self._publish_status,
                        self._publish_inventory,
                        self._publish_lighting,
                        self._publish_activator,
                        self.stop_event,
                    )
                )
            except HueAuthenticationError:
                self._publish_status("unauthorized")
            except HueConfigurationError:
                self._publish_status("invalid_configuration")
            except Exception:
                self._publish_status("unreachable")

            if not self.stop_event.wait(self.retry_seconds):
                continue
            break
