import json
from pathlib import Path

from .config import CACHE_FILE


def load_cache() -> list[dict]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return []


def save_cache(devices: list[dict]) -> None:
    CACHE_FILE.write_text(json.dumps(devices, indent=2, ensure_ascii=False))


def get_device(device_id: str = "") -> dict | None:
    devices = load_cache()
    if not devices:
        return None
    if not device_id:
        return devices[0]
    for d in devices:
        if str(d["id"]) == str(device_id):
            return d
    return None
