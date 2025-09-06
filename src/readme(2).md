# README.md

# Solitary Forge

A Jinja2-based environment generator with Git plugin support for creating Docker and Nix development environments.

## Overview

Solitary Forge allows you to generate development environment files (Dockerfiles, docker-compose.yml, devenv.nix, etc.) using a plugin-based template system. Plugins are distributed as Git repositories containing Jinja2 templates, making it easy to share and version environment configurations.

## Features

- **Git-based plugins**: Templates distributed as Git repositories
- **Jinja2 templating**: Powerful template engine with variables and logic
- **Plugin caching**: Automatic cloning and updating of plugin repositories
- **Multiple file generation**: Generate multiple files from different templates
- **Validation**: Built-in configuration and template validation
- **CLI interface**: Easy-to-use command-line interface

## Installation

```bash
pip install solitary-forge
```

Or with uv:
```bash
uv add solitary-forge
```

## Quick Start

1. **Initialize a new project:**
   ```bash
   solitary-forge init
   ```

2. **Edit `.forge.yml`** to configure your variables and plugin URLs:
   ```yaml
   variables:
     project_name: "my-project"
     base_image: "nixos/nix:latest"
     container_name: "my-project-dev"
   
   plugins:
     - name: "core"
       git: "https://github.com/example/forge-plugin-core.git"
       version: "main"
   
   render:
     - template: "Dockerfile.j2"
       output: "Dockerfile"
     - template: "docker-compose.yml.j2"
       output: "docker-compose.yml"
   ```

3. **Build your environment:**
   ```bash
   solitary-forge build
   ```

## Configuration

The `.forge.yml` file contains three main sections:

### Variables
Global template variables available to all templates:
```yaml
variables:
  project_name: "test-project"
  base_image: "nixos/nix:latest"
  python_version: "python313"
```

### Plugins
Git repositories containing templates:
```yaml
plugins:
  - name: "core"
    git: "https://github.com/example/forge-plugin-core.git"
    version: "main"
  - name: "python-dev"
    git: "https://github.com/example/forge-plugin-python.git"
    version: "v1.0.0"
    config:
      packages: ["uv", "git"]
      python_version: "313"
```

### Render
Template to output file mappings:
```yaml
render:
  - template: "Dockerfile.j2"
    output: "Dockerfile"
  - template: "devenv.nix.j2"
    output: "devenv.nix"
```

## CLI Commands

- `solitary-forge build` - Generate environment files
- `solitary-forge init` - Initialize new configuration
- `solitary-forge validate` - Validate configuration
- `solitary-forge clean` - Clean plugin cache
- `solitary-forge list-plugins` - List cached plugins
- `solitary-forge list-templates` - List available templates

## Plugin Development

Plugins are Git repositories with this structure:
```
plugin-name/
├── plugin.yml          # Plugin manifest (optional)
└── templates/          # Jinja2 templates
    ├── Dockerfile.j2
    └── docker-compose.yml.j2
```

### Plugin Manifest (plugin.yml)
```yaml
name: "core"
version: "1.0.0"
description: "Core templates for Docker environments"
dependencies: []
```

### Template Context

Templates have access to:
- `variables.*` - Global variables from configuration
- `plugins.*` - Plugin-specific configurations
- `project_root` - Project root directory path
- `config_path` - Configuration file path

Example template:
```jinja2
FROM {{ variables.base_image }}

WORKDIR {{ variables.workdir }}

{% if plugins.python.config.packages %}
RUN nix-env -iA {% for pkg in plugins.python.config.packages %}{{ pkg }} {% endfor %}
{% endif %}
```

## Examples

See the `examples/` directory for complete project examples using various plugins.

## Requirements

- Python 3.11+
- Git

## License

MIT License