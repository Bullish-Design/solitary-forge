# src/solitary_forge/exceptions.py
"""Exception classes for solitary-forge."""
from __future__ import annotations


class ForgeError(Exception):
    """Base exception for solitary-forge errors."""
    pass


class ConfigError(ForgeError):
    """Raised when configuration is invalid or missing."""
    pass


class PluginError(ForgeError):
    """Raised when plugin operations fail."""
    pass


class TemplateError(ForgeError):
    """Raised when template rendering fails."""
    pass


class GitOperationError(PluginError):
    """Raised when Git operations fail."""
    pass


class SecurityError(ForgeError):
    """Raised when security policies are violated."""
    pass


class ValidationError(ForgeError):
    """Raised when validation fails."""
    pass


class DependencyError(PluginError):
    """Raised when dependency resolution fails."""
    pass
