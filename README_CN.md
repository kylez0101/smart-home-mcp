# Smart Home MCP

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

中文 | [English](README.md)

用 Claude 控制你的整个家。不需要 APP，不需要仪表盘，不需要 Home Assistant。说句话就行。

智能家居的控制太碎片化了... 每个品牌都有自己的 APP，自己的自动化，自己的围墙花园。Smart Home MCP 直连设备 API，没有中间层。克隆仓库，填入账号密码，你的 AI 助手就是你的家居控制中心。

AI 不只是一个遥控器，它能理解你的家。"帮我准备睡觉" 就会变成一连串跨设备的协调操作：空调、灯、窗帘同时响应。不需要写 YAML 规则，不需要配置自动化。自然语言就是交互方式。

### 实际效果

```
你：    "我要睡觉了"
Claude: 正在激活睡眠模式...
          ✓ 卧室空调 → 26°C 制冷
          ✓ 客厅灯 → 关闭
          ✓ 窗帘 → 关闭

你：    "我出门了"
Claude: 正在激活离家模式...
          ✓ 卧室空调 → 关闭
          ✓ 卧室灯 → 关闭
          ✓ 窗帘 → 关闭

你：    "有点热，把卧室降降温"
Claude: 正在打开卧室空调，设置为 25°C 制冷模式。
          ✓ 电源 → 开启
          ✓ 温度 → 25°C
          ✓ 模式 → 制冷
```

不需要为所有事情定义场景，Claude 可以即时推理。

## 特性

- **极简安装** — 不需要 Home Assistant，不需要服务器，不需要仪表盘。只需一个本地 MCP 服务
- **AI 原生自动化** — 通过自然语言实现场景联动和跨设备协调
- **插件化架构** — 每个品牌是一个独立插件，方便社区贡献
- **局域网优先** — 直连本地设备，毫秒级响应，无需经过云端
- **统一控制** — 一个通用接口控制所有品牌和设备类型
- **虚拟设备** — 无需真实硬件即可开发和测试

## 快速开始

### 一键安装

复制以下内容发给 Claude Code 或 OpenClaw，它会帮你自动完成所有配置：

```
Install the Smart Home MCP server from https://github.com/kylez0101/smart-home-mcp.git — clone the repo, run `uv sync`, and add it to my MCP config with command "uv" and args ["--directory", "<cloned-path>", "run", "python", "-m", "smart_home_mcp"]. Then help me configure my .env file with my device credentials.
```

### 手动安装

