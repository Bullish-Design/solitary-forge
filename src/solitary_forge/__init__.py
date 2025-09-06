# src/solitary_forge/__init__.py
"""
Solitary Forge - Jinja2-based environment generator with Git plugin support
"""
from __future__ import annotations

from .exceptions import ForgeError, PluginError, TemplateError
from .forge import Forge
from .models import ForgeConfig, PluginConfig, RenderConfig
from .plugin import Plugin, PluginManager

__version__ = "0.1.0"
__all__ = [
    "Forge",
    "Plugin", 
    "PluginManager",
    "ForgeConfig",
    "PluginConfig",
    "RenderConfig",
    "ForgeError",
    "PluginError",
    "TemplateError",
]