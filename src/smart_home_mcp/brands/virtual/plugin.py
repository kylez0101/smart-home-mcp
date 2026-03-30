import json
from pathlib import Path
from typing import Any

import yaml

from smart_home_mcp.config import get_brand_config
from smart_home_mcp.models import Device, DeviceState
from smart_home_mcp.plugin_base import BrandPlugin, ToolDefinition

from .device_store import VirtualDeviceStore


def _format(data: dict | list) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


class VirtualPlugin(BrandPlugin):

    @property
    def brand_name(self) -> str:
        return "virtual"

    def __init__(self):
        cfg = get_brand_config("VIRTUAL")
        devices_file = cfg.get("DEVICES_FILE", "")
        if not devices_file:
            devices_file = str(Path(__file__).parent / "devices.yaml")

        with open(devices_file) as f:
            data = yaml.safe_load(f)

        self._store = VirtualDeviceStore(data["devices"])

    # --- Generic interface (used by control_device) ---

    def get_devices(self) -> list[Device]:
        return self._store.list_devices()

    def get_state(self, device_id: str) -> DeviceState:
        return self._store.get_state(device_id)

    def control(self, device_id: str, capability: str, value: Any) -> DeviceState:
        return self._store.control(device_id, capability, value)

    # --- Brand-specific MCP tools ---

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="virtual_list_devices",
                description="List all virtual devices and their types/capabilities.",
                fn=self._list_devices,
            ),
            ToolDefinition(
                name="virtual_get_status",
                description="Get current state of a virtual device.",
                fn=self._get_status,
            ),
            ToolDefinition(
                name="virtual_turn_on",
                description="Turn on a virtual device.",
                fn=self._turn_on,
            ),
            ToolDefinition(
                name="virtual_turn_off",
                description="Turn off a virtual device.",
                fn=self._turn_off,
            ),
            ToolDefinition(
                name="virtual_set_temperature",
                description="Set temperature of a virtual AC device (16-31°C).",
                fn=self._set_temperature,
            ),
            ToolDefinition(
                name="virtual_set_mode",
                description='Set mode of a virtual AC device. One of "cool", "heat", "auto", "dry", "fan".',
                fn=self._set_mode,
            ),
            ToolDefinition(
                name="virtual_set_fan_speed",
                description='Set fan speed of a virtual AC device. One of "auto", "low", "medium", "high", "full".',
                fn=self._set_fan_speed,
            ),
            ToolDefinition(
                name="virtual_set_brightness",
                description="Set brightness of a virtual light (0-100).",
                fn=self._set_brightness,
            ),
            ToolDefinition(
                name="virtual_set_position",
                description="Set position of a virtual curtain (0=closed, 100=open).",
                fn=self._set_position,
            ),
        ]

    def _control_result(self, device_id: str, capability: str, value) -> str:
        """Control a device and return structured before/after result."""
        try:
            changes, state = self._store.control_with_diff(device_id, capability, value)
            result = {
                "changes": changes,
                "state": state.capabilities,
            }
            return _format(result)
        except Exception as e:
            return f"Error: {e}"

    def _list_devices(self) -> str:
        devices = self._store.list_devices()
        lines = []
        for d in devices:
            caps = ", ".join(c.name for c in d.capabilities)
            lines.append(f"- {d.name} (ID: {d.id}, Type: {d.type}, Capabilities: {caps})")
        return f"Found {len(devices)} virtual device(s):\n" + "\n".join(lines)

    def _get_status(self, device_id: str = "") -> str:
        try:
            state = self._store.get_state(device_id)
            device = self._store.get_device(device_id)
            result = {"device": device.name, "state": state.capabilities}
            return _format(result)
        except Exception as e:
            return f"Error: {e}"

    def _turn_on(self, device_id: str = "") -> str:
        return self._control_result(device_id, "power", True)

    def _turn_off(self, device_id: str = "") -> str:
        return self._control_result(device_id, "power", False)

    def _set_temperature(self, temperature: float, device_id: str = "") -> str:
        return self._control_result(device_id, "temperature", temperature)

    def _set_mode(self, mode: str, device_id: str = "") -> str:
        return self._control_result(device_id, "mode", mode)

    def _set_fan_speed(self, speed: str, device_id: str = "") -> str:
        return self._control_result(device_id, "fan_speed", speed)

    def _set_brightness(self, brightness: int, device_id: str = "") -> str:
        return self._control_result(device_id, "brightness", brightness)

    def _set_position(self, position: int, device_id: str = "") -> str:
        return self._control_result(device_id, "position", position)
