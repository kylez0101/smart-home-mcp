from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Capability:
    """A single capability of a device."""

    name: str  # "power", "temperature", "brightness", etc.
    type: str  # "bool", "float", "int", "enum"
    read_only: bool = False
    range: dict | None = None  # {"min": 16, "max": 31, "step": 0.5}
    options: list | None = None  # ["cool", "heat", "auto"]

    def validate(self, value: Any) -> Any:
        """Validate and coerce a value against this capability's type and constraints."""
        if self.read_only:
            raise ValueError(f"'{self.name}' is read-only")

        if self.type == "bool":
            if not isinstance(value, bool):
                raise ValueError(f"'{self.name}' expects bool, got {type(value).__name__}")
            return value

        if self.type == "enum":
            if str(value) not in [str(o) for o in (self.options or [])]:
                raise ValueError(
                    f"'{self.name}' must be one of {self.options}, got '{value}'"
                )
            return str(value)

        if self.type in ("int", "float"):
            num = int(value) if self.type == "int" else float(value)
            if self.range:
                lo, hi = self.range.get("min"), self.range.get("max")
                if lo is not None and num < lo:
                    raise ValueError(f"'{self.name}' minimum is {lo}, got {num}")
                if hi is not None and num > hi:
                    raise ValueError(f"'{self.name}' maximum is {hi}, got {num}")
            return num

        return value


@dataclass
class DeviceState:
    """Current state snapshot of a device."""

    device_id: str
    capabilities: dict[str, Any]  # {"power": True, "temperature": 24.0}
    online: bool = True


@dataclass
class Device:
    """Brand-agnostic device representation."""

    id: str
    name: str
    brand: str  # "midea_ac", "virtual", "xiaomi"
    type: str  # "ac", "light", "curtain", "sensor"
    capabilities: list[Capability]
    state: DeviceState | None = None

    def get_capability(self, name: str) -> Capability | None:
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "type": self.type,
            "capabilities": [
                {"name": c.name, "type": c.type, "read_only": c.read_only}
                | ({"range": c.range} if c.range else {})
                | ({"options": c.options} if c.options else {})
                for c in self.capabilities
            ],
        }
        if self.state:
            result["state"] = self.state.capabilities
        return result
