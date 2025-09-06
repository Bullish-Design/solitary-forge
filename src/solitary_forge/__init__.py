# src/solitary_forge/__init__.py
"""
Solitary Forge - Jinja2-based environment generator with Git plugin support
"""
from __future__ import annotations

from .exceptions import ForgeError, PluginError, TemplateError, SecurityError
from .forge import Forge
from .models import ForgeConfig, PluginConfig, RenderConfig, PluginManifest
from .plugin import Plugin, PluginManager

__version__ = "0.2.0"
__all__ = [
    "Forge",
    "Plugin", 
    "PluginManager",
    "ForgeConfig",
    "PluginConfig",
    "RenderConfig",
    "PluginManifest",
    "ForgeError",
    "PluginError",
    "TemplateError",
    "SecurityError",
]
