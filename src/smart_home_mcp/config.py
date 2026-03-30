import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

CACHE_FILE = _project_root / "device_cache.json"


def get_brand_config(prefix: str) -> dict[str, str]:
    """Return all env vars starting with PREFIX_ as a dict with the prefix stripped.

    Example: prefix="MIDEA" returns {"ACCOUNT": "...", "PASSWORD": "..."}
    from MIDEA_ACCOUNT, MIDEA_PASSWORD env vars.
    """
    prefix_upper = prefix.upper() + "_"
    return {
        k[len(prefix_upper):]: v
        for k, v in os.environ.items()
        if k.startswith(prefix_upper)
    }
