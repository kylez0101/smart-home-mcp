# Smart Home MCP

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Control your entire home from Claude. No app, no dashboard, no Home Assistant. Just talk.

Smart home control is fragmented... every brand has its own app, its own automations, its own walled garden. Smart Home MCP goes direct: MCP to device APIs, no middleware. Clone, add credentials, and your AI assistant becomes your home controller.

The AI isn't just a remote control. It reasons about your home. "Make the bedroom sleep-ready" becomes a coordinated sequence across AC, lights, and curtains. No YAML rules, no automation configs. Natural language is the interface.

### What it looks like

```
You:    "I'm going to sleep"
Claude: Activating Sleep Mode...
          ✓ Bedroom AC → 26°C cooling
          ✓ Living room light → off
          ✓ Curtains → closed

You:    "I'm heading out"
Claude: Activating Leave Home...
          ✓ Bedroom AC → off
          ✓ Bedroom light → off
          ✓ Curtains → closed

You:    "It's getting hot, cool down the bedroom"
Claude: Turning on bedroom AC, setting to 25°C cooling mode.
          ✓ Power → on
          ✓ Temperature → 25°C
          ✓ Mode → cool
```

You don't need to define scenes for everything. Claude reasons on the fly.

## Features

- **Minimal setup** — no Home Assistant, no server, no dashboard. Just a local MCP server
- **AI-native automation** — scenes and cross-device coordination through natural language
- **Plugin-based** — each brand is a self-contained plugin, easy to contribute
- **LAN-first** — direct local control, millisecond latency, no cloud roundtrip
- **Universal control** — one generic interface works across all brands and device types
- **Virtual devices** — develop and test without real hardware

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/kylez0101/smart-home-mcp.git
cd smart-home-mcp
cp .env.example .env
```

Edit `.env` with your device credentials:

```bash
# Midea AC
MIDEA_ACCOUNT=your_phone_number
MIDEA_PASSWORD=your_password
```

Install dependencies:

```bash
uv sync --extra midea    # install with Midea AC support
# or
uv sync                  # virtual devices only (no hardware needed)
```

### Usage

Add to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "smart-home": {
      "command": "uv",
      "args": ["--directory", "/path/to/smart-home-mcp", "run", "python", "-m", "smart_home_mcp"]
    }
  }
}
```

Then just talk to Claude naturally. Your credentials never leave your machine.

## Scenes

Define scenes in `home.yaml` to coordinate multiple devices with a single command:

```yaml
scenes:
  sleep:
    display_name: "Sleep Mode"
    actions:
      - alias: "bedroom_ac"
        tool: "midea_set_temperature"
        params: { temperature: 26 }
      - alias: "bedroom_ac"
        tool: "midea_set_mode"
        params: { mode: "cool" }
      - alias: "bedroom_light"
        tool: "virtual_turn_off"
        params: {}

  leave_home:
    display_name: "Leave Home"
    actions:
      - alias: "bedroom_ac"
        tool: "midea_turn_off"
        params: {}
      - alias: "living_light"
        tool: "virtual_turn_off"
        params: {}
      - alias: "robot_vacuum"
        tool: "roborock_start_clean"
        params: {}
```

> "I'm heading out" → AC off, lights off, robot vacuum starts cleaning

See [home.yaml.example](home.yaml.example) for a complete example with rooms, devices, and multiple scenes.

## Supported Brands

| Brand | Device Type | Control Method | Status |
|-------|-----------|----------------|--------|
| Midea (美的) | Air Conditioner | LAN (UDP 6444) | Available |
| Virtual | Light, AC, Curtain, Sensor | In-memory mock | Available |
| Xiaomi (小米) | Various | miIO protocol | Planned |
| Hisense (海信) | TV / AC | Various | Looking for contributors |
| Haier (海尔) | Various | Various | Looking for contributors |
| Roborock (石头) | Robot Vacuum | Various | Looking for contributors |
| Ecovacs (科沃斯) | Robot Vacuum | Various | Looking for contributors |
| Sony | TV | REST API / IRCC | Looking for contributors |

