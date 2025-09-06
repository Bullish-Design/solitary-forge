#!/usr/bin/env python3
# src/tests/test_forge_fixed.py
"""
Test script for solitary-forge library functionality.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add src to path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from solitary_forge import Forge, ForgeError


def setup_test_plugins(temp_dir: Path) -> str:
    """Create local test plugin repositories. Returns the repo path."""
    # Create core plugin
    core_plugin = temp_dir / "plugins" / "core"
    core_plugin.mkdir(parents=True)

    # Plugin manifest
    (core_plugin / "plugin.yml").write_text("""
name: 'core'
version: '1.0.0'
description: 'Core plugin for testing'
""")

    # Templates directory
    templates_dir = core_plugin / "templates"
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

    # Initialize as git repo
    import git

    repo = git.Repo.init(core_plugin, bare=False)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    repo.index.add(["."])
    repo.index.commit("Initial commit")

    print(f"✓ Created test plugin at {core_plugin}")
    return str(core_plugin)


def test_forge_functionality() -> None:
    """Test the main forge functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        project_dir = temp_path / "test-project"
        project_dir.mkdir()

        # Setup test plugins and get the path
        plugin_path = setup_test_plugins(temp_path)

        # Create test config with the actual plugin path
        config_path = project_dir / ".forge.yml"
        config_content = f"""variables:
  project_name: "test-project"
  base_image: "nixos/nix:latest"
  container_name: "test-dev"
  workdir: "/workspace"

plugins:
  - name: "core"
    git: "file://{plugin_path}"
    version: "main"

render:
  - template: "Dockerfile.j2"
    output: "Dockerfile"
  - template: "docker-compose.yml.j2"
    output: "docker-compose.yml"
"""
        config_path.write_text(config_content)

        # Test forge build
        try:
            forge = Forge(config_path=config_path)
            rendered_files = forge.build()

            print(f"✓ Build successful, generated {len(rendered_files)} files")

            # Verify generated files exist
            dockerfile = project_dir / "Dockerfile"
            compose_file = project_dir / "docker-compose.yml"

            assert dockerfile.exists(), "Dockerfile not generated"
            assert compose_file.exists(), "docker-compose.yml not generated"

            # Check content contains variables
            dockerfile_content = dockerfile.read_text()
            assert "test-project" in dockerfile_content, "Variables not substituted"

            print("✓ All tests passed!")
            print(f"Generated files: {list(rendered_files.values())}")

            # Show generated content
            print("\n--- Generated Dockerfile ---")
            print(dockerfile_content)

        except ForgeError as e:
            print(f"✗ Forge error: {e}")
            raise
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            raise


if __name__ == "__main__":
    test_forge_functionality()
