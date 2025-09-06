# src/solitary_forge/forge.py
"""Main Forge orchestrator for solitary-forge."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, ConfigDict
from rich.console import Console

from .exceptions import ConfigError, TemplateError
from .models import ForgeConfig
from .plugin import Plugin, PluginManager


class Forge(BaseModel):
    """Main orchestrator for environment generation."""

    config_path: Path
    project_root: Path
    config: ForgeConfig
    plugin_manager: Any  # PluginManager
    console: Console = Console()

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    # class Config:
    #    arbitrary_types_allowed = True

    def __init__(self, config_path: str | Path = ".forge.yml", **kwargs):
        config_path = Path(config_path).resolve()
        project_root = config_path.parent

        # Load configuration
        try:
            config = ForgeConfig.from_yaml_file(config_path)
        except FileNotFoundError:
            raise ConfigError(f"Configuration file not found: {config_path}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")

        # Initialize plugin manager
        cache_dir = project_root / ".forge_cache" / "plugins"
        # plugin_manager = PluginManager(cache_dir=cache_dir)
        plugin_manager = kwargs.pop("plugin_manager", None) or PluginManager(cache_dir=cache_dir)

        super().__init__(
            config_path=config_path, project_root=project_root, config=config, plugin_manager=plugin_manager, **kwargs
        )

    def build(self) -> Dict[str, Path]:
        """Build the environment by rendering all templates."""
        self.console.print("\n🔨 Starting environment build...")

        # Load plugins
        plugins = self._load_plugins()

        # Create Jinja2 environment
        jinja_env = self._create_jinja_environment(plugins)

        # Build template context
        context = self._build_context(plugins)

        # Render templates
        rendered_files = self._render_templates(jinja_env, context)

        self.console.print(f"\n✅ Build complete! Generated {len(rendered_files)} files.")
        return rendered_files

    def clean(self, plugin_name: str | None = None) -> None:
        """Clean plugin cache."""
        self.plugin_manager.clean_cache(plugin_name)

    def list_plugins(self) -> List[str]:
        """List cached plugins."""
        return self.plugin_manager.list_cached_plugins()

    def list_templates(self) -> Dict[str, List[str]]:
        """List available templates from all plugins."""
        plugins = self._load_plugins()
        return {plugin.name: plugin.list_templates() for plugin in plugins}

    def _load_plugins(self) -> List[Plugin]:
        """Load all plugins from configuration."""
        if not self.config.plugins:
            raise ConfigError("No plugins configured")

        self.console.print(f"Loading {len(self.config.plugins)} plugins...")
        return self.plugin_manager.load_plugins(self.config.plugins)

    def _create_jinja_environment(self, plugins: List[Plugin]) -> Environment:
        """Create Jinja2 environment with plugin template paths."""
        template_paths = []

        for plugin in plugins:
            if plugin.has_templates:
                template_paths.append(str(plugin.templates_path))
            else:
                self.console.print(f"⚠️  Plugin '{plugin.name}' has no templates directory", style="yellow")

        if not template_paths:
            raise TemplateError("No template directories found in any plugins")

        return Environment(
            loader=FileSystemLoader(template_paths), trim_blocks=True, lstrip_blocks=True, autoescape=False
        )

    def _build_context(self, plugins: List[Plugin]) -> Dict[str, Any]:
        """Build the template context."""
        context = {
            "variables": self.config.variables.copy(),
            "plugins": {},
            "project_root": str(self.project_root),
            "config_path": str(self.config_path),
        }

        # Be robust to test doubles/mocks that omit attributes
        for plugin in plugins:
            p_config = getattr(plugin, "config", {}) or {}
            p_path = getattr(plugin, "path", "") or ""
            p_manifest = getattr(plugin, "manifest", None)
            if hasattr(p_manifest, "model_dump"):
                p_manifest = p_manifest.model_dump()
            elif hasattr(p_manifest, "dict"):
                p_manifest = p_manifest.dict()
            else:
                p_manifest = {}

            context["plugins"][plugin.name] = {
                "config": p_config,
                "path": str(p_path) if p_path else "",
                "manifest": p_manifest,
            }

        return context

    def _render_templates(self, jinja_env: Environment, context: Dict[str, Any]) -> Dict[str, Path]:
        """Render all templates specified in configuration."""
        rendered_files = {}

        for render_config in self.config.render:
            try:
                template = jinja_env.get_template(render_config.template)
                rendered_content = template.render(context)

                output_path = self.project_root / render_config.output
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(rendered_content)

                rendered_files[render_config.template] = output_path
                self.console.print(f"  ✓ {render_config.template} → [cyan]{render_config.output}[/cyan]")

            except TemplateNotFound:
                raise TemplateError(f"Template not found: {render_config.template}")
            except Exception as e:
                raise TemplateError(f"Failed to render {render_config.template}: {e}")

        return rendered_files

    def validate_config(self) -> bool:
        """Validate the current configuration."""
        try:
            # Check if all plugins can be loaded
            plugins = self._load_plugins()

            # Check if all templates exist
            jinja_env = self._create_jinja_environment(plugins)

            for render_config in self.config.render:
                try:
                    jinja_env.get_template(render_config.template)
                except TemplateNotFound:
                    self.console.print(f"✗ Template not found: {render_config.template}", style="red")
                    return False

            self.console.print("✅ Configuration is valid")
            return True

        except Exception as e:
            self.console.print(f"✗ Configuration validation failed: {e}", style="red")
            return False

    @classmethod
    def init_config(cls, project_dir: Path | str = ".", force: bool = False) -> Path:
        """Initialize a default .forge.yml configuration."""
        project_dir = Path(project_dir).resolve()
        config_path = project_dir / ".forge.yml"

        if config_path.exists() and not force:
            raise ConfigError(f"Configuration already exists: {config_path}")

        default_config = {
            "variables": {
                "project_name": project_dir.name,
                "base_image": "nixos/nix:latest",
                "container_name": f"{project_dir.name}-dev",
                "workdir": "/workspace",
            },
            "plugins": [
                {"name": "core", "git": "https://github.com/solitary-project/forge-plugin-core.git", "version": "main"}
            ],
            "render": [
                {"template": "Dockerfile.j2", "output": "Dockerfile"},
                {"template": "docker-compose.yml.j2", "output": "docker-compose.yml"},
            ],
        }

        import yaml

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        console = Console()
        console.print(f"✅ Created configuration: [cyan]{config_path}[/cyan]")
        console.print("⚠️  [yellow]Update the plugin Git URLs before running build[/yellow]")

        return config_path

