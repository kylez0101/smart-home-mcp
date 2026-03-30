from smart_home_mcp.plugin_base import BrandPlugin

# Contributors: add your plugin class import and append to PLUGIN_CLASSES.
from smart_home_mcp.brands.midea_ac.plugin import MideaACPlugin
from smart_home_mcp.brands.virtual.plugin import VirtualPlugin

PLUGIN_CLASSES: list[type[BrandPlugin]] = [
    MideaACPlugin,
    VirtualPlugin,
]
