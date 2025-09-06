#!/usr/bin/env python3
# src/tests/simple_test.py
"""
Simple test that bypasses Git operations by directly using local plugin directories.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from solitary_forge.plugin import Plugin, PluginManager
from solitary_forge.forge import Forge
from solitary_forge.models import ForgeConfig, PluginConfig, RenderConfig
from jinja2 import Environment, FileSystemLoader


def create_local_plugin(temp_dir: Path) -> Path:
    """Create a local plugin directory (no Git)."""
    plugin_dir = temp_dir / "core"
    plugin_dir.mkdir(parents=True)

    # Plugin manifest
    (plugin_dir / "plugin.yml").write_text("""name: 'core'
version: '1.0.0'
description: 'Core plugin for testing'
""")

    # Templates directory
    templates_dir = plugin_dir / "templates"
    templates_dir.mkdir()

    # Dockerfile template
    (templates_dir / "Dockerfile.j2").write_text("""FROM {{ variables.base_image }}
WORKDIR {{ variables.workdir }}
RUN echo "Project: {{ variables.project_name }}"
CMD ["tail", "-f", "/dev/null"]
""")

    # docker-compose template
    (templates_dir / "docker-compose.yml.j2").write_text("""services:
  dev:
    container_name: {{ variables.container_name }}
    build: .
    working_dir: {{ variables.workdir }}
    volumes:
      - .:{{ variables.workdir }}
""")

    return plugin_dir


def test_plugin_loading():
    """Test loading plugins directly without Git."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        plugin_dir = create_local_plugin(temp_path)

        # Create plugin directly
        plugin = Plugin(name="core", path=plugin_dir, config={})

        plugin.load_manifest()

        print(f"✓ Plugin loaded: {plugin.name}")
        print(f"✓ Templates: {plugin.list_templates()}")

        assert plugin.has_templates
        assert len(plugin.list_templates()) == 2


def test_template_rendering():
    """Test template rendering directly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        plugin_dir = create_local_plugin(temp_path)

        # Create Jinja2 environment
        env = Environment(loader=FileSystemLoader(str(plugin_dir / "templates")), trim_blocks=True, lstrip_blocks=True)

        # Test context
        context = {
            "variables": {
                "base_image": "nixos/nix:latest",
                "workdir": "/workspace",
                "project_name": "test-project",
                "container_name": "test-dev",
            }
        }

        # Render Dockerfile
        template = env.get_template("Dockerfile.j2")
        result = template.render(context)

        print("✓ Template rendered:")
        print(result)

        assert "test-project" in result
        assert "/workspace" in result


def test_config_parsing():
    """Test configuration parsing."""
    config_data = {
        "variables": {"project_name": "test-project", "base_image": "nixos/nix:latest"},
        "plugins": [{"name": "core", "git": "https://example.com/core.git", "version": "main"}],
        "render": [{"template": "Dockerfile.j2", "output": "Dockerfile"}],
    }

    config = ForgeConfig.model_validate(config_data)

    print(f"✓ Config parsed: {len(config.plugins)} plugins, {len(config.render)} renders")

    assert config.variables["project_name"] == "test-project"
    assert len(config.plugins) == 1
    assert config.plugins[0].name == "core"


def test_forge_init():
    """Test forge initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        config_path = Forge.init_config(temp_path, force=True)

        print(f"✓ Config initialized at: {config_path}")

        assert config_path.exists()

        # Try to load the config
        config = ForgeConfig.from_yaml_file(config_path)
        print(f"✓ Config loaded: {config.variables}")


def main():
    """Run all tests."""
    tests = [test_plugin_loading, test_template_rendering, test_config_parsing, test_forge_init]

    for test in tests:
        try:
            print(f"\n🧪 Running {test.__name__}...")
            test()
            print(f"✅ {test.__name__} passed")
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            raise

    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    main()
