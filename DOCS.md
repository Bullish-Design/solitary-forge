# DOCS.md

# Solitary Forge Developer Documentation

## Architecture Overview

Solitary Forge uses a plugin-based architecture with the following core components:

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐
│     CLI         │───▶│      Forge       │───▶│ PluginManager  │
│   (typer)       │    │ (orchestrator)   │    │  (git ops)     │
└─────────────────┘    └──────────────────┘    └────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌──────────────────┐    ┌────────────────┐
                        │ Jinja2 Environment│    │    Plugin      │
                        │   (templating)    │    │  (templates)   │
                        └──────────────────┘    └────────────────┘
```

## Core Classes

### Forge (`forge.py`)

Main orchestrator class that coordinates the entire build process.

```python
from solitary_forge import Forge

forge = Forge(config_path=".forge.yml")
rendered_files = forge.build()
```

**Key Methods:**
- `build()` - Complete build process returning dict of rendered files
- `validate_config()` - Validate configuration and templates
- `clean(plugin_name=None)` - Clean plugin cache
- `list_plugins()` - List cached plugins
- `list_templates()` - Get available templates by plugin

### PluginManager (`plugin.py`)

Manages plugin lifecycle including Git operations and caching.

```python
from solitary_forge.plugin import PluginManager
from pathlib import Path

manager = PluginManager(cache_dir=Path(".forge_cache/plugins"))
plugins = manager.load_plugins(plugin_configs)
```

**Key Methods:**
- `load_plugins(configs)` - Load all plugins from configurations
- `clean_cache(plugin_name=None)` - Clean plugin cache
- `list_cached_plugins()` - List cached plugin names

### Plugin (`plugin.py`)

Represents a loaded plugin with templates and metadata.

**Properties:**
- `templates_path` - Path to plugin templates directory
- `has_templates` - Boolean indicating if templates exist
- `manifest` - Loaded plugin manifest (optional)

**Methods:**
- `load_manifest()` - Load plugin.yml manifest
- `list_templates()` - List available template files

## Configuration Models

All configuration uses Pydantic models with validation:

### ForgeConfig (`models.py`)

```python
from solitary_forge.models import ForgeConfig

config = ForgeConfig.from_yaml_file(Path(".forge.yml"))
```

**Fields:**
- `variables: Dict[str, Any]` - Global template variables
- `plugins: List[PluginConfig]` - Plugin configurations
- `render: List[RenderConfig]` - Template render configurations

### PluginConfig (`models.py`)

```python
plugin_config = PluginConfig(
    name="core",
    git="https://github.com/example/plugin.git",
    version="main",
    config={"custom": "values"}
)
```

### RenderConfig (`models.py`)

```python
render_config = RenderConfig(
    template="Dockerfile.j2",
    output="Dockerfile"
)
```

## Template Context

Templates receive a comprehensive context object:

```python
context = {
    "variables": {
        "project_name": "my-project",
        "base_image": "nixos/nix:latest"
    },
    "plugins": {
        "core": {
            "config": {},
            "path": "/cache/core",
            "manifest": {"name": "core", "version": "1.0.0"}
        }
    },
    "project_root": "/path/to/project",
    "config_path": "/path/to/.forge.yml"
}
```

## Plugin Development

### Directory Structure
```
my-plugin/
├── plugin.yml          # Optional manifest
└── templates/          # Required templates directory
    ├── Dockerfile.j2
    ├── docker-compose.yml.j2
    └── subdirectory/
        └── config.j2
```

### Plugin Manifest (plugin.yml)
```yaml
name: "my-plugin"
version: "1.0.0"
description: "My custom plugin"
dependencies: ["other-plugin"]
```

### Template Guidelines

Use Jinja2 features for flexible templates:

```jinja2
FROM {{ variables.base_image }}

{% if variables.workdir %}
WORKDIR {{ variables.workdir }}
{% endif %}

{% for package in plugins.python.config.packages %}
RUN install {{ package }}
{% endfor %}
```

## Error Handling

Custom exception hierarchy:

```python
ForgeError                    # Base exception
├── ConfigError              # Configuration issues
├── PluginError              # Plugin-related errors
│   └── GitOperationError    # Git operation failures
└── TemplateError            # Template rendering issues
```

## Development Setup

1. **Clone repository:**
   ```bash
   git clone <repository>
   cd solitary-forge
   ```

2. **Install dependencies:**
   ```bash
   uv sync --dev
   ```

3. **Run tests:**
   ```bash
   uv run pytest
   ```

4. **Run linting:**
   ```bash
   uv run ruff check
   uv run mypy src/
   ```

## API Reference

### Forge Class

```python
class Forge(BaseModel):
    config_path: Path
    project_root: Path
    config: ForgeConfig
    plugin_manager: PluginManager
    console: Console
```

**Constructor:**
```python
Forge(config_path: str | Path = ".forge.yml")
```

**Methods:**

#### `build() -> Dict[str, Path]`
Execute complete build process.

**Returns:** Dictionary mapping template names to output file paths.

**Raises:** `ConfigError`, `PluginError`, `TemplateError`

#### `validate_config() -> bool`
Validate configuration and check template availability.

#### `clean(plugin_name: str | None = None) -> None`
Clean plugin cache for specific plugin or all plugins.

#### `list_plugins() -> List[str]`
List names of cached plugins.

#### `list_templates() -> Dict[str, List[str]]`
Get available templates grouped by plugin.

#### `@classmethod init_config(project_dir: Path | str = ".", force: bool = False) -> Path`
Initialize default configuration file.

### PluginManager Class

```python
class PluginManager(BaseModel):
    cache_dir: Path
    console: Console
```

**Methods:**

#### `load_plugins(plugins_config: List[PluginConfig]) -> List[Plugin]`
Load and cache all plugins from configuration.

#### `clean_cache(plugin_name: Optional[str] = None) -> None`
Clean plugin cache.

#### `list_cached_plugins() -> List[str]`
List cached plugin names.

## Testing

The test suite covers:

- Configuration loading and validation
- Plugin management and Git operations
- Template rendering
- CLI command functionality
- Error handling

Run specific test categories:
```bash
uv run pytest tests/test_models.py      # Configuration tests
uv run pytest tests/test_plugin.py     # Plugin tests
uv run pytest tests/test_forge.py      # Integration tests
uv run pytest tests/test_cli.py        # CLI tests
```

## Contributing

1. Follow existing code style (Pydantic models, type hints)
2. Add tests for new functionality
3. Update documentation
4. Ensure all linting passes
5. Keep lines under 120 characters