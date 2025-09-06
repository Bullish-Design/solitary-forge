# tests/test_cli.py
"""Tests for CLI interface functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from solitary_forge.cli import app
from solitary_forge.exceptions import ConfigError, ForgeError


class TestCLI:
    """Test CLI commands functionality."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("solitary_forge.cli.Forge")
    def test_build_command_success(self, mock_forge):
        """Test successful build command."""
        mock_forge_instance = Mock()
        mock_forge_instance.build.return_value = {
            "Dockerfile.j2": Path("Dockerfile"),
            "compose.j2": Path("docker-compose.yml"),
        }
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["build"])

        assert result.exit_code == 0
        assert "Generated files:" in result.stdout
        assert "Dockerfile" in result.stdout
        mock_forge.assert_called_once_with(config_path=".forge.yml")
        mock_forge_instance.build.assert_called_once()

    @patch("solitary_forge.cli.Forge")
    def test_build_command_with_config(self, mock_forge):
        """Test build command with custom config file."""
        mock_forge_instance = Mock()
        mock_forge_instance.build.return_value = {}
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["build", "--config", "custom.yml"])

        assert result.exit_code == 0
        mock_forge.assert_called_once_with(config_path="custom.yml")

    @patch("solitary_forge.cli.Forge")
    def test_build_command_forge_error(self, mock_forge):
        """Test build command with ForgeError."""
        mock_forge.side_effect = ForgeError("Build failed")

        result = self.runner.invoke(app, ["build"])

        assert result.exit_code == 1
        assert "Build failed: Build failed" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_build_command_unexpected_error(self, mock_forge):
        """Test build command with unexpected error."""
        mock_forge.side_effect = ValueError("Unexpected error")

        result = self.runner.invoke(app, ["build"])

        assert result.exit_code == 1
        assert "Unexpected error: Unexpected error" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_init_command_success(self, mock_forge):
        """Test successful init command."""
        mock_forge.init_config.return_value = Path(".forge.yml")

        result = self.runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Next steps:" in result.stdout
        assert "solitary-forge build" in result.stdout
        mock_forge.init_config.assert_called_once_with(".", force=False)

    @patch("solitary_forge.cli.Forge")
    def test_init_command_with_directory(self, mock_forge):
        """Test init command with custom directory."""
        mock_forge.init_config.return_value = Path("project/.forge.yml")

        result = self.runner.invoke(app, ["init", "project"])

        assert result.exit_code == 0
        mock_forge.init_config.assert_called_once_with("project", force=False)

    @patch("solitary_forge.cli.Forge")
    def test_init_command_with_force(self, mock_forge):
        """Test init command with force flag."""
        mock_forge.init_config.return_value = Path(".forge.yml")

        result = self.runner.invoke(app, ["init", "--force"])

        assert result.exit_code == 0
        mock_forge.init_config.assert_called_once_with(".", force=True)

    @patch("solitary_forge.cli.Forge")
    def test_init_command_config_error(self, mock_forge):
        """Test init command with ConfigError."""
        mock_forge.init_config.side_effect = ConfigError("Initialization failed")

        result = self.runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "Initialization failed: Initialization failed" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_validate_command_success(self, mock_forge):
        """Test successful validate command."""
        mock_forge_instance = Mock()
        mock_forge_instance.validate_config.return_value = True
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["validate"])

        assert result.exit_code == 0
        mock_forge.assert_called_once_with(config_path=".forge.yml")
        mock_forge_instance.validate_config.assert_called_once()

    @patch("solitary_forge.cli.Forge")
    def test_validate_command_invalid(self, mock_forge):
        """Test validate command with invalid configuration."""
        mock_forge_instance = Mock()
        mock_forge_instance.validate_config.return_value = False
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["validate"])

        assert result.exit_code == 1

    @patch("solitary_forge.cli.Forge")
    def test_validate_command_forge_error(self, mock_forge):
        """Test validate command with ForgeError."""
        mock_forge.side_effect = ForgeError("Validation failed")

        result = self.runner.invoke(app, ["validate"])

        assert result.exit_code == 1
        assert "Validation failed: Validation failed" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_clean_command_success(self, mock_forge):
        """Test successful clean command."""
        mock_forge_instance = Mock()
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["clean"])

        assert result.exit_code == 0
        mock_forge.assert_called_once_with(config_path=".forge.yml")
        mock_forge_instance.clean.assert_called_once_with(plugin_name=None)

    @patch("solitary_forge.cli.Forge")
    def test_clean_command_specific_plugin(self, mock_forge):
        """Test clean command for specific plugin."""
        mock_forge_instance = Mock()
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["clean", "--plugin", "core"])

        assert result.exit_code == 0
        mock_forge_instance.clean.assert_called_once_with(plugin_name="core")

    @patch("solitary_forge.cli.Forge")
    def test_clean_command_forge_error(self, mock_forge):
        """Test clean command with ForgeError."""
        mock_forge.side_effect = ForgeError("Clean failed")

        result = self.runner.invoke(app, ["clean"])

        assert result.exit_code == 1
        assert "Clean failed: Clean failed" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_list_plugins_command_success(self, mock_forge):
        """Test successful list-plugins command."""
        mock_forge_instance = Mock()
        mock_forge_instance.list_plugins.return_value = ["core", "python"]
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["list-plugins"])

        assert result.exit_code == 0
        assert "Cached Plugins" in result.stdout
        assert "core" in result.stdout
        assert "python" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_list_plugins_command_empty(self, mock_forge):
        """Test list-plugins command with no cached plugins."""
        mock_forge_instance = Mock()
        mock_forge_instance.list_plugins.return_value = []
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["list-plugins"])

        assert result.exit_code == 0
        assert "No cached plugins found" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_list_plugins_command_forge_error(self, mock_forge):
        """Test list-plugins command with ForgeError."""
        mock_forge.side_effect = ForgeError("Failed to list plugins")

        result = self.runner.invoke(app, ["list-plugins"])

        assert result.exit_code == 1
        assert "Failed to list plugins: Failed to list plugins" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_list_templates_command_success(self, mock_forge):
        """Test successful list-templates command."""
        mock_forge_instance = Mock()
        mock_forge_instance.list_templates.return_value = {
            "core": ["Dockerfile.j2", "compose.j2"],
            "python": ["requirements.txt.j2"],
        }
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["list-templates"])

        assert result.exit_code == 0
        # Strip ANSI color codes for assertion
        clean_output = result.stdout.replace("\x1b[36m", "").replace("\x1b[0m", "")
        assert "core:" in clean_output
        assert "Dockerfile.j2" in result.stdout
        assert "python:" in result.stdout
        assert "requirements.txt.j2" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_list_templates_command_empty(self, mock_forge):
        """Test list-templates command with no templates."""
        mock_forge_instance = Mock()
        mock_forge_instance.list_templates.return_value = {}
        mock_forge.return_value = mock_forge_instance

        result = self.runner.invoke(app, ["list-templates"])

        assert result.exit_code == 0
        assert "No templates found" in result.stdout

    @patch("solitary_forge.cli.Forge")
    def test_list_templates_command_forge_error(self, mock_forge):
        """Test list-templates command with ForgeError."""
        mock_forge.side_effect = ForgeError("Failed to list templates")

        result = self.runner.invoke(app, ["list-templates"])

        assert result.exit_code == 1
        assert "Failed to list templates: Failed to list templates" in result.stdout

    def test_help_output(self):
        """Test CLI help output."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Jinja2-based environment generator" in result.stdout
        assert "build" in result.stdout
        assert "init" in result.stdout
        assert "validate" in result.stdout
        assert "clean" in result.stdout

    def test_command_help_output(self):
        """Test individual command help output."""
        result = self.runner.invoke(app, ["build", "--help"])

        assert result.exit_code == 0
        assert "Build environment files from templates" in result.stdout
        assert "--config" in result.stdout