**前置条件：** Python 3.13+、[uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/kylez0101/smart-home-mcp.git
cd smart-home-mcp
cp .env.example .env
```

编辑 `.env`，填入你的设备账号：

```bash
# 美的空调
MIDEA_ACCOUNT=your_phone_number
MIDEA_PASSWORD=your_password
```

安装依赖：

```bash
uv sync --extra midea    # 安装美的空调支持
# 或
uv sync                  # 仅虚拟设备（无需硬件）
```

### 使用方法

添加到你的 Claude Code MCP 配置中：

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

然后直接用自然语言和 Claude 对话即可。你的账号密码只保存在本地，绝不会上传。

## 场景

在 `home.yaml` 中定义场景，一句话协调多个设备：

```yaml
scenes:
  sleep:
    display_name: "睡眠模式"
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
    display_name: "离家模式"
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

> "我出门了" → 空调关闭，灯关闭，扫地机器人开始清扫

完整示例参见 [home.yaml.example](home.yaml.example)。

## 支持品牌

| 品牌 | 设备类型 | 控制方式 | 状态 |
|------|---------|---------|------|
| 美的 (Midea) | 空调 | 局域网 (UDP 6444) | 已支持 |
| 虚拟设备 | 灯、空调、窗帘、传感器 | 内存模拟 | 已支持 |
| 小米 (Xiaomi) | 多种 | miIO 协议 | 计划中 |
| 海信 (Hisense) | 电视 / 空调 | 待定 | 欢迎贡献 |
| 海尔 (Haier) | 多种 | 待定 | 欢迎贡献 |
| 石头 (Roborock) | 扫地机器人 | 待定 | 欢迎贡献 |
| 科沃斯 (Ecovacs) | 扫地机器人 | 待定 | 欢迎贡献 |
| Sony | 电视 | REST API / IRCC | 欢迎贡献 |

欢迎提交 PR！参见下方[添加新品牌](#添加新品牌)。

## 架构

Smart Home MCP 通过你的本地 WiFi 与设备通信。账号密码保存在本地。任何支持 MCP 协议的 AI 客户端都可以使用，不仅限于 Claude。

```
你（自然语言）
 |
 v
Claude / 任何 MCP 客户端
 |
 |  MCP 协议
 v
┌──────────────────────────────────────┐
│  server.py                           │
│  通用工具: list_devices,              │
│  control_device, get_device_state    │
│  + 场景引擎 (home.yaml)              │
└───────┬──────────────┬───────────────┘
        |              |
   ┌────┴────┐   ┌────┴────┐
   │  美的    │   │  虚拟   │  ...
   │  插件    │   │  插件   │
   └────┬────┘   └────┬────┘
        |              |
   ┌────┴────┐   ┌────┴────┐
   │ 局域网   │   │ 内存    │
   │  控制    │   │  状态   │
   └─────────┘   └─────────┘
```

```
src/smart_home_mcp/
├── server.py              # 插件加载器 + 通用工具 + 场景引擎
├── models.py              # Device, Capability, DeviceState（品牌无关）
├── plugin_base.py         # BrandPlugin 抽象基类
├── home_config.py         # home.yaml 解析器
├── home_plugin.py         # 场景激活工具
├── config.py              # 品牌配置助手
├── device_cache.py        # 通用设备缓存
└── brands/
    ├── __init__.py         # 插件注册表
    ├── midea_ac/           # 美的空调
    └── virtual/            # 虚拟设备（开发/测试用）
```

`control_device(device_id, capability, value)` 通用工具适用于所有品牌。每个设备都暴露其能力（类型、范围、选项），AI 在调用前就知道什么参数是合法的。

## 添加新品牌

想给新设备添加支持？只需 3 步：

**1. 创建插件** `src/smart_home_mcp/brands/<your_brand>/plugin.py`：

```python
from smart_home_mcp.config import get_brand_config
from smart_home_mcp.models import Capability, Device, DeviceState
from smart_home_mcp.plugin_base import BrandPlugin, ToolDefinition


class MyBrandPlugin(BrandPlugin):
    @property
    def brand_name(self) -> str:
        return "my_brand"

    def __init__(self):
        cfg = get_brand_config("MY_BRAND")  # 读取 MY_BRAND_* 环境变量
        self._host = cfg.get("HOST", "")

    def get_devices(self) -> list[Device]:
        # 返回已发现的设备
        ...

    def get_state(self, device_id: str) -> DeviceState:
        # 查询设备当前状态
        ...

    def control(self, device_id: str, capability: str, value) -> DeviceState:
        # 发送控制命令
        ...

    def get_tools(self) -> list[ToolDefinition]:
        # 可选：通用控制之外的品牌特有工具
        return []
```

**2. 注册插件** `src/smart_home_mcp/brands/__init__.py`：

```python
from smart_home_mcp.brands.my_brand.plugin import MyBrandPlugin

PLUGIN_CLASSES: list[type[BrandPlugin]] = [
    MideaACPlugin,
    VirtualPlugin,
    MyBrandPlugin,   # <-- 加上这一行
]
```

**3. 添加依赖**（如有）到 `pyproject.toml`：

```toml
[project.optional-dependencies]
my_brand = ["some-library>=1.0"]
```

你的设备会自动出现在 `list_devices` 中，并可通过 `control_device` 控制。

## 虚拟设备

虚拟设备插件自带模拟设备（灯、空调、窗帘、传感器），无需真实硬件即可开发和测试：

```bash
uv sync              # 不需要 --extra
cp home.yaml.example home.yaml
```

虚拟设备状态保存在内存中。适合开发新品牌插件、测试场景联动、项目演示。

## 许可证

MIT
