import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_LOGGER = logging.getLogger(__name__)

_project_root = Path(__file__).parent.parent.parent
HOME_YAML = _project_root / "home.yaml"


@dataclass
class DeviceRef:
    id: str
    brand: str
    alias: str


@dataclass
class Room:
    name: str
    display_name: str
    devices: list[DeviceRef]


@dataclass
class SceneAction:
    alias: str
    tool: str
    params: dict


@dataclass
class Scene:
    name: str
    display_name: str
    actions: list[SceneAction]


@dataclass
class HomeConfig:
    rooms: list[Room]
    scenes: list[Scene]
    alias_map: dict[str, DeviceRef] = field(default_factory=dict)


def load_home_config() -> HomeConfig | None:
    """Load home.yaml from project root. Returns None if file does not exist."""
    if not HOME_YAML.exists():
        _LOGGER.info("No home.yaml found, skipping home config.")
        return None

    with open(HOME_YAML) as f:
        data = yaml.safe_load(f)

    if not data:
        return None

    alias_map: dict[str, DeviceRef] = {}
    rooms: list[Room] = []

    for room_name, room_data in (data.get("rooms") or {}).items():
        devices: list[DeviceRef] = []
        for dev in room_data.get("devices", []):
            ref = DeviceRef(id=dev["id"], brand=dev["brand"], alias=dev["alias"])
            if ref.alias in alias_map:
                raise ValueError(f"Duplicate device alias: '{ref.alias}'")
            alias_map[ref.alias] = ref
            devices.append(ref)
        rooms.append(Room(
            name=room_name,
            display_name=room_data.get("display_name", room_name),
            devices=devices,
        ))

    scenes: list[Scene] = []
    for scene_name, scene_data in (data.get("scenes") or {}).items():
        actions: list[SceneAction] = []
        for act in scene_data.get("actions", []):
            actions.append(SceneAction(
                alias=act["alias"],
                tool=act["tool"],
                params=act.get("params", {}),
            ))
        scenes.append(Scene(
            name=scene_name,
            display_name=scene_data.get("display_name", scene_name),
            actions=actions,
        ))

    _LOGGER.info("Loaded home.yaml: %d rooms, %d scenes", len(rooms), len(scenes))
    return HomeConfig(rooms=rooms, scenes=scenes, alias_map=alias_map)
