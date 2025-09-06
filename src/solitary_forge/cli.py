# src/solitary_forge/cli.py
"""CLI interface for solitary-forge."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .exceptions import ConfigError, ForgeError
from .forge import Forge

app = typer.Typer(
    name="solitary-forge", help="Jinja2-based environment generator with Git plugin support", add_completion=False
)
console = Console()


@app.command()
def build(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
) -> None:
    """Build environment files from templates."""
    try:
        forge = Forge(config_path=config_file)
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
        console.print(f"\n📝 Next steps:")
        console.print(f"  1. Edit [cyan]{config_path}[/cyan] to update plugin URLs")
        console.print(f"  2. Run [green]solitary-forge build[/green] to generate files")

    except ConfigError as e:
        console.print(f"[red]Initialization failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    config_file: str = typer.Option(".forge.yml", "--config", "-c", help="Path to forge configuration file"),
) -> None:
    """Validate forge configuration."""
    try:
        forge = Forge(config_path=config_file)
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


@app.command()
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


@app.command()
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
            # console.print(f"\n[cyan]{plugin_name}[/cyan]:")
            console.print(f"\n{plugin_name}:")
            for template in templates:
                console.print(f"  • {template}")

    except ForgeError as e:
        console.print(f"[red]Failed to list templates: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()

