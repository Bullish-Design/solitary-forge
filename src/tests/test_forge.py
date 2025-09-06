# tests/test_forge.py
"""Tests for main Forge orchestrator functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from solitary_forge.exceptions import ConfigError, TemplateError
from solitary_forge.forge import Forge
from solitary_forge.models import ForgeConfig, PluginConfig, RenderConfig
from solitary_forge.plugin import Plugin
from solitary_forge.plugin import PluginManager


class TestForge:
    """Test Forge class functionality."""

    def create_test_config(self, temp_dir: Path) -> Path:
        """Create a test configuration file."""
        config_data = {
            "variables": {"project_name": "test-project", "base_image": "nixos/nix:latest"},
            "plugins": [{"name": "core", "git": "https://github.com/example/core.git", "version": "main"}],
            "render": [{"template": "Dockerfile.j2", "output": "Dockerfile"}],
        }

        config_path = temp_dir / ".forge.yml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        return config_path

    def create_test_plugin(self, cache_dir: Path, templates: dict[str, str]) -> Path:
        """Create a test plugin with templates."""
        plugin_path = cache_dir / "core"
        templates_path = plugin_path / "templates"
        templates_path.mkdir(parents=True)

        for template_name, content in templates.items():
            template_file = templates_path / template_name
            with open(template_file, "w") as f:
                f.write(content)

        return plugin_path

    def test_forge_initialization_success(self):
        """Test successful Forge initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            forge = Forge(config_path=config_path)

            assert forge.config_path == config_path
            assert forge.project_root == temp_path
            assert isinstance(forge.config, ForgeConfig)
            assert forge.config.variables["project_name"] == "test-project"

    def test_forge_initialization_config_not_found(self):
        """Test Forge initialization with missing config file."""
        with pytest.raises(ConfigError, match="Configuration file not found"):
            Forge(config_path="nonexistent.yml")

    def test_forge_initialization_invalid_config(self):
        """Test Forge initialization with invalid config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / ".forge.yml"

            # Create invalid config
            with open(config_path, "w") as f:
                f.write("invalid: yaml: content: [\n")

            with pytest.raises(ConfigError, match="Failed to load configuration"):
                Forge(config_path=config_path)

    @patch("solitary_forge.forge.PluginManager")
    def test_build_success(self, mock_plugin_manager):
        """Test successful build process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            # Mock plugin
            mock_plugin = Mock(spec=Plugin)
            mock_plugin.name = "core"
            mock_plugin.config = {}
            mock_plugin.path = temp_path / "cache" / "core"
            mock_plugin.manifest = None
            mock_plugin.has_templates = True
            mock_plugin.templates_path = mock_plugin.path / "templates"

            # Mock plugin manager
            mock_manager_instance = Mock()
            mock_manager_instance.load_plugins.return_value = [mock_plugin]
            mock_plugin_manager.return_value = mock_manager_instance

            # Create actual template file for Jinja2
            cache_dir = temp_path / ".forge_cache" / "plugins"
            plugin_path = self.create_test_plugin(
                cache_dir, {"Dockerfile.j2": "FROM {{ variables.base_image }}\nWORKDIR /app"}
            )
            mock_plugin.templates_path = plugin_path / "templates"

            forge = Forge(config_path=config_path)
            rendered_files = forge.build()

            assert len(rendered_files) == 1
            assert "Dockerfile.j2" in rendered_files

            # Check output file was created
            output_path = temp_path / "Dockerfile"
            assert output_path.exists()

            # Check template was rendered correctly
            with open(output_path, "r") as f:
                content = f.read()
            assert "FROM nixos/nix:latest" in content
            assert "WORKDIR /app" in content

    @patch("solitary_forge.forge.PluginManager")
    def test_build_template_not_found(self, mock_plugin_manager):
        """Test build fails when template not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            # Mock plugin with no templates
            mock_plugin = Mock(spec=Plugin)
            mock_plugin.name = "core"
            mock_plugin.has_templates = True
            mock_plugin.templates_path = temp_path / "nonexistent"

            mock_manager_instance = Mock()
            mock_manager_instance.load_plugins.return_value = [mock_plugin]
            mock_plugin_manager.return_value = mock_manager_instance

            forge = Forge(config_path=config_path)

            with pytest.raises(TemplateError, match="Template not found"):
                forge.build()

    @patch("solitary_forge.forge.PluginManager")
    def test_build_no_template_paths(self, mock_plugin_manager):
        """Test build fails when no template directories found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            # Mock plugin with no templates
            mock_plugin = Mock(spec=Plugin)
            mock_plugin.name = "core"
            mock_plugin.has_templates = False

            mock_manager_instance = Mock()
            mock_manager_instance.load_plugins.return_value = [mock_plugin]
            mock_plugin_manager.return_value = mock_manager_instance

            forge = Forge(config_path=config_path)

            with pytest.raises(TemplateError, match="No template directories found"):
                forge.build()

    def test_build_context_creation(self):
        """Test build context includes all required data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            forge = Forge(config_path=config_path)

            # Mock plugin
            mock_plugin = Mock(spec=Plugin)
            mock_plugin.name = "core"
            mock_plugin.config = {"key": "value"}
            mock_plugin.path = temp_path / "plugin_path"
            mock_plugin.manifest = None

            context = forge._build_context([mock_plugin])

            assert "variables" in context
            assert context["variables"]["project_name"] == "test-project"
            assert "plugins" in context
            assert "core" in context["plugins"]
            assert context["plugins"]["core"]["config"] == {"key": "value"}
            assert "project_root" in context
            assert "config_path" in context

    @patch("solitary_forge.forge.PluginManager")
    def test_validate_config_success(self, mock_plugin_manager):
        """Test successful configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            # Mock plugin
            mock_plugin = Mock(spec=Plugin)
            mock_plugin.name = "core"
            mock_plugin.has_templates = True
            mock_plugin.templates_path = temp_path / "templates"

            mock_manager_instance = Mock()
            mock_manager_instance.load_plugins.return_value = [mock_plugin]
            mock_plugin_manager.return_value = mock_manager_instance

            # Create actual template
            cache_dir = temp_path / ".forge_cache" / "plugins"
            plugin_path = self.create_test_plugin(cache_dir, {"Dockerfile.j2": "FROM {{ variables.base_image }}"})
            mock_plugin.templates_path = plugin_path / "templates"

            forge = Forge(config_path=config_path)
            is_valid = forge.validate_config()

            assert is_valid is True

    @patch("solitary_forge.forge.PluginManager")
    def test_validate_config_template_missing(self, mock_plugin_manager):
        """Test validation fails when template missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            # Mock plugin with no templates
            mock_plugin = Mock(spec=Plugin)
            mock_plugin.name = "core"
            mock_plugin.has_templates = True
            mock_plugin.templates_path = temp_path / "nonexistent"

            mock_manager_instance = Mock()
            mock_manager_instance.load_plugins.return_value = [mock_plugin]
            mock_plugin_manager.return_value = mock_manager_instance

            forge = Forge(config_path=config_path)
            is_valid = forge.validate_config()

            assert is_valid is False

    def test_clean_delegates_to_plugin_manager(self):
        """Test clean delegates to plugin manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            forge = Forge(config_path=config_path)

            with patch.object(forge.plugin_manager, "clean_cache") as mock_clean:
                forge.clean("test-plugin")
                mock_clean.assert_called_once_with("test-plugin")

    def test_list_plugins_delegates_to_plugin_manager(self):
        """Test list_plugins delegates to plugin manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            forge = Forge(config_path=config_path)

            with patch.object(forge.plugin_manager, "list_cached_plugins") as mock_list:
                mock_list.return_value = ["plugin1", "plugin2"]
                result = forge.list_plugins()

                assert result == ["plugin1", "plugin2"]
                mock_list.assert_called_once()

    def test_list_templates(self):
        """Test listing templates from all plugins."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self.create_test_config(temp_path)

            # Mock plugins
            mock_plugin1 = Mock(spec=Plugin)
            mock_plugin1.name = "core"
            mock_plugin1.list_templates.return_value = ["Dockerfile.j2", "compose.j2"]

            mock_plugin2 = Mock(spec=Plugin)
            mock_plugin2.name = "python"
            mock_plugin2.list_templates.return_value = ["requirements.txt.j2"]

            # Mock plugin manager
            mock_plugin_manager = Mock(spec=PluginManager)
            mock_plugin_manager.load_plugins.return_value = [mock_plugin1, mock_plugin2]

            forge = Forge(config_path=config_path, plugin_manager=mock_plugin_manager)
            templates = forge.list_templates()

            assert len(templates) == 2
            assert templates["core"] == ["Dockerfile.j2", "compose.j2"]
            assert templates["python"] == ["requirements.txt.j2"]

    def test_init_config_success(self):
        """Test successful configuration initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_path = Forge.init_config(temp_path)

            assert config_path.exists()
            assert config_path.name == ".forge.yml"

            # Verify config content
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            assert "variables" in config_data
            assert "plugins" in config_data
            assert "render" in config_data
            assert config_data["variables"]["project_name"] == temp_path.name

    def test_init_config_exists_no_force(self):
        """Test initialization fails when config exists without force."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / ".forge.yml"
            config_path.touch()  # Create existing file

            with pytest.raises(ConfigError, match="Configuration already exists"):
                Forge.init_config(temp_path, force=False)

    def test_init_config_exists_with_force(self):
        """Test initialization succeeds when config exists with force."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / ".forge.yml"

            # Create existing config
            with open(config_path, "w") as f:
                f.write("old: config")

            new_config_path = Forge.init_config(temp_path, force=True)

            assert new_config_path == config_path

            # Verify old config was overwritten
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
            assert "old" not in config_data
            assert "variables" in config_data
