# src/solitary_forge/forge.py
"""Main Forge orchestrator for solitary-forge with modular architecture."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, SkipValidation
from rich.console import Console

from .context.context_builder import ContextBuilder
from .exceptions import ConfigError, TemplateError
from .generators import GeneratorRegistry, create_default_registry
from .models import ForgeConfig
from .output.output_manager import OutputManager
from .plugin import Plugin, PluginManager
from .rendering.template_renderer import JinjaTemplateRenderer, PluginTemplateLoader
from .settings import TEST_MODE
from .validation.validation_system import ValidationSystem


PMFieldType = SkipValidation[PluginManager] if TEST_MODE else PluginManager


class Forge(BaseModel):
    """Main orchestrator for environment generation with modular architecture."""

    config_path: Path
    project_root: Path
    config: ForgeConfig
    plugin_manager: PMFieldType
    generator_registry: GeneratorRegistry
    console: Console = Console()
    environment: str = "base"

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def __init__(
        self, 
        config_path: str | Path = ".forge.yml", 
        environment: str = "base",
        dry_run: bool = False,
        **kwargs
    ):
        config_path = Path(config_path).resolve()
        project_root = config_path.parent

        # Load configuration
        try:
            config = ForgeConfig.from_yaml_file(config_path)
        except FileNotFoundError:
            raise ConfigError(f"Configuration file not found: {config_path}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")

        # Initialize components
        cache_dir = project_root / ".forge_cache" / "plugins"
        plugin_manager = kwargs.pop("plugin_manager", None) or PluginManager(cache_dir=cache_dir)
        generator_registry = kwargs.pop("generator_registry", None) or create_default_registry()

        super().__init__(
            config_path=config_path,
            project_root=project_root,
            config=config,
            plugin_manager=plugin_manager,
            generator_registry=generator_registry,
            environment=environment,
            **kwargs
        )

    def build(self, generators: Optional[List] = None) -> Dict[str, Path]:
        """Build the environment by rendering all templates."""
        self.console.print("\n🔨 Starting environment build...")

        # Load plugins
        plugins = self._load_plugins()

        # Build context
        context = self._build_context(plugins)

        # Validate configuration
        if not self._validate_build(plugins, context):
            raise ConfigError("Build validation failed")

        # Create template renderer
        template_renderer = self._create_template_renderer(plugins)

        # Create output manager
        output_manager = self._create_output_manager()

        # Determine generators to use
        if generators is None:
            generators = self._get_generators_from_config()

        # Render templates
        rendered_content = template_renderer.render_templates(self.config.render, context)

        # Post-process with generators
        processed_content = self._post_process_content(rendered_content, generators, context)

        # Write output files
        rendered_files = output_manager.write_rendered_templates(processed_content, self.config.render)

        self.console.print(f"\n✅ Build complete! Generated {len(rendered_files)} files.")
        return rendered_files

    def validate_config(self) -> bool:
        """Validate the current configuration."""
        try:
            plugins = self._load_plugins()
            context = self._build_context(plugins)
            return self._validate_build(plugins, context)
        except Exception as e:
            self.console.print(f"✗ Configuration validation failed: {e}", style="red")
            return False

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

    def dev_mode(self, watch_paths: List[Path] = None) -> None:
        """Start development server with live reload."""
        from .dev.template_tools import DevServer
        
        if watch_paths is None:
            watch_paths = [self.project_root]
            
        dev_server = DevServer(forge=self, watch_paths=watch_paths)
        dev_server.start()

    def _load_plugins(self) -> List[Plugin]:
        """Load all plugins from configuration."""
        if not self.config.plugins:
            raise ConfigError("No plugins configured")

        self.console.print(f"Loading {len(self.config.plugins)} plugins...")
        return self.plugin_manager.load_plugins(self.config.plugins)

    def _build_context(self, plugins: List[Plugin]) -> Dict[str, Any]:
        """Build rendering context using context builder."""
        context_builder = ContextBuilder.create_default(
            config=self.config,
            plugins=plugins,
            project_root=self.project_root,
            config_path=self.config_path,
            environment=self.environment
        )
        
        return context_builder.build_context()

    def _validate_build(self, plugins: List[Plugin], context: Dict[str, Any]) -> bool:
        """Validate build configuration."""
        validation_system = ValidationSystem.create_default(self.project_root)
        
        return validation_system.validate_all(
            config=self.config,
            plugins=plugins,
            render_configs=self.config.render,
            context=context
        )

    def _create_template_renderer(self, plugins: List[Plugin]) -> JinjaTemplateRenderer:
        """Create template renderer with plugin paths."""
        template_paths = []
        for plugin in plugins:
            if plugin.has_templates:
                template_paths.append(plugin.templates_path)

        if not template_paths:
            raise TemplateError("No template directories found in any plugins")

        template_loader = PluginTemplateLoader(template_paths=template_paths)
        return JinjaTemplateRenderer(template_loader=template_loader)

    def _create_output_manager(self) -> OutputManager:
        """Create output manager."""
        return OutputManager.create_filesystem(self.project_root)

    def _get_generators_from_config(self) -> List:
        """Get generators based on render configuration."""
        generators = []
        template_names = [config.template for config in self.config.render]
        
        detected_generators = self.generator_registry.auto_detect_generators(template_names)
        generators.extend(detected_generators)
        
        return generators

    def _post_process_content(
        self, 
        rendered_content: Dict[str, str], 
        generators: List, 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Post-process rendered content with file generators."""
        processed_content = {}
        
        # Create lookup for generators by template name
        generator_map = {gen.template_name: gen for gen in generators}
        
        for template_name, content in rendered_content.items():
            if template_name in generator_map:
                generator = generator_map[template_name]
                processed_content[template_name] = generator.post_process_content(content, context)
            else:
                processed_content[template_name] = content
                
        return processed_content

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
