import json

from mcp.server.fastmcp import FastMCP

from .cloud_session import CloudSession
from .config import MIDEA_ACCOUNT, MIDEA_APP, MIDEA_CONTROL_MODE, MIDEA_PASSWORD
from .device_manager import DeviceManager

mcp = FastMCP(
    "midea-ac",
    instructions="Control Midea smart air conditioners via local LAN and cloud.",
)

cloud_session = CloudSession(MIDEA_ACCOUNT, MIDEA_PASSWORD, MIDEA_APP)
manager = DeviceManager(cloud_session, MIDEA_CONTROL_MODE)


def _format(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
def discover_devices() -> str:
    """Discover Midea AC devices on the local network.
    Requires MIDEA_ACCOUNT and MIDEA_PASSWORD configured in .env.
    Results are cached locally for subsequent commands.
    """
    try:
        devices = manager.discover()
        if not devices:
            return "No devices found on the network."
        summary = []
        for d in devices:
            summary.append(f"- {d['name']} (ID: {d['id']}, IP: {d['address']}, Type: {d['type']})")
        return f"Found {len(devices)} device(s):\n" + "\n".join(summary)
    except Exception as e:
        return f"Error discovering devices: {e}"


@mcp.tool()
def get_ac_status(device_id: str = "") -> str:
    """Get the current status of the air conditioner.
    Returns: power state, mode, temperatures, fan speed, and feature states.
    Args:
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.get_status(device_id)
        return _format(status)
    except Exception as e:
        return f"Error getting status: {e}"


@mcp.tool()
def turn_on(device_id: str = "") -> str:
    """Turn on the air conditioner.
    Args:
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.turn_on(device_id)
        return f"AC turned ON.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error turning on: {e}"


@mcp.tool()
def turn_off(device_id: str = "") -> str:
    """Turn off the air conditioner.
    Args:
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.turn_off(device_id)
        return f"AC turned OFF.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error turning off: {e}"


@mcp.tool()
def set_temperature(temperature: float, device_id: str = "") -> str:
    """Set the target temperature of the air conditioner (16-31°C).
    Args:
        temperature: Target temperature in Celsius (16-31, supports 0.5 increments).
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.set_temperature(temperature, device_id)
        return f"Temperature set to {temperature}°C.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error setting temperature: {e}"


@mcp.tool()
def set_mode(mode: str, device_id: str = "") -> str:
    """Set the operating mode of the air conditioner.
    Args:
        mode: One of "cool", "heat", "auto", "dry", "fan".
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.set_mode(mode, device_id)
        return f"Mode set to {mode}.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error setting mode: {e}"


@mcp.tool()
def set_fan_speed(speed: str, device_id: str = "") -> str:
    """Set the fan speed of the air conditioner.
    Args:
        speed: One of "auto", "low", "medium", "high", "full".
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.set_fan_speed(speed, device_id)
        return f"Fan speed set to {speed}.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error setting fan speed: {e}"


@mcp.tool()
def set_swing(
    vertical: bool | None = None,
    horizontal: bool | None = None,
    device_id: str = "",
) -> str:
    """Control swing/oscillation of the air conditioner.
    Args:
        vertical: Enable or disable vertical swing. Pass null to leave unchanged.
        horizontal: Enable or disable horizontal swing. Pass null to leave unchanged.
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.set_swing(vertical, horizontal, device_id)
        return f"Swing updated.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error setting swing: {e}"


@mcp.tool()
def set_eco_mode(enabled: bool, device_id: str = "") -> str:
    """Enable or disable eco/energy-saving mode.
    Args:
        enabled: True to enable, False to disable.
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.set_eco_mode(enabled, device_id)
        state = "enabled" if enabled else "disabled"
        return f"Eco mode {state}.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error setting eco mode: {e}"


@mcp.tool()
def set_turbo(enabled: bool, device_id: str = "") -> str:
    """Enable or disable turbo/powerful mode.
    Args:
        enabled: True to enable, False to disable.
        device_id: Optional device ID. Defaults to the first cached device.
    """
    try:
        status = manager.set_turbo(enabled, device_id)
        state = "enabled" if enabled else "disabled"
        return f"Turbo mode {state}.\nCurrent status:\n{_format(status)}"
    except Exception as e:
        return f"Error setting turbo mode: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
