# tests/conftest.py
"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for tests."""
    return {
        "variables": {
            "project_name": "test-project",
            "base_image": "nixos/nix:latest",
            "container_name": "test-project-dev",
            "workdir": "/workspace"
        },
        "plugins": [
            {
                "name": "core",
                "git": "https://github.com/example/forge-plugin-core.git",
                "version": "main"
            },
            {
                "name": "python-dev",
                "git": "https://github.com/example/forge-plugin-python.git",
                "version": "v1.0.0",
                "config": {
                    "packages": ["uv", "git"],
                    "python_version": "313"
                }
            }
        ],
        "render": [
            {
                "template": "Dockerfile.j2",
                "output": "Dockerfile"
            },
            {
                "template": "docker-compose.yml.j2",
                "output": "docker-compose.yml"
            }
        ]
    }


@pytest.fixture
def config_file(temp_dir, sample_config_data):
    """Create a sample config file."""
    config_path = temp_dir / ".forge.yml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config_data, f)
    return config_path


@pytest.fixture
def sample_templates():
    """Sample Jinja2 templates for testing."""
    return {
        "Dockerfile.j2": """FROM {{ variables.base_image }}

WORKDIR {{ variables.workdir }}

{% if plugins['python-dev'].config.packages %}
# Install packages
{% for package in plugins['python-dev'].config.packages %}
RUN nix-env -iA nixpkgs.{{ package }}
{% endfor %}
{% endif %}

# Set project name
ENV PROJECT_NAME={{ variables.project_name }}
""",
        "docker-compose.yml.j2": """version: '3.8'

services:
  {{ variables.container_name }}:
    build: .
    container_name: {{ variables.container_name }}
    working_dir: {{ variables.workdir }}
    volumes:
      - .{{ variables.workdir }}
    environment:
      - PROJECT_NAME={{ variables.project_name }}
{% if plugins['python-dev'].config.python_version %}
      - PYTHON_VERSION={{ plugins['python-dev'].config.python_version }}
{% endif %}
""",
        "devenv.nix.j2": """{ pkgs, ... }:

{
  packages = with pkgs; [
{% for package in plugins['python-dev'].config.packages %}
    {{ package }}
{% endfor %}
  ];

  env = {
    PROJECT_NAME = "{{ variables.project_name }}";
{% if plugins['python-dev'].config.python_version %}
    PYTHON_VERSION = "{{ plugins['python-dev'].config.python_version }}";
{% endif %}
  };

  scripts = {
    start.exec = "echo 'Starting {{ variables.project_name }}'";
  };
}
"""
    }


@pytest.fixture
def plugin_with_templates(temp_dir, sample_templates):
    """Create a mock plugin directory with templates."""
    plugin_path = temp_dir / "mock-plugin"
    templates_path = plugin_path / "templates"
    templates_path.mkdir(parents=True)
    
    # Create template files
    for template_name, content in sample_templates.items():
        template_file = templates_path / template_name
        with open(template_file, 'w') as f:
            f.write(content)
    
    # Create plugin manifest
    manifest_data = {
        "name": "mock-plugin",
        "version": "1.0.0",
        "description": "Mock plugin for testing",
        "dependencies": []
    }
    manifest_path = plugin_path / "plugin.yml"
    with open(manifest_path, 'w') as f:
        yaml.dump(manifest_data, f)
    
    return plugin_path


@pytest.fixture
def git_mock_plugin(temp_dir, sample_templates):
    """Create a mock plugin with .git directory to simulate cached plugin."""
    plugin_path = temp_dir / "cached-plugin"
    git_path = plugin_path / ".git"
    templates_path = plugin_path / "templates"
    
    # Create directories
    git_path.mkdir(parents=True)
    templates_path.mkdir(parents=True)
    
    # Create template files
    for template_name, content in sample_templates.items():
        template_file = templates_path / template_name
        with open(template_file, 'w') as f:
            f.write(content)
    
    return plugin_path
