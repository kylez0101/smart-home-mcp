import logging
from hashlib import sha256

from midea_beautiful import appliance_state, connect_to_cloud, find_appliances
from midea_beautiful.exceptions import MideaError, MideaNetworkError
from midea_beautiful.lan import LanDevice
from midea_beautiful.scanner import do_find_appliances

from .cloud_session import CloudSession
from smart_home_mcp.config import get_brand_config
from smart_home_mcp.device_cache import get_device, save_cache

_cfg = get_brand_config("MIDEA")
MIDEA_ACCOUNT = _cfg.get("ACCOUNT", "")
MIDEA_PASSWORD = _cfg.get("PASSWORD", "")

_LOGGER = logging.getLogger(__name__)

MODE_MAP = {
    "cool": 0,
    "dry": 1,
    "auto": 2,
    "fan": 3,
    "heat": 4,
}
MODE_NAMES = {v: k for k, v in MODE_MAP.items()}

FAN_MAP = {
    "auto": 102,
    "low": 40,
    "medium": 60,
    "high": 80,
    "full": 100,
}

# Preset account for NetHome Plus (used to get device tokens since
# MeijuCloud's getToken API is deprecated).
_PRESET_ACCOUNT_DATA = [
    39182118275972017797890111985649342047468653967530949796945843010512,
    39182118275980892824833804202177448991093361348247890162501600564413,
    39182118275972017797890111985649342050088014265865102175083010656997,
]


def _get_nethome_tokens(appliance_id: int) -> list[tuple[str, str]]:
    """Get all available token/key pairs via NetHome Plus preset account.

    Returns a list of (token, key) tuples to try during device authentication.
    """
    username = bytes.fromhex(
        format((_PRESET_ACCOUNT_DATA[0] ^ _PRESET_ACCOUNT_DATA[1]), "X")
    ).decode("utf-8", errors="ignore")
    password = bytes.fromhex(
        format((_PRESET_ACCOUNT_DATA[0] ^ _PRESET_ACCOUNT_DATA[2]), "X")
    ).decode("utf-8", errors="ignore")

    cloud = connect_to_cloud(account=username, password=password, appname="NetHome Plus")

    results = []
    for method in [1, 0, 2]:  # big-endian 6 bytes first (most common)
        if method == 0:
            bytes_id = bytes(reversed(appliance_id.to_bytes(8, "big")))
        elif method == 1:
            bytes_id = appliance_id.to_bytes(6, "big")
        else:
            bytes_id = appliance_id.to_bytes(6, "little")

        data = bytearray(sha256(bytes_id).digest())
        for i in range(16):
            data[i] ^= data[i + 16]
        udp_id = bytes(data[0:16]).hex()

        try:
            response = cloud.api_request("/v1/iot/secure/getToken", {"udpid": udp_id})
            if response and "tokenlist" in response:
                for t in response["tokenlist"]:
                    if t["udpId"] == udp_id:
                        results.append((t["token"], t["key"]))
        except Exception:
            continue

    return results


