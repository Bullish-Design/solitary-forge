# src/solitary_forge/cli.py
"""Enhanced CLI interface for solitary-forge."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from .exceptions import ConfigError, ForgeError
from .forge import Forge
from .settings import NO_COLOR

app = typer.Typer(
    name="solitary-forge", 
    help="Jinja2-based environment generator with Git plugin support", 
    add_completion=False
)
console = Console(no_color=NO_COLOR)


@app.command()
def build(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
    environment: str = typer.Option("base", "--env", "-e", help="Environment to build for"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be built without writing files"),
) -> None:
    """Build environment files from templates."""
    try:
        forge = Forge(config_path=config_file, environment=environment, dry_run=dry_run)
        rendered_files = forge.build()

        if rendered_files:
            console.print("\n📄 Generated files:")
            for template, output_path in rendered_files.items():
                console.print(f"  [green]✓[/green] {output_path.name}")

    except ForgeError as e:
        console.print(f"[red]Build failed: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init(
    project_dir: str = typer.Argument(".", help="Project directory to initialize"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration"),
) -> None:
    """Initialize a new forge configuration."""
    try:
        config_path = Forge.init_config(project_dir, force=force)
        console.print(f"\n📋 Next steps:")
        console.print(f"  1. Edit [cyan]{config_path}[/cyan] to update plugin URLs")
        console.print(f"  2. Run [green]solitary-forge build[/green] to generate files")

    except ConfigError as e:
        console.print(f"[red]Initialization failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
    environment: str = typer.Option("base", "--env", "-e", help="Environment to validate"),
) -> None:
    """Validate forge configuration."""
    try:
        forge = Forge(config_path=config_file, environment=environment)
        is_valid = forge.validate_config()

        if not is_valid:
            raise typer.Exit(1)

    except ForgeError as e:
        console.print(f"[red]Validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def clean(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
    plugin: Optional[str] = typer.Option(None, "--plugin", "-p", help="Specific plugin to clean (default: all)"),
) -> None:
    """Clean plugin cache."""
    try:
        forge = Forge(config_path=config_file)
        forge.clean(plugin_name=plugin)

    except ForgeError as e:
        console.print(f"[red]Clean failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-plugins")
def list_plugins(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
) -> None:
    """List cached plugins."""
    try:
        forge = Forge(config_path=config_file)
        plugins = forge.list_plugins()

        if not plugins:
            console.print("No cached plugins found")
            return

        table = Table(title="Cached Plugins")
        table.add_column("Plugin Name", style="cyan")

        for plugin in plugins:
            table.add_row(plugin)

        console.print(table)

    except ForgeError as e:
        console.print(f"[red]Failed to list plugins: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-templates")
def list_templates(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
) -> None:
    """List available templates from all plugins."""
    try:
        forge = Forge(config_path=config_file)
        plugin_templates = forge.list_templates()

        if not plugin_templates:
            console.print("No templates found")
            return

        for plugin_name, templates in plugin_templates.items():
            if NO_COLOR:
                console.print(f"\n{plugin_name}:")
            else:
                console.print(f"\n[cyan]{plugin_name}[/cyan]:")
            for template in templates:
                console.print(f"  • {template}")

    except ForgeError as e:
        console.print(f"[red]Failed to list templates: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def dev(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
    environment: str = typer.Option("base", "--env", "-e", help="Environment for development"),
    watch_paths: List[str] = typer.Option(None, "--watch", "-w", help="Additional paths to watch for changes"),
) -> None:
    """Start development server with live reload."""
    try:
        forge = Forge(config_path=config_file, environment=environment)
        
        watch_path_objects = [Path(p) for p in watch_paths] if watch_paths else None
        forge.dev_mode(watch_paths=watch_path_objects)

    except ForgeError as e:
        console.print(f"[red]Dev server failed: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Development server stopped[/yellow]")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query for plugins"),
    file_types: List[str] = typer.Option(None, "--type", "-t", help="Filter by file types"),
) -> None:
    """Search for plugins in registry."""
    try:
        from .installation.plugin_registry import PluginRegistry
        
        registry = PluginRegistry()
        plugins = registry.search_plugins(query, tags=file_types)
        
        if not plugins:
            console.print(f"No plugins found for query: {query}")
            return
            
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Version")
        table.add_column("File Types", style="green")
        
        for plugin in plugins[:10]:  # Limit to top 10 results
            file_types_str = ", ".join(plugin.file_types) if plugin.file_types else "N/A"
            table.add_row(
                plugin.name,
                plugin.description[:50] + "..." if len(plugin.description) > 50 else plugin.description,
                plugin.version,
                file_types_str
            )
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def install(
    plugins: List[str] = typer.Argument(..., help="Plugin names to install"),
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
    version: str = typer.Option("main", "--version", "-v", help="Version to install"),
) -> None:
    """Install plugins from registry."""
    try:
        from .installation.plugin_registry import PluginRegistry
        from .models import PluginConfig
        
        registry = PluginRegistry()
        forge = Forge(config_path=config_file)
        
        # Convert plugin names to configs
        plugin_configs = []
        for plugin_name in plugins:
            metadata = registry.get_plugin_info(plugin_name)
            if not metadata:
                console.print(f"[red]Plugin not found: {plugin_name}[/red]")
                raise typer.Exit(1)
                
            config = registry.create_plugin_config(metadata, version)
            plugin_configs.append(config)
        
        # Install plugins
        installations = forge.plugin_manager.load_plugins(plugin_configs)
        
        console.print(f"[green]Successfully installed {len(installations)} plugins[/green]")
        
    except Exception as e:
        console.print(f"[red]Installation failed: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
