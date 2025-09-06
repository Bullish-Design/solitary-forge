# src/solitary_forge/models.py
"""Pydantic models for solitary-forge configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator


class PluginConfig(BaseModel):
    """Configuration for a single plugin."""

    name: str = Field(..., description="Plugin name")
    git: str = Field(..., description="Git repository URL")
    version: str = Field(default="main", description="Git branch, tag, or commit")
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin-specific configuration")

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Plugin name cannot be empty")
        return v.strip()

    @field_validator("git")
    def validate_git_url(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Git URL cannot be empty")
        return v.strip()


class RenderConfig(BaseModel):
    """Configuration for template rendering."""

    template: str = Field(..., description="Template file path")
    output: str = Field(..., description="Output file path")

    @field_validator("template", "output")
    def validate_paths(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Template and output paths cannot be empty")
        return v.strip()


class ForgeConfig(BaseModel):
    """Main forge configuration."""

    variables: Dict[str, Any] = Field(default_factory=dict, description="Global template variables")
    plugins: List[PluginConfig] = Field(default_factory=list, description="Plugin configurations")
    render: List[RenderConfig] = Field(default_factory=list, description="Template render configurations")

    @field_validator("plugins")
    def validate_plugins(cls, v: List[PluginConfig]) -> List[PluginConfig]:
        if not v:
            raise ValueError("At least one plugin must be specified")

        # Check for duplicate plugin names
        names = [plugin.name for plugin in v]
        if len(names) != len(set(names)):
            raise ValueError("Plugin names must be unique")

        return v

    @field_validator("render")
    def validate_render(cls, v: List[RenderConfig]) -> List[RenderConfig]:
        if not v:
            raise ValueError("At least one render configuration must be specified")
        return v

    @classmethod
    def from_yaml_file(cls, path: Path) -> ForgeConfig:
        """Load configuration from YAML file."""
        import yaml

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls.model_validate(data or {})
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")


class PluginManifest(BaseModel):
    """Plugin manifest (plugin.yml) structure."""

    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str = Field(default="", description="Plugin description")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")

    @classmethod
    def from_yaml_file(cls, path: Path) -> PluginManifest:
        """Load manifest from YAML file."""
        import yaml

        if not path.exists():
            raise FileNotFoundError(f"Plugin manifest not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls.model_validate(data or {})
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid plugin manifest YAML: {e}")

