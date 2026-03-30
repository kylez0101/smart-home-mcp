import json
from typing import Any

from smart_home_mcp.config import get_brand_config
from smart_home_mcp.device_cache import load_cache
from smart_home_mcp.models import Capability, Device, DeviceState
from smart_home_mcp.plugin_base import BrandPlugin, ToolDefinition

from .cloud_session import CloudSession
from .device_manager import DeviceManager


def _format(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


# Midea AC capabilities definition
_AC_CAPABILITIES = [
    Capability(name="power", type="bool"),
    Capability(name="temperature", type="float", range={"min": 16, "max": 31, "step": 0.5}),
    Capability(name="mode", type="enum", options=["cool", "heat", "auto", "dry", "fan"]),
    Capability(name="fan_speed", type="enum", options=["auto", "low", "medium", "high", "full"]),
    Capability(name="vertical_swing", type="bool"),
    Capability(name="horizontal_swing", type="bool"),
    Capability(name="eco_mode", type="bool"),
    Capability(name="turbo", type="bool"),
    Capability(name="indoor_temperature", type="float", read_only=True),
    Capability(name="outdoor_temperature", type="float", read_only=True),
]

# Maps generic capability names to DeviceManager methods
_CONTROL_MAP = {
    "power": lambda mgr, did, v: mgr.turn_on(did) if v else mgr.turn_off(did),
    "temperature": lambda mgr, did, v: mgr.set_temperature(v, did),
    "mode": lambda mgr, did, v: mgr.set_mode(v, did),
    "fan_speed": lambda mgr, did, v: mgr.set_fan_speed(v, did),
    "eco_mode": lambda mgr, did, v: mgr.set_eco_mode(v, did),
    "turbo": lambda mgr, did, v: mgr.set_turbo(v, did),
}


class MideaACPlugin(BrandPlugin):

    @property
    def brand_name(self) -> str:
        return "midea_ac"

    def __init__(self):
        cfg = get_brand_config("MIDEA")
        account = cfg.get("ACCOUNT", "")
        password = cfg.get("PASSWORD", "")
        app = cfg.get("APP", "MSmartHome")
        control_mode = cfg.get("CONTROL_MODE", "auto")

        if not account or not password:
            raise ValueError("MIDEA_ACCOUNT and MIDEA_PASSWORD must be set in .env")

        self._cloud = CloudSession(account, password, app)
        self._manager = DeviceManager(self._cloud, control_mode)

    # --- Generic interface ---

    def get_devices(self) -> list[Device]:
        cached = load_cache()
        return [
            Device(
                id=str(d["id"]),
                name=d.get("name", "Midea AC"),
                brand="midea_ac",
                type="ac",
                capabilities=list(_AC_CAPABILITIES),
            )
            for d in cached
        ]

    def get_state(self, device_id: str) -> DeviceState:
        status = self._manager.get_status(device_id)
        return DeviceState(device_id=device_id, capabilities=status)

    def control(self, device_id: str, capability: str, value: Any) -> DeviceState:
        # Validate capability
        cap = next((c for c in _AC_CAPABILITIES if c.name == capability), None)
        if not cap:
            raise ValueError(f"Midea AC does not support '{capability}'")
        if cap.read_only:
            raise ValueError(f"'{capability}' is read-only")

        validated = cap.validate(value)

        # Handle swing separately (needs two params)
        if capability == "vertical_swing":
            self._manager.set_swing(vertical=validated, device_id=device_id)
        elif capability == "horizontal_swing":
            self._manager.set_swing(horizontal=validated, device_id=device_id)
        elif capability in _CONTROL_MAP:
            _CONTROL_MAP[capability](self._manager, device_id, validated)
        else:
            raise ValueError(f"No control handler for '{capability}'")

        return self.get_state(device_id)

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="midea_discover_devices",
                description="Discover Midea AC devices on the local network. "
                "Requires MIDEA_ACCOUNT and MIDEA_PASSWORD configured in .env. "
                "Results are cached locally for subsequent commands.",
                fn=self._discover_devices,
            ),
            ToolDefinition(
                name="midea_get_ac_status",
                description="Get the current status of the Midea air conditioner. "
                "Returns: power state, mode, temperatures, fan speed, and feature states.",
                fn=self._get_ac_status,
            ),
            ToolDefinition(
                name="midea_turn_on",
                description="Turn on the Midea air conditioner.",
                fn=self._turn_on,
            ),
            ToolDefinition(
                name="midea_turn_off",
                description="Turn off the Midea air conditioner.",
                fn=self._turn_off,
            ),
            ToolDefinition(
                name="midea_set_temperature",
                description="Set the target temperature of the Midea air conditioner (16-31°C).",
                fn=self._set_temperature,
            ),
            ToolDefinition(
                name="midea_set_mode",
                description='Set the operating mode of the Midea air conditioner. '
                'One of "cool", "heat", "auto", "dry", "fan".',
                fn=self._set_mode,
            ),
            ToolDefinition(
                name="midea_set_fan_speed",
                description='Set the fan speed of the Midea air conditioner. '
                'One of "auto", "low", "medium", "high", "full".',
                fn=self._set_fan_speed,
            ),
            ToolDefinition(
                name="midea_set_swing",
                description="Control swing/oscillation of the Midea air conditioner.",
                fn=self._set_swing,
            ),
            ToolDefinition(
                name="midea_set_eco_mode",
                description="Enable or disable eco/energy-saving mode on the Midea air conditioner.",
                fn=self._set_eco_mode,
            ),
            ToolDefinition(
                name="midea_set_turbo",
                description="Enable or disable turbo/powerful mode on the Midea air conditioner.",
                fn=self._set_turbo,
            ),
        ]

    def _discover_devices(self) -> str:
        try:
            devices = self._manager.discover()
            if not devices:
                return "No devices found on the network."
            summary = []
            for d in devices:
                summary.append(
                    f"- {d['name']} (ID: {d['id']}, IP: {d['address']}, Type: {d['type']})"
                )
            return f"Found {len(devices)} device(s):\n" + "\n".join(summary)
        except Exception as e:
            return f"Error discovering devices: {e}"

    def _get_ac_status(self, device_id: str = "") -> str:
        try:
            status = self._manager.get_status(device_id)
            return _format(status)
        except Exception as e:
            return f"Error getting status: {e}"

    def _turn_on(self, device_id: str = "") -> str:
        try:
            status = self._manager.turn_on(device_id)
            return f"AC turned ON.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error turning on: {e}"

    def _turn_off(self, device_id: str = "") -> str:
        try:
            status = self._manager.turn_off(device_id)
            return f"AC turned OFF.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error turning off: {e}"

    def _set_temperature(self, temperature: float, device_id: str = "") -> str:
        try:
            status = self._manager.set_temperature(temperature, device_id)
            return f"Temperature set to {temperature}°C.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error setting temperature: {e}"

    def _set_mode(self, mode: str, device_id: str = "") -> str:
        try:
            status = self._manager.set_mode(mode, device_id)
            return f"Mode set to {mode}.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error setting mode: {e}"

    def _set_fan_speed(self, speed: str, device_id: str = "") -> str:
        try:
            status = self._manager.set_fan_speed(speed, device_id)
            return f"Fan speed set to {speed}.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error setting fan speed: {e}"

    def _set_swing(
        self,
        vertical: bool | None = None,
        horizontal: bool | None = None,
        device_id: str = "",
    ) -> str:
        try:
            status = self._manager.set_swing(vertical, horizontal, device_id)
            return f"Swing updated.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error setting swing: {e}"

    def _set_eco_mode(self, enabled: bool, device_id: str = "") -> str:
        try:
            status = self._manager.set_eco_mode(enabled, device_id)
            state = "enabled" if enabled else "disabled"
            return f"Eco mode {state}.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error setting eco mode: {e}"

    def _set_turbo(self, enabled: bool, device_id: str = "") -> str:
        try:
            status = self._manager.set_turbo(enabled, device_id)
            state = "enabled" if enabled else "disabled"
            return f"Turbo mode {state}.\nCurrent status:\n{_format(status)}"
        except Exception as e:
            return f"Error setting turbo mode: {e}"
