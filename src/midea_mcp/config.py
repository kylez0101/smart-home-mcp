import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

MIDEA_ACCOUNT = os.environ.get("MIDEA_ACCOUNT", "")
MIDEA_PASSWORD = os.environ.get("MIDEA_PASSWORD", "")
MIDEA_APP = os.environ.get("MIDEA_APP", "MSmartHome")

# Control mode: "auto" (LAN first, cloud fallback), "lan" (LAN only), "cloud" (cloud only)
MIDEA_CONTROL_MODE = os.environ.get("MIDEA_CONTROL_MODE", "auto")

CACHE_FILE = _project_root / "device_cache.json"
