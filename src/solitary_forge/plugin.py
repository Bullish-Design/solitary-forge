# src/solitary_forge/plugin.py
"""Plugin management for solitary-forge."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import Repo, exc as git_exc
from pydantic import BaseModel, ConfigDict
from rich.console import Console

from .exceptions import GitOperationError, PluginError
from .models import PluginConfig, PluginManifest


class Plugin(BaseModel):
    """Represents a loaded plugin."""

    name: str
    path: Path
    config: Dict[str, Any] = {}
    manifest: Optional[PluginManifest] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
    # class Config:
    #    arbitrary_types_allowed = True

    @property
    def templates_path(self) -> Path:
        """Get the templates directory for this plugin."""
        return self.path / "templates"

    @property
    def has_templates(self) -> bool:
        """Check if plugin has templates directory."""
        return self.templates_path.exists() and self.templates_path.is_dir()

    def load_manifest(self) -> Optional[PluginManifest]:
        """Load plugin manifest if it exists."""
        manifest_path = self.path / "plugin.yml"
        if manifest_path.exists():
            try:
                self.manifest = PluginManifest.from_yaml_file(manifest_path)
                return self.manifest
            except Exception as e:
                raise PluginError(f"Failed to load manifest for plugin '{self.name}': {e}")
        return None

    def list_templates(self) -> List[str]:
        """List available templates in this plugin."""
        if not self.has_templates:
            return []

        templates = []
        for template_file in self.templates_path.rglob("*.j2"):
            # Get relative path from templates directory
            rel_path = template_file.relative_to(self.templates_path)
            templates.append(str(rel_path))

        return sorted(templates)


class PluginManager(BaseModel):
    """Manages plugin lifecycle and caching."""

    cache_dir: Path
    console: Console = Console()

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    # class Config:
    #    arbitrary_types_allowed = True

    def __init__(self, cache_dir: Path, **kwargs):
        super().__init__(cache_dir=cache_dir, **kwargs)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_plugins(self, plugins_config: List[PluginConfig]) -> List[Plugin]:
        """Load all plugins from configuration."""
        loaded_plugins = []

        for plugin_config in plugins_config:
            try:
                plugin = self._load_plugin(plugin_config)
                loaded_plugins.append(plugin)
                self.console.print(f"✓ Loaded plugin: [cyan]{plugin.name}[/cyan]")
            except Exception as e:
                self.console.print(f"✗ Failed to load plugin '{plugin_config.name}': {e}", style="red")
                raise PluginError(f"Failed to load plugin '{plugin_config.name}': {e}")

        return loaded_plugins

    def _load_plugin(self, config: PluginConfig) -> Plugin:
        """Load a single plugin."""
        plugin_path = self._ensure_plugin_available(config)

        plugin = Plugin(name=config.name, path=plugin_path, config=config.config)

        # Load manifest if available
        plugin.load_manifest()

        # Validate plugin has templates
        if not plugin.has_templates:
            raise PluginError(f"Plugin '{config.name}' has no templates directory")

        return plugin

    def _ensure_plugin_available(self, config: PluginConfig) -> Path:
        """Ensure plugin is available locally, cloning or updating as needed."""
        plugin_path = self.cache_dir / config.name

        if plugin_path.exists():
            return self._update_plugin(config, plugin_path)
        else:
            return self._clone_plugin(config, plugin_path)

    def _clone_plugin(self, config: PluginConfig, target_path: Path) -> Path:
        """Clone a plugin repository."""
        self.console.print(f"Cloning plugin '[cyan]{config.name}[/cyan]' from {config.git}...")

        try:
            repo = Repo.clone_from(config.git, target_path)
            self._checkout_version(repo, config.version)
            return target_path
        except git_exc.GitCommandError as e:
            # Clean up partial clone on failure
            if target_path.exists():
                shutil.rmtree(target_path)
            raise GitOperationError(f"Failed to clone plugin '{config.name}': {e}")

    def _update_plugin(self, config: PluginConfig, plugin_path: Path) -> Path:
        """Update an existing plugin repository."""
        try:
            repo = Repo(plugin_path)

            # Fetch latest changes
            self.console.print(f"Updating plugin '[cyan]{config.name}[/cyan]'...")
            repo.remotes.origin.fetch()

            # Checkout requested version
            self._checkout_version(repo, config.version)

            return plugin_path
        except git_exc.GitCommandError as e:
            raise GitOperationError(f"Failed to update plugin '{config.name}': {e}")
        except git_exc.InvalidGitRepositoryError:
            # Cache directory exists but isn't a git repo - remove and reclone
            shutil.rmtree(plugin_path)
            return self._clone_plugin(config, plugin_path)

    def _checkout_version(self, repo: Repo, version: str) -> None:
        """Checkout specific version (branch, tag, or commit)."""
        try:
            repo.git.checkout(version)
        except git_exc.GitCommandError as e:
            raise GitOperationError(f"Failed to checkout version '{version}': {e}")

    def clean_cache(self, plugin_name: Optional[str] = None) -> None:
        """Clean plugin cache."""
        if plugin_name:
            plugin_path = self.cache_dir / plugin_name
            if plugin_path.exists():
                shutil.rmtree(plugin_path)
                self.console.print(f"Cleaned cache for plugin: [cyan]{plugin_name}[/cyan]")
        else:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.console.print("Cleaned all plugin cache")

    def list_cached_plugins(self) -> List[str]:
        """List all cached plugins."""
        if not self.cache_dir.exists():
            return []

        return [p.name for p in self.cache_dir.iterdir() if p.is_dir() and (p / ".git").exists()]

