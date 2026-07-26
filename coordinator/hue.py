import asyncio
import json
import re
import threading
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


CONFIG_KEYS = {"app_key", "bridge_id", "host", "supports_v2"}
HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]+$")
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


async def connect_hue(config, publish_status, publish_inventory, stop_event):
    from aiohue import HueBridgeV2
    from aiohue.errors import Unauthorized
    from aiohue.util import normalize_bridge_id
    from aiohue.v2.controllers.events import EventType

    bridge = HueBridgeV2(config.host, config.app_key)

    try:
        def handle_connection(event_type, _data):
            if event_type == EventType.DISCONNECTED:
                publish_status("event_interrupted")
            elif event_type in {EventType.CONNECTED, EventType.RECONNECTED}:
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
        if bridge.events.connected:
            publish_status("connected")

        while not stop_event.is_set():
            await asyncio.sleep(0.2)
    except Unauthorized as error:
        raise HueAuthenticationError from error
    finally:
        with suppress(Exception):
            await bridge.close()


class HueAdapter:
    def __init__(
        self,
        config_path,
        on_status,
        connector=connect_hue,
        retry_seconds=2,
    ):
        self.config_path = Path(config_path)
        self.on_status = on_status
        self.connector = connector
        self.retry_seconds = retry_seconds
        self.stop_event = threading.Event()
        self.thread = None
        self.lock = threading.Lock()
        self.status = "unconfigured"
        self.inventory = None

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
            return {"status": self.status, "inventory": self.inventory}

    def _publish_status(self, status):
        if status not in HUE_STATUSES:
            raise ValueError(f"Unknown Hue status: {status}")
        with self.lock:
            self.status = status
        self.on_status(status)

    def _publish_inventory(self, inventory):
        with self.lock:
            self.inventory = inventory

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
