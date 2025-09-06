# tests/test_models.py
"""Tests for Pydantic models."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from solitary_forge.models import ForgeConfig, PluginConfig, PluginManifest, RenderConfig


class TestPluginConfig:
    """Test PluginConfig model validation."""

    def test_valid_plugin_config(self):
        """Test valid plugin configuration."""
        config = PluginConfig(
            name="test-plugin",
            git="https://github.com/example/plugin.git",
            version="main",
            config={"key": "value"}
        )
        assert config.name == "test-plugin"
        assert config.git == "https://github.com/example/plugin.git"
        assert config.version == "main"
        assert config.config == {"key": "value"}

    def test_plugin_config_defaults(self):
        """Test plugin configuration defaults."""
        config = PluginConfig(name="test", git="https://github.com/example/test.git")
        assert config.version == "main"
        assert config.config == {}

    def test_empty_name_validation(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValidationError):
            PluginConfig(name="", git="https://github.com/example/test.git")

    def test_empty_git_validation(self):
        """Test validation fails with empty git URL."""
        with pytest.raises(ValidationError):
            PluginConfig(name="test", git="")

    def test_whitespace_trimming(self):
        """Test whitespace is trimmed from name and git URL."""
        config = PluginConfig(name="  test  ", git="  https://github.com/example/test.git  ")
        assert config.name == "test"
        assert config.git == "https://github.com/example/test.git"


class TestRenderConfig:
    """Test RenderConfig model validation."""

    def test_valid_render_config(self):
        """Test valid render configuration."""
        config = RenderConfig(template="Dockerfile.j2", output="Dockerfile")
        assert config.template == "Dockerfile.j2"
        assert config.output == "Dockerfile"

    def test_empty_template_validation(self):
        """Test validation fails with empty template."""
        with pytest.raises(ValidationError):
            RenderConfig(template="", output="Dockerfile")

    def test_empty_output_validation(self):
        """Test validation fails with empty output."""
        with pytest.raises(ValidationError):
            RenderConfig(template="Dockerfile.j2", output="")

    def test_whitespace_trimming(self):
        """Test whitespace is trimmed from paths."""
        config = RenderConfig(template="  Dockerfile.j2  ", output="  Dockerfile  ")
        assert config.template == "Dockerfile.j2"
        assert config.output == "Dockerfile"


class TestForgeConfig:
    """Test ForgeConfig model validation."""

    def test_valid_forge_config(self):
        """Test valid forge configuration."""
        config = ForgeConfig(
            variables={"project": "test"},
            plugins=[PluginConfig(name="core", git="https://github.com/example/core.git")],
            render=[RenderConfig(template="test.j2", output="test")]
        )
        assert config.variables == {"project": "test"}
        assert len(config.plugins) == 1
        assert len(config.render) == 1

    def test_forge_config_defaults(self):
        """Test forge configuration defaults."""
        config = ForgeConfig()
        assert config.variables == {}
        assert config.plugins == []
        assert config.render == []

    def test_no_plugins_validation(self):
        """Test validation fails with no plugins."""
        with pytest.raises(ValidationError, match="At least one plugin must be specified"):
            ForgeConfig(
                plugins=[],
                render=[RenderConfig(template="test.j2", output="test")]
            )

    def test_no_render_validation(self):
        """Test validation fails with no render configurations."""
        with pytest.raises(ValidationError, match="At least one render configuration must be specified"):
            ForgeConfig(
                plugins=[PluginConfig(name="core", git="https://github.com/example/core.git")],
                render=[]
            )

    def test_duplicate_plugin_names(self):
        """Test validation fails with duplicate plugin names."""
        with pytest.raises(ValidationError, match="Plugin names must be unique"):
            ForgeConfig(
                plugins=[
                    PluginConfig(name="core", git="https://github.com/example/core1.git"),
                    PluginConfig(name="core", git="https://github.com/example/core2.git"),
                ],
                render=[RenderConfig(template="test.j2", output="test")]
            )

    def test_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "variables": {"project_name": "test"},
            "plugins": [{"name": "core", "git": "https://github.com/example/core.git"}],
            "render": [{"template": "Dockerfile.j2", "output": "Dockerfile"}]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            config = ForgeConfig.from_yaml_file(config_path)
            assert config.variables["project_name"] == "test"
            assert len(config.plugins) == 1
            assert config.plugins[0].name == "core"
        finally:
            config_path.unlink()

    def test_from_yaml_file_not_found(self):
        """Test error when YAML file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ForgeConfig.from_yaml_file(Path("nonexistent.yml"))

    def test_from_yaml_file_invalid_yaml(self):
        """Test error with invalid YAML content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: [\n")
            config_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                ForgeConfig.from_yaml_file(config_path)
        finally:
            config_path.unlink()


class TestPluginManifest:
    """Test PluginManifest model validation."""

    def test_valid_plugin_manifest(self):
        """Test valid plugin manifest."""
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            dependencies=["other-plugin"]
        )
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "Test plugin"
        assert manifest.dependencies == ["other-plugin"]

    def test_plugin_manifest_defaults(self):
        """Test plugin manifest defaults."""
        manifest = PluginManifest(name="test", version="1.0.0")
        assert manifest.description == ""
        assert manifest.dependencies == []

    def test_from_yaml_file(self):
        """Test loading manifest from YAML file."""
        manifest_data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "dependencies": ["dep1", "dep2"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(manifest_data, f)
            manifest_path = Path(f.name)
        
        try:
            manifest = PluginManifest.from_yaml_file(manifest_path)
            assert manifest.name == "test-plugin"
            assert manifest.version == "1.0.0"
            assert len(manifest.dependencies) == 2
        finally:
            manifest_path.unlink()

    def test_from_yaml_file_not_found(self):
        """Test error when manifest file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            PluginManifest.from_yaml_file(Path("nonexistent.yml"))
