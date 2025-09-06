# src/examples/demo.py
"""
Minimal example script demonstrating all solitary-forge functionality.

This script demonstrates:
- Configuration initialization
- Plugin management and caching
- Template rendering
- Validation
- Listing operations
- Error handling

Requirements:
    solitary-forge>=0.1.0
"""
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "solitary-forge>=0.1.0",
#     "rich>=13.0.0",
# ]
# ///

from __future__ import annotations

import tempfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from solitary_forge import Forge, ForgeConfig, PluginConfig, RenderConfig
from solitary_forge.exceptions import ConfigError, ForgeError, PluginError


def main():
    """Demonstrate all solitary-forge functionality."""
    console = Console()
    
    console.print(Panel.fit("🔨 Solitary Forge Demo", style="bold blue"))
    
    # Create temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        console.print(f"\n📁 Working in: {workspace}")
        
        # Create mock plugin repository
        mock_plugin_dir = create_mock_plugin(workspace)
        console.print(f"📦 Created mock plugin at: {mock_plugin_dir}")
        
        # 1. Demonstrate configuration initialization
        console.print("\n" + "="*50)
        console.print("1. Configuration Initialization", style="bold cyan")
        console.print("="*50)
        
        try:
            config_path = Forge.init_config(workspace, force=True)
            console.print(f"✅ Initialized config: {config_path}")
            
            # Customize the config to use our mock plugin
            customize_config(config_path, mock_plugin_dir)
            console.print("✅ Customized config with mock plugin")
            
        except ConfigError as e:
            console.print(f"❌ Config initialization failed: {e}", style="red")
            return
        
        # 2. Demonstrate configuration loading and validation
        console.print("\n" + "="*50)
        console.print("2. Configuration Loading & Validation", style="bold cyan")
        console.print("="*50)
        
        try:
            forge = Forge(config_path=config_path)
            console.print("✅ Configuration loaded successfully")
            
            # Show configuration details
            show_config_details(console, forge.config)
            
            # Validate configuration
            is_valid = forge.validate_config()
            if is_valid:
                console.print("✅ Configuration is valid")
            else:
                console.print("❌ Configuration validation failed", style="red")
                
        except (ConfigError, ForgeError) as e:
            console.print(f"❌ Configuration error: {e}", style="red")
            return
        
        # 3. Demonstrate plugin management
        console.print("\n" + "="*50)
        console.print("3. Plugin Management", style="bold cyan")
        console.print("="*50)
        
        try:
            # List plugins before build (should be empty)
            plugins_before = forge.list_plugins()
            console.print(f"📦 Cached plugins before build: {plugins_before}")
            
            # Build (which loads plugins)
            console.print("\n🏗️  Building environment...")
            rendered_files = forge.build()
            
            # Show build results
            show_build_results(console, rendered_files, workspace)
            
            # List plugins after build
            plugins_after = forge.list_plugins()
            console.print(f"\n📦 Cached plugins after build: {plugins_after}")
            
            # List available templates
            templates = forge.list_templates()
            show_templates(console, templates)
            
        except (PluginError, ForgeError) as e:
            console.print(f"❌ Plugin/Build error: {e}", style="red")
            return
        
        # 4. Demonstrate cache management
        console.print("\n" + "="*50)
        console.print("4. Cache Management", style="bold cyan")
        console.print("="*50)
        
        try:
            # Show cache before cleaning
            console.print("🧹 Cache before cleaning:")
            console.print(f"   Cached plugins: {forge.list_plugins()}")
            
            # Clean specific plugin
            if plugins_after:
                plugin_to_clean = plugins_after[0]
                forge.clean(plugin_name=plugin_to_clean)
                console.print(f"✅ Cleaned plugin: {plugin_to_clean}")
                console.print(f"   Remaining plugins: {forge.list_plugins()}")
            
            # Clean all cache
            forge.clean()
            console.print("✅ Cleaned all plugin cache")
            console.print(f"   Remaining plugins: {forge.list_plugins()}")
            
        except ForgeError as e:
            console.print(f"❌ Cache management error: {e}", style="red")
        
        # 5. Demonstrate programmatic configuration
        console.print("\n" + "="*50)
        console.print("5. Programmatic Configuration", style="bold cyan")
        console.print("="*50)
        
        try:
            # Create configuration programmatically
            programmatic_config = ForgeConfig(
                variables={
                    "project_name": "programmatic-demo",
                    "base_image": "alpine:latest",
                    "workdir": "/app"
                },
                plugins=[
                    PluginConfig(
                        name="demo-plugin",
                        git=f"file://{mock_plugin_dir}",
                        version="main",
                        config={"feature_enabled": True}
                    )
                ],
                render=[
                    RenderConfig(template="simple.j2", output="simple.txt")
                ]
            )
            
            console.print("✅ Created programmatic configuration")
            show_config_details(console, programmatic_config)
            
        except Exception as e:
            console.print(f"❌ Programmatic configuration error: {e}", style="red")
        
        console.print("\n" + "="*50)
        console.print("🎉 Demo completed successfully!", style="bold green")
        console.print("="*50)


