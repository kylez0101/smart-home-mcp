from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

from .models import Device, DeviceState


@dataclass
class ToolDefinition:
    """A tool to register with FastMCP."""

    name: str
    description: str
    fn: Callable[..., Any]


class BrandPlugin(ABC):
    """Base class for all brand plugins."""

    @property
    @abstractmethod
    def brand_name(self) -> str:
        """Short identifier, e.g. 'midea_ac', 'virtual'."""
        ...

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return the list of brand-specific MCP tools."""
        ...

    @abstractmethod
    def get_devices(self) -> list[Device]:
        """Return all known devices from this plugin."""
        ...

    @abstractmethod
    def get_state(self, device_id: str) -> DeviceState:
        """Get the current state of a device."""
        ...

    @abstractmethod
    def control(self, device_id: str, capability: str, value: Any) -> DeviceState:
        """Set a capability on a device. Returns updated state."""
        ...
