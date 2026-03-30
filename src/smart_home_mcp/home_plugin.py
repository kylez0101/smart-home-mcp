from typing import Any, Callable

from .home_config import HomeConfig
from .plugin_base import ToolDefinition


class HomePlugin:
    """Provides MCP tools for home layout and scene management."""

    def __init__(self, config: HomeConfig, tool_registry: dict[str, Callable[..., Any]]):
        self._config = config
        self._tool_registry = tool_registry

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="home_list_rooms",
                description="List all rooms in the home and their devices.",
                fn=self._list_rooms,
            ),
            ToolDefinition(
                name="home_list_scenes",
                description="List all available scenes that can be activated.",
                fn=self._list_scenes,
            ),
            ToolDefinition(
                name="home_activate_scene",
                description="Activate a scene by name. Executes all actions defined in the scene.",
                fn=self._activate_scene,
            ),
        ]

    def _list_rooms(self) -> str:
        if not self._config.rooms:
            return "No rooms configured in home.yaml."
        lines = []
        for room in self._config.rooms:
            lines.append(f"## {room.display_name}")
            for dev in room.devices:
                lines.append(f"  - {dev.alias} (ID: {dev.id}, Brand: {dev.brand})")
        return "\n".join(lines)

    def _list_scenes(self) -> str:
        if not self._config.scenes:
            return "No scenes configured in home.yaml."
        lines = []
        for scene in self._config.scenes:
            action_summary = ", ".join(
                f"{a.alias}→{a.tool}" for a in scene.actions
            )
            lines.append(f"- **{scene.display_name}** ({scene.name}): {action_summary}")
        return "\n".join(lines)

    def _activate_scene(self, scene_name: str) -> str:
        scene = None
        for s in self._config.scenes:
            if s.name == scene_name:
                scene = s
                break
        if not scene:
            available = ", ".join(s.name for s in self._config.scenes)
            return f"Scene '{scene_name}' not found. Available: {available}"

        results = []
        for action in scene.actions:
            device_ref = self._config.alias_map.get(action.alias)
            if not device_ref:
                results.append(f"FAIL: Unknown alias '{action.alias}'")
                continue

            fn = self._tool_registry.get(action.tool)
            if not fn:
                results.append(f"FAIL: Tool '{action.tool}' not found")
                continue

            try:
                params = {**action.params, "device_id": device_ref.id}
                result = fn(**params)
                results.append(f"OK: {action.alias} ({action.tool})")
            except Exception as e:
                results.append(f"FAIL: {action.alias} ({action.tool}): {e}")

        header = f"Scene '{scene.display_name}' activated:"
        return header + "\n" + "\n".join(results)
