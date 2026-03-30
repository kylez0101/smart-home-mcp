from smart_home_mcp.models import Capability, Device, DeviceState


class VirtualDeviceStore:
    """In-memory state store for virtual devices."""

    def __init__(self, devices_config: list[dict]):
        self._devices: dict[str, Device] = {}
        self._states: dict[str, dict] = {}

        for dev in devices_config:
            caps = []
            for c in dev["capabilities"]:
                caps.append(Capability(
                    name=c["name"],
                    type=c["type"],
                    read_only=c.get("read_only", False),
                    range=c.get("range"),
                    options=c.get("options"),
                ))
            device = Device(
                id=dev["id"],
                name=dev["name"],
                brand="virtual",
                type=dev["type"],
                capabilities=caps,
            )
            self._devices[dev["id"]] = device
            self._states[dev["id"]] = dict(dev["initial_state"])

    def list_devices(self) -> list[Device]:
        return list(self._devices.values())

    def _resolve_id(self, device_id: str = "") -> str:
        if device_id and device_id in self._devices:
            return device_id
        if not device_id and self._devices:
            return next(iter(self._devices))
        raise ValueError(f"Virtual device not found: {device_id or '(none)'}")

    def get_device(self, device_id: str = "") -> Device:
        return self._devices[self._resolve_id(device_id)]

    def get_state(self, device_id: str = "") -> DeviceState:
        did = self._resolve_id(device_id)
        return DeviceState(
            device_id=did,
            capabilities=dict(self._states[did]),
        )

    def control(self, device_id: str, capability: str, value) -> DeviceState:
        did = self._resolve_id(device_id)
        device = self._devices[did]
        cap = device.get_capability(capability)
        if not cap:
            available = ", ".join(c.name for c in device.capabilities)
            raise ValueError(
                f"Device '{device.name}' does not support '{capability}'. "
                f"Available: {available}"
            )
        validated = cap.validate(value)
        self._states[did][capability] = validated
        return self.get_state(did)