class DeviceManager:
    def __init__(self, cloud_session: CloudSession, control_mode: str = "auto"):
        self._cloud = cloud_session
        self._mode = control_mode
        self._devices: dict[str, LanDevice] = {}

    def discover(self) -> list[dict]:
        if not MIDEA_ACCOUNT or not MIDEA_PASSWORD:
            raise ValueError("MIDEA_ACCOUNT and MIDEA_PASSWORD must be set in .env")

        cloud = self._cloud.get_cloud()

        # Step 1: List devices from MeijuCloud
        cloud_appliances = cloud.list_appliances()

        # Step 2: LAN broadcast to find device addresses
        lan_devices = do_find_appliances(
            cloud=None,
            addresses=["255.255.255.255"],
            max_retries=2,
        )
        lan_map = {str(d.appliance_id): d for d in lan_devices}

        result = []
        for app in cloud_appliances:
            app_id = str(app["id"])
            address = None
            port = 6444
            token = ""
            key = ""

            # Get LAN address if found
            if app_id in lan_map:
                ld = lan_map[app_id]
                address = ld.address
                port = ld.port

            # Get token/key pairs from NetHome Plus and try each
            token_pairs = []
            try:
                token_pairs = _get_nethome_tokens(int(app_id))
            except Exception as e:
                _LOGGER.warning("Failed to get tokens for %s: %s", app_id, e)

            if address and token_pairs:
                for t, k in token_pairs:
                    try:
                        device = appliance_state(address=address, token=t, key=k)
                        self._devices[app_id] = device
                        token, key = t, k
                        _LOGGER.info("Connected to %s with token method", app_id)
                        break
                    except Exception as e:
                        _LOGGER.debug("Token attempt failed for %s: %s", app_id, e)
                        continue

            info = {
                "id": app_id,
                "name": app.get("name"),
                "type": app.get("type"),
                "address": address,
                "port": port,
                "token": token,
                "key": key,
                "model": app.get("modelNumber"),
                "serial_number": app.get("sn"),
            }
            result.append(info)

        save_cache(result)
        return result

    def _get_device(self, device_id: str = "") -> LanDevice:
        # Try in-memory cache first
        if device_id and device_id in self._devices:
            return self._devices[device_id]
        if not device_id and self._devices:
            return next(iter(self._devices.values()))

        # Fall back to disk cache
        info = get_device(device_id)
        if not info:
            raise ValueError("No cached device found. Run discover_devices first.")

        device = appliance_state(
            address=info["address"],
            token=info["token"],
            key=info["key"],
        )
        self._devices[str(info["id"])] = device
        return device

    def _apply(self, device: LanDevice) -> None:
        """Apply pending state changes via LAN."""
        try:
            device.apply()
        except (MideaError, MideaNetworkError, OSError) as e:
            _LOGGER.warning("LAN control failed: %s", e)
            raise

    def _refresh(self, device: LanDevice) -> None:
        """Refresh device state via LAN."""
        try:
            device.refresh()
        except (MideaError, MideaNetworkError, OSError) as e:
            _LOGGER.warning("LAN refresh failed: %s", e)
            raise

    def _build_status(self, device: LanDevice) -> dict:
        state = device.state
        return {
            "power": state.running,
            "mode": MODE_NAMES.get(state.mode, f"unknown({state.mode})"),
            "target_temperature": state.target_temperature,
            "indoor_temperature": state.indoor_temperature,
            "outdoor_temperature": state.outdoor_temperature,
            "fan_speed": state.fan_speed,
            "vertical_swing": state.vertical_swing,
            "horizontal_swing": state.horizontal_swing,
            "eco_mode": state.eco_mode,
            "turbo": state.turbo,
            "comfort_sleep": state.comfort_sleep,
        }

    def get_status(self, device_id: str = "") -> dict:
        device = self._get_device(device_id)
        self._refresh(device)
        return self._build_status(device)

    def turn_on(self, device_id: str = "") -> dict:
        device = self._get_device(device_id)
        device.state.running = True
        self._apply(device)
        return self._build_status(device)

    def turn_off(self, device_id: str = "") -> dict:
        device = self._get_device(device_id)
        device.state.running = False
        self._apply(device)
        return self._build_status(device)

    def set_temperature(self, temperature: float, device_id: str = "") -> dict:
        if temperature < 16 or temperature > 31:
            raise ValueError("Temperature must be between 16 and 31°C")
        device = self._get_device(device_id)
        device.state.target_temperature = temperature
        self._apply(device)
        return self._build_status(device)

    def set_mode(self, mode: str, device_id: str = "") -> dict:
        mode_lower = mode.lower()
        if mode_lower not in MODE_MAP:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {', '.join(MODE_MAP.keys())}")
        device = self._get_device(device_id)
        device.state.mode = MODE_MAP[mode_lower]
        self._apply(device)
        return self._build_status(device)

    def set_fan_speed(self, speed: str, device_id: str = "") -> dict:
        speed_lower = speed.lower()
        if speed_lower not in FAN_MAP:
            raise ValueError(f"Invalid speed '{speed}'. Choose from: {', '.join(FAN_MAP.keys())}")
        device = self._get_device(device_id)
        device.state.fan_speed = FAN_MAP[speed_lower]
        self._apply(device)
        return self._build_status(device)

    def set_swing(
        self,
        vertical: bool | None = None,
        horizontal: bool | None = None,
        device_id: str = "",
    ) -> dict:
        device = self._get_device(device_id)
        if vertical is not None:
            device.state.vertical_swing = vertical
        if horizontal is not None:
            device.state.horizontal_swing = horizontal
        self._apply(device)
        return self._build_status(device)

    def set_eco_mode(self, enabled: bool, device_id: str = "") -> dict:
        device = self._get_device(device_id)
        device.state.eco_mode = enabled
        self._apply(device)
        return self._build_status(device)

    def set_turbo(self, enabled: bool, device_id: str = "") -> dict:
        device = self._get_device(device_id)
        device.state.turbo = enabled
        self._apply(device)
        return self._build_status(device)
