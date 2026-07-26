#!/usr/bin/env python3

import argparse
import asyncio
import grp
import json
import os
from contextlib import suppress
from pathlib import Path

from hue import HOST_PATTERN, summarize_v2


CONFIG_PATH = Path("/etc/cortex-home/hue.json")
OBSERVATION_SECONDS = 60


def write_config(bridge, app_key):
    CONFIG_PATH.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    os.chown(CONFIG_PATH.parent, 0, grp.getgrnam("cortex-home").gr_gid)
    os.chmod(CONFIG_PATH.parent, 0o750)

    payload = {
        "host": bridge.host,
        "app_key": app_key,
        "bridge_id": bridge.id,
        "supports_v2": bridge.supports_v2,
    }
    descriptor = os.open(
        CONFIG_PATH,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o640,
    )
    try:
        os.fchown(descriptor, 0, grp.getgrnam("cortex-home").gr_gid)
        with os.fdopen(descriptor, "w") as config_file:
            json.dump(payload, config_file)
            config_file.write("\n")
    except BaseException:
        CONFIG_PATH.unlink(missing_ok=True)
        raise


def print_inventory(inventory):
    print(f"Bridge generation: {inventory['generation']}")
    print("Rooms: " + (", ".join(inventory["rooms"]) or "none"))
    print("Scenes: " + (", ".join(inventory["scenes"]) or "none"))
    if not inventory["remotes"]:
        print("Remotes: none")
        return

    print("Remotes:")
    for remote in inventory["remotes"]:
        print(
            f"  {remote['name']} — {remote['product']} ({remote['model']})"
        )
        for control in remote["controls"]:
            events = ", ".join(control["events"]) or "not advertised"
            print(f"    control {control['control']}: {events}")


async def observe_remote_events(bridge):
    from aiohue.v2.controllers.events import EventType

    def handle_button(event_type, button):
        if event_type != EventType.RESOURCE_UPDATED or button.button is None:
            return
        device = bridge.sensors.button.get_device(button.id)
        if device is None:
            return
        print(
            f"  {device.product_data.model_id} control "
            f"{button.metadata.control_id}: {button.button.value.value}",
            flush=True,
        )

    bridge.sensors.button.subscribe(
        handle_button,
        event_filter=EventType.RESOURCE_UPDATED,
    )
    print(
        f"Use every intended remote press now; observing for "
        f"{OBSERVATION_SECONDS} seconds."
    )
    await asyncio.sleep(OBSERVATION_SECONDS)


async def pair(host):
    from aiohue import HueBridgeV2, create_app_key
    from aiohue.discovery import discover_bridge
    from aiohue.util import normalize_bridge_id

    bridge_details = await discover_bridge(host)
    if not bridge_details.supports_v2:
        raise SystemExit(
            "This bridge cannot expose the accepted V2 resources and events."
        )

    input("Press the Hue bridge link button, then press Enter here: ")
    app_key = await create_app_key(host, "Cortex Home")
    bridge = HueBridgeV2(host, app_key)

    try:
        await bridge.initialize()
        if normalize_bridge_id(bridge.bridge_id) != bridge_details.id:
            raise RuntimeError("The connected bridge identity changed.")

        inventory = summarize_v2(bridge)
        write_config(bridge_details, app_key)
        print("Hue pairing credential stored.")
        print_inventory(inventory)
        if inventory["remotes"]:
            await observe_remote_events(bridge)
    finally:
        with suppress(Exception):
            await bridge.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("bridge_host")
    args = parser.parse_args()
    if not HOST_PATTERN.fullmatch(args.bridge_host):
        parser.error("bridge_host must be an IPv4 address or local hostname")
    return args


def main():
    args = parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Run Hue pairing as root.")
    if CONFIG_PATH.exists():
        raise SystemExit(
            "Hue is already paired. Remove the protected credential deliberately "
            "before pairing again."
        )

    asyncio.run(pair(args.bridge_host))


if __name__ == "__main__":
    main()
