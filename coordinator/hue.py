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
SCENE_NAME = "Warm"
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


def resolve_scene(bridge):
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
        if scene.metadata.name == SCENE_NAME and scene.group.rid == rooms[0].id
    ]
    return scenes[0] if len(scenes) == 1 else None


def normalize_scene_status(scene):
    active = getattr(getattr(scene, "status", None), "active", None)
    value = getattr(active, "value", active)
    return "active" if value in {"static", "dynamic_palette"} else "inactive"


class HueSceneControl:
    def __init__(self, bridge, scene, publish_lighting):
        self.bridge = bridge
        self.scene = scene
        self.publish_lighting = publish_lighting
        self.loop = asyncio.get_running_loop()
        self.waiters = set()
        self.available = True

    def observe(self, event_type, scene):
        if (
            getattr(event_type, "value", event_type) == "delete"
            or scene.metadata.name != SCENE_NAME
            or scene.group.rid != self.scene.group.rid
        ):
            self.unavailable()
            return

        self.available = True
        status = normalize_scene_status(scene)
        self.publish_lighting(status)
        if status == "active":
            for waiter in tuple(self.waiters):
                if not waiter.done():
                    waiter.set_result(None)

    def unavailable(self):
        self.available = False
        self.publish_lighting("unavailable")
        for waiter in tuple(self.waiters):
            if not waiter.done():
                waiter.set_exception(HueSceneUnavailable())

    async def activate_async(self, timeout):
        if not self.available:
            raise HueSceneUnavailable

        observation = self.loop.create_future()
        self.waiters.add(observation)
        try:
            try:
                async with asyncio.timeout(timeout):
                    try:
                        await self.bridge.scenes.recall(self.scene.id)
                    except asyncio.CancelledError:
                        raise
                    except Exception as error:
                        observation.cancel()
                        raise HueSceneError from error
                    await observation
            except TimeoutError as error:
                raise HueSceneTimeout from error
        finally:
            self.waiters.discard(observation)
            if not observation.done():
                observation.cancel()

    def activate(self, timeout):
        future = asyncio.run_coroutine_threadsafe(
            self.activate_async(timeout),
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
                    scene_control.observe(
                        EventType.RESOURCE_UPDATED,
                        scene_control.scene,
                    )
                    if scene_control.available:
                        publish_activator(scene_control.activate)
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
        scene = resolve_scene(bridge)
        if scene:
            scene_control = HueSceneControl(bridge, scene, publish_lighting)
            bridge.scenes.subscribe(scene_control.observe, id_filter=scene.id)
            scene_control.observe(EventType.RESOURCE_UPDATED, scene)
            publish_activator(scene_control.activate)
        else:
            publish_lighting("unavailable")
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
            publish_lighting("unavailable")
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
        self.lighting = "unavailable"
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

    def activate_scene(self, timeout):
        with self.lock:
            activator = self.activator
            available = self.status == "connected" and activator is not None
        if not available:
            raise HueSceneUnavailable
        activator(timeout)

    def _publish_status(self, status):
        if status not in HUE_STATUSES:
            raise ValueError(f"Unknown Hue status: {status}")
        with self.lock:
            self.status = status
            if status != "connected":
                self.activator = None
        self.on_status(status)
        if status != "connected":
            self._publish_lighting("unavailable")

    def _publish_inventory(self, inventory):
        with self.lock:
            self.inventory = inventory

    def _publish_lighting(self, status):
        if status not in {"active", "inactive", "unavailable"}:
            raise ValueError(f"Unknown Hue lighting status: {status}")
        with self.lock:
            if status == self.lighting:
                return
            self.lighting = status
        self.on_lighting(status)

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