PRs welcome! See [Adding a New Brand](#adding-a-new-brand) below.

## Architecture

Smart Home MCP talks to your devices over your local WiFi. Your credentials stay on your machine. Any AI client that supports MCP can use it, not just Claude.

```
You (natural language)
 |
 v
Claude / Any MCP Client
 |
 |  MCP Protocol
 v
┌──────────────────────────────────────┐
│  server.py                           │
│  Generic tools: list_devices,        │
│  control_device, get_device_state    │
│  + Scene engine (home.yaml)          │
└───────┬──────────────┬───────────────┘
        |              |
   ┌────┴────┐   ┌────┴────┐
   │ Midea   │   │ Virtual │  ...
   │ Plugin  │   │ Plugin  │
   └────┬────┘   └────┬────┘
        |              |
   ┌────┴────┐   ┌────┴────┐
   │ AC via  │   │In-memory│
   │  LAN    │   │  state  │
   └─────────┘   └─────────┘
```

```
src/smart_home_mcp/
├── server.py              # Plugin loader + generic tools + scene engine
├── models.py              # Device, Capability, DeviceState (brand-agnostic)
├── plugin_base.py         # BrandPlugin ABC
├── home_config.py         # home.yaml parser
├── home_plugin.py         # Scene activation tools
├── config.py              # Per-brand config helper
├── device_cache.py        # Generic device cache
└── brands/
    ├── __init__.py         # Plugin registry
    ├── midea_ac/           # Midea air conditioner
    └── virtual/            # Mock devices for dev/testing
```

The `control_device(device_id, capability, value)` generic tool works across all brands. Every device exposes its capabilities with types, ranges, and options, so the AI always knows what's valid before making a call.

## Adding a New Brand

Want to add support for a new device? It only takes 3 steps:

**1. Create your plugin** in `src/smart_home_mcp/brands/<your_brand>/plugin.py`:

```python
from smart_home_mcp.config import get_brand_config
from smart_home_mcp.models import Capability, Device, DeviceState
from smart_home_mcp.plugin_base import BrandPlugin, ToolDefinition


class MyBrandPlugin(BrandPlugin):
    @property
    def brand_name(self) -> str:
        return "my_brand"

    def __init__(self):
        cfg = get_brand_config("MY_BRAND")  # reads MY_BRAND_* env vars
        self._host = cfg.get("HOST", "")

    def get_devices(self) -> list[Device]:
        # Return your discovered devices
        ...

    def get_state(self, device_id: str) -> DeviceState:
        # Query device for current state
        ...

    def control(self, device_id: str, capability: str, value) -> DeviceState:
        # Send command to device
        ...

    def get_tools(self) -> list[ToolDefinition]:
        # Optional: brand-specific tools beyond generic control
        return []
```

**2. Register it** in `src/smart_home_mcp/brands/__init__.py`:

```python
from smart_home_mcp.brands.my_brand.plugin import MyBrandPlugin

PLUGIN_CLASSES: list[type[BrandPlugin]] = [
    MideaACPlugin,
    VirtualPlugin,
    MyBrandPlugin,   # <-- add this line
]
```

**3. Add dependencies** (if any) to `pyproject.toml`:

```toml
[project.optional-dependencies]
my_brand = ["some-library>=1.0"]
```

Your devices will automatically appear in `list_devices` and be controllable via `control_device`.

## Virtual Devices

The virtual plugin ships with mock devices (light, AC, curtain, sensor) so you can develop and test without owning any hardware:

```bash
uv sync              # no --extra needed
cp home.yaml.example home.yaml
```

Virtual devices maintain state in memory. Perfect for developing new brand plugins, testing scene coordination, and demoing the project.

## License

MIT
