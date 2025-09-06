# tests/test_plugin.py
"""Tests for plugin management functionality."""
from __future__ import annotations

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import yaml
from git import Repo

from solitary_forge.exceptions import GitOperationError, PluginError
from solitary_forge.models import PluginConfig, PluginManifest
from solitary_forge.plugin import Plugin, PluginManager


class TestPlugin:
    """Test Plugin class functionality."""

    def test_plugin_creation(self):
        """Test plugin creation with basic properties."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            plugin_path.mkdir()
            
            plugin = Plugin(name="test", path=plugin_path)
            assert plugin.name == "test"
            assert plugin.path == plugin_path
            assert plugin.config == {}
            assert plugin.manifest is None

    def test_templates_path_property(self):
        """Test templates_path property."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            plugin = Plugin(name="test", path=plugin_path)
            
            expected_templates = plugin_path / "templates"
            assert plugin.templates_path == expected_templates

    def test_has_templates_true(self):
        """Test has_templates returns True when templates directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            templates_path = plugin_path / "templates"
            templates_path.mkdir(parents=True)
            
            plugin = Plugin(name="test", path=plugin_path)
            assert plugin.has_templates is True

    def test_has_templates_false(self):
        """Test has_templates returns False when templates directory missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            plugin_path.mkdir()
            
            plugin = Plugin(name="test", path=plugin_path)
            assert plugin.has_templates is False

    def test_load_manifest_success(self):
        """Test loading plugin manifest successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            plugin_path.mkdir()
            
            manifest_data = {
                "name": "test-plugin",
                "version": "1.0.0",
                "description": "Test plugin"
            }
            manifest_path = plugin_path / "plugin.yml"
            with open(manifest_path, 'w') as f:
                yaml.dump(manifest_data, f)
            
            plugin = Plugin(name="test", path=plugin_path)
            manifest = plugin.load_manifest()
            
            assert manifest is not None
            assert manifest.name == "test-plugin"
            assert manifest.version == "1.0.0"
            assert plugin.manifest == manifest

    def test_load_manifest_not_found(self):
        """Test loading manifest when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            plugin_path.mkdir()
            
            plugin = Plugin(name="test", path=plugin_path)
            manifest = plugin.load_manifest()
            
            assert manifest is None
            assert plugin.manifest is None

    def test_load_manifest_invalid(self):
        """Test error when loading invalid manifest."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            plugin_path.mkdir()
            
            manifest_path = plugin_path / "plugin.yml"
            with open(manifest_path, 'w') as f:
                f.write("invalid: yaml: content: [\n")
            
            plugin = Plugin(name="test", path=plugin_path)
            
            with pytest.raises(PluginError, match="Failed to load manifest"):
                plugin.load_manifest()

    def test_list_templates_with_templates(self):
        """Test listing templates when templates exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            templates_path = plugin_path / "templates"
            templates_path.mkdir(parents=True)
            
            # Create test templates
            (templates_path / "Dockerfile.j2").touch()
            (templates_path / "docker-compose.yml.j2").touch()
            subdir = templates_path / "subdir"
            subdir.mkdir()
            (subdir / "config.j2").touch()
            
            plugin = Plugin(name="test", path=plugin_path)
            templates = plugin.list_templates()
            
            assert len(templates) == 3
            assert "Dockerfile.j2" in templates
            assert "docker-compose.yml.j2" in templates
            assert "subdir/config.j2" in templates

    def test_list_templates_no_templates(self):
        """Test listing templates when no templates directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "test-plugin"
            plugin_path.mkdir()
            
            plugin = Plugin(name="test", path=plugin_path)
            templates = plugin.list_templates()
            
            assert templates == []


class TestPluginManager:
    """Test PluginManager class functionality."""

    def test_plugin_manager_creation(self):
        """Test plugin manager creation and cache directory setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            assert manager.cache_dir == cache_dir
            assert cache_dir.exists()

    @patch('solitary_forge.plugin.Repo')
    def test_clone_plugin_success(self, mock_repo):
        """Test successful plugin cloning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            config = PluginConfig(
                name="test-plugin",
                git="https://github.com/example/test.git",
                version="main"
            )
            
            # Mock successful clone
            mock_repo_instance = Mock()
            mock_repo.clone_from.return_value = mock_repo_instance
            
            target_path = cache_dir / "test-plugin"
            result = manager._clone_plugin(config, target_path)
            
            assert result == target_path
            mock_repo.clone_from.assert_called_once_with(config.git, target_path)
            mock_repo_instance.git.checkout.assert_called_once_with("main")

    @patch('solitary_forge.plugin.Repo')
    def test_clone_plugin_failure(self, mock_repo):
        """Test plugin cloning failure and cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            config = PluginConfig(
                name="test-plugin",
                git="https://github.com/example/test.git"
            )
            
            # Mock clone failure
            from git.exc import GitCommandError
            mock_repo.clone_from.side_effect = GitCommandError("clone", "error")
            
            target_path = cache_dir / "test-plugin"
            target_path.mkdir(parents=True)  # Create partial directory
            
            with pytest.raises(GitOperationError):
                manager._clone_plugin(config, target_path)
            
            # Verify cleanup
            assert not target_path.exists()

    @patch('solitary_forge.plugin.Repo')
    def test_update_plugin_success(self, mock_repo):
        """Test successful plugin update."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            config = PluginConfig(
                name="test-plugin",
                git="https://github.com/example/test.git",
                version="v1.0.0"
            )
            
            plugin_path = cache_dir / "test-plugin"
            plugin_path.mkdir(parents=True)
            
            # Mock existing repo
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_origin = Mock()
            mock_repo_instance.remotes.origin = mock_origin
            
            result = manager._update_plugin(config, plugin_path)
            
            assert result == plugin_path
            mock_origin.fetch.assert_called_once()
            mock_repo_instance.git.checkout.assert_called_once_with("v1.0.0")

    @patch('solitary_forge.plugin.Repo')
    @patch('solitary_forge.plugin.shutil.rmtree')
    def test_update_plugin_invalid_repo(self, mock_rmtree, mock_repo):
        """Test update when directory isn't a valid git repo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            config = PluginConfig(
                name="test-plugin",
                git="https://github.com/example/test.git"
            )
            
            plugin_path = cache_dir / "test-plugin"
            
            # Mock invalid repo error, then successful clone
            from git.exc import InvalidGitRepositoryError
            mock_repo.side_effect = [InvalidGitRepositoryError(), Mock()]
            
            with patch.object(manager, '_clone_plugin') as mock_clone:
                mock_clone.return_value = plugin_path
                result = manager._update_plugin(config, plugin_path)
                
                assert result == plugin_path
                mock_rmtree.assert_called_once_with(plugin_path)
                mock_clone.assert_called_once_with(config, plugin_path)

    def test_load_plugins_success(self):
        """Test successful loading of plugins."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            # Create mock plugin directory with templates
            plugin_path = cache_dir / "test-plugin"
            templates_path = plugin_path / "templates"
            templates_path.mkdir(parents=True)
            (templates_path / "test.j2").touch()
            
            config = PluginConfig(
                name="test-plugin",
                git="https://github.com/example/test.git"
            )
            
            with patch.object(manager, '_ensure_plugin_available') as mock_ensure:
                mock_ensure.return_value = plugin_path
                
                plugins = manager.load_plugins([config])
                
                assert len(plugins) == 1
                assert plugins[0].name == "test-plugin"
                assert plugins[0].path == plugin_path

    def test_load_plugins_no_templates(self):
        """Test loading plugin fails when no templates directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            # Create mock plugin directory without templates
            plugin_path = cache_dir / "test-plugin"
            plugin_path.mkdir(parents=True)
            
            config = PluginConfig(
                name="test-plugin",
                git="https://github.com/example/test.git"
            )
            
            with patch.object(manager, '_ensure_plugin_available') as mock_ensure:
                mock_ensure.return_value = plugin_path
                
                with pytest.raises(PluginError, match="has no templates directory"):
                    manager.load_plugins([config])

    def test_clean_cache_specific_plugin(self):
        """Test cleaning cache for specific plugin."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            # Create mock plugin directories
            plugin1_path = cache_dir / "plugin1"
            plugin2_path = cache_dir / "plugin2"
            plugin1_path.mkdir(parents=True)
            plugin2_path.mkdir(parents=True)
            
            manager.clean_cache("plugin1")
            
            assert not plugin1_path.exists()
            assert plugin2_path.exists()

    def test_clean_cache_all_plugins(self):
        """Test cleaning all plugin cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            # Create mock plugin directories
            plugin1_path = cache_dir / "plugin1"
            plugin2_path = cache_dir / "plugin2"
            plugin1_path.mkdir(parents=True)
            plugin2_path.mkdir(parents=True)
            
            manager.clean_cache()
            
            assert cache_dir.exists()  # Directory recreated
            assert not plugin1_path.exists()
            assert not plugin2_path.exists()

    def test_list_cached_plugins(self):
        """Test listing cached plugins."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            manager = PluginManager(cache_dir=cache_dir)
            
            # Create mock plugin directories with .git
            plugin1_path = cache_dir / "plugin1"
            plugin2_path = cache_dir / "plugin2"
            plugin3_path = cache_dir / "not-git"  # No .git directory
            
            plugin1_path.mkdir(parents=True)
            plugin2_path.mkdir(parents=True)
            plugin3_path.mkdir(parents=True)
            
            (plugin1_path / ".git").mkdir()
            (plugin2_path / ".git").mkdir()
            
            plugins = manager.list_cached_plugins()
            
            assert len(plugins) == 2
            assert "plugin1" in plugins
            assert "plugin2" in plugins
            assert "not-git" not in plugins

    def test_list_cached_plugins_no_cache(self):
        """Test listing cached plugins when cache doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "nonexistent"
            manager = PluginManager(cache_dir=cache_dir)
            
            plugins = manager.list_cached_plugins()
            assert plugins == []
