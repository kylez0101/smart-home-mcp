import json
import logging
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from .brands import PLUGIN_CLASSES
from .home_config import load_home_config
from .home_plugin import HomePlugin
from .plugin_base import BrandPlugin

_LOGGER = logging.getLogger(__name__)

mcp = FastMCP(
    "smart-home",
    instructions="Control smart home devices from multiple brands.",
)

_tool_registry: dict[str, Callable[..., Any]] = {}
_plugins: list[BrandPlugin] = []
_device_plugin_map: dict[str, BrandPlugin] = {}  # device_id -> plugin


def _rebuild_device_map() -> None:
    """Rebuild the device->plugin mapping from all loaded plugins."""
    _device_plugin_map.clear()
    for plugin in _plugins:
        try:
            for device in plugin.get_devices():
                _device_plugin_map[device.id] = plugin
        except Exception:
            pass


def _fmt(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


# --- Generic MCP tools ---


def _list_devices(brand: str = "", type: str = "") -> str:
    """List all known devices across all brands. Optionally filter by brand or device type."""
    _rebuild_device_map()
    all_devices = []
    for plugin in _plugins:
        try:
            for device in plugin.get_devices():
                if brand and device.brand != brand:
                    continue
                if type and device.type != type:
                    continue
                all_devices.append(device.to_dict())
        except Exception as e:
            all_devices.append({"error": f"{plugin.brand_name}: {e}"})

    if not all_devices:
        return "No devices found. Run discover_devices for your brand first."
    return _fmt(all_devices)


def _get_device_state(device_id: str) -> str:
    """Get the current state of any device by its ID."""
    _rebuild_device_map()
    plugin = _device_plugin_map.get(device_id)
    if not plugin:
        return f"Error: Device '{device_id}' not found. Run list_devices to see available devices."
    try:
        state = plugin.get_state(device_id)
        return _fmt(state.capabilities)
    except Exception as e:
        return f"Error getting state: {e}"


def _control_device(device_id: str, capability: str, value: Any) -> str:
    """Control any device by setting a capability value.
    Args:
        device_id: The device ID to control.
        capability: The capability to set (e.g. "power", "temperature", "brightness").
        value: The value to set (e.g. true, 25.0, "cool").
    """
    _rebuild_device_map()
    plugin = _device_plugin_map.get(device_id)
    if not plugin:
        return f"Error: Device '{device_id}' not found. Run list_devices to see available devices."
    try:
        state = plugin.control(device_id, capability, value)
        return f"Set {capability}={value} on {device_id}.\n{_fmt(state.capabilities)}"
    except Exception as e:
        return f"Error: {e}"


def _load_plugins() -> None:
    # Load brand plugins
    for plugin_cls in PLUGIN_CLASSES:
        try:
            plugin = plugin_cls()
            _plugins.append(plugin)
            tools = plugin.get_tools()
            for tool_def in tools:
                mcp.add_tool(
                    fn=tool_def.fn,
                    name=tool_def.name,
                    description=tool_def.description,
                )
                _tool_registry[tool_def.name] = tool_def.fn
            _LOGGER.info(
                "Loaded plugin: %s (%d tools)", plugin.brand_name, len(tools)
            )
        except Exception:
            _LOGGER.exception("Failed to load plugin: %s", plugin_cls.__name__)

    # Register generic tools
    mcp.add_tool(fn=_list_devices, name="list_devices", description="List all known devices across all brands. Optionally filter by brand or device type.")
    mcp.add_tool(fn=_get_device_state, name="get_device_state", description="Get the current state of any device by its ID.")
    mcp.add_tool(fn=_control_device, name="control_device", description="Control any device by setting a capability value (e.g. power, temperature, brightness, mode).")

    # Build device map
    _rebuild_device_map()

    # Load home config (rooms + scenes)
    home_config = load_home_config()
    if home_config is not None:
        home_plugin = HomePlugin(home_config, _tool_registry)
        for tool_def in home_plugin.get_tools():
            mcp.add_tool(
                fn=tool_def.fn,
                name=tool_def.name,
                description=tool_def.description,
            )
        _LOGGER.info(
            "Loaded home config: %d rooms, %d scenes",
            len(home_config.rooms),
            len(home_config.scenes),
        )


_load_plugins()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