def create_mock_plugin(workspace: Path) -> Path:
    """Create a mock plugin for demonstration."""
    plugin_dir = workspace / "mock-plugin"
    templates_dir = plugin_dir / "templates"
    templates_dir.mkdir(parents=True)
    
    # Create simple templates
    templates = {
        "Dockerfile.j2": """FROM {{ variables.base_image }}

WORKDIR {{ variables.workdir | default("/workspace") }}

# Project: {{ variables.project_name }}
RUN echo "Setting up {{ variables.project_name }}"

{% if variables.packages %}
# Install packages
{% for package in variables.packages %}
RUN apk add --no-cache {{ package }}
{% endfor %}
{% endif %}

CMD ["sh", "-c", "echo 'Hello from {{ variables.project_name }}'"]
""",
        "docker-compose.yml.j2": """version: '3.8'

services:
  {{ variables.project_name | replace("-", "_") }}:
    build: .
    container_name: {{ variables.project_name }}-dev
    working_dir: {{ variables.workdir | default("/workspace") }}
    volumes:
      - .{{ variables.workdir | default("/workspace") }}
    environment:
      - PROJECT_NAME={{ variables.project_name }}
    ports:
      - "8000:8000"
""",
        "simple.j2": """Simple template demonstration:

Project: {{ variables.project_name }}
Base Image: {{ variables.base_image }}
Working Directory: {{ variables.workdir }}

{% if plugins %}
Configured Plugins:
{% for plugin_name, plugin_data in plugins.items() %}
- {{ plugin_name }}: {{ plugin_data.config }}
{% endfor %}
{% endif %}
"""
    }
    
    for filename, content in templates.items():
        template_path = templates_dir / filename
        with open(template_path, 'w') as f:
            f.write(content)
    
    # Create plugin manifest
    manifest = {
        "name": "mock-plugin",
        "version": "1.0.0",
        "description": "Mock plugin for demonstration purposes",
        "dependencies": []
    }
    
    import yaml
    manifest_path = plugin_dir / "plugin.yml"
    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f)
    
    # Initialize as git repo (mock)
    git_dir = plugin_dir / ".git"
    git_dir.mkdir()
    
    return plugin_dir


def customize_config(config_path: Path, plugin_dir: Path) -> None:
    """Customize the generated config to use our mock plugin."""
    import yaml
    
    # Load existing config
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Update with our mock plugin
    config_data["variables"]["packages"] = ["curl", "git"]
    config_data["plugins"] = [
        {
            "name": "mock-plugin",
            "git": f"file://{plugin_dir}",
            "version": "main",
            "config": {"demo_mode": True}
        }
    ]
    
    # Save updated config
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)


def show_config_details(console: Console, config: ForgeConfig) -> None:
    """Display configuration details in a formatted table."""
    table = Table(title="Configuration Details")
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="yellow")
    table.add_column("Value", style="green")
    
    # Variables
    for key, value in config.variables.items():
        table.add_row("Variables", key, str(value))
    
    # Plugins
    for plugin in config.plugins:
        table.add_row("Plugin", "name", plugin.name)
        table.add_row("", "git", plugin.git)
        table.add_row("", "version", plugin.version)
        if plugin.config:
            table.add_row("", "config", str(plugin.config))
    
    # Render configurations
    for render_config in config.render:
        table.add_row("Render", "template", render_config.template)
        table.add_row("", "output", render_config.output)
    
    console.print(table)


def show_build_results(console: Console, rendered_files: dict[str, Path], workspace: Path) -> None:
    """Display build results and generated file contents."""
    console.print(f"\n✅ Build completed! Generated {len(rendered_files)} files:")
    
    for template, output_path in rendered_files.items():
        console.print(f"  📄 {template} → {output_path.name}")
        
        # Show file content preview
        if output_path.exists():
            with open(output_path, 'r') as f:
                content = f.read()
            
            # Show first few lines
            lines = content.split('\n')[:10]
            preview = '\n'.join(lines)
            if len(content.split('\n')) > 10:
                preview += "\n... (truncated)"
            
            console.print(Panel(preview, title=f"Preview: {output_path.name}", expand=False))


def show_templates(console: Console, templates: dict[str, list[str]]) -> None:
    """Display available templates in a formatted table."""
    if not templates:
        console.print("📄 No templates found")
        return
    
    table = Table(title="Available Templates")
    table.add_column("Plugin", style="cyan")
    table.add_column("Templates", style="yellow")
    
    for plugin_name, template_list in templates.items():
        template_str = '\n'.join(template_list)
        table.add_row(plugin_name, template_str)
    
    console.print(table)


if __name__ == "__main__":
    main()
