# src/solitary_forge/context/context_builder.py
"""Context building system for template rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Protocol

from pydantic import BaseModel, ConfigDict

from ..models import ForgeConfig
from ..plugin import Plugin


class ContextProvider(Protocol):
    """Protocol for components that contribute to rendering context."""
    
    def get_context_data(self) -> Dict[str, Any]:
        """Return context data to be merged into rendering context."""
        ...
    
    def get_priority(self) -> int:
        """Return priority for context merging (higher = later in chain)."""
        ...


class VariablesProvider(BaseModel):
    """Provides variables from forge configuration."""
    
    variables: Dict[str, Any]
    
    def get_context_data(self) -> Dict[str, Any]:
        return {"variables": self.variables.copy()}
    
    def get_priority(self) -> int:
        return 10


class PluginContextProvider(BaseModel):
    """Provides plugin information to context."""
    
    plugins: List[Plugin]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def get_context_data(self) -> Dict[str, Any]:
        plugin_context = {}
        
        for plugin in self.plugins:
            plugin_context[plugin.name] = {
                "config": plugin.config,
                "path": str(plugin.path) if plugin.path else "",
                "manifest": self._get_plugin_manifest(plugin),
            }
            
        return {"plugins": plugin_context}
    
    def _get_plugin_manifest(self, plugin: Plugin) -> Dict[str, Any]:
        """Get plugin manifest data."""
        if plugin.manifest:
            if hasattr(plugin.manifest, "model_dump"):
                return plugin.manifest.model_dump()
            elif hasattr(plugin.manifest, "dict"):
                return plugin.manifest.dict()
        return {}
    
    def get_priority(self) -> int:
        return 20


class ProjectInfoProvider(BaseModel):
    """Provides project-level information."""
    
    project_root: Path
    config_path: Path
    
    def get_context_data(self) -> Dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "config_path": str(self.config_path),
        }
    
    def get_priority(self) -> int:
        return 5


class EnvironmentProvider(BaseModel):
    """Provides environment-specific variables."""
    
    environment: str
    env_variables: Dict[str, Any]
    
    def get_context_data(self) -> Dict[str, Any]:
        return {
            "environment": self.environment,
            "env": self.env_variables
        }
    
    def get_priority(self) -> int:
        return 15


class ContextBuilder(BaseModel):
    """Builds rendering context from multiple providers."""
    
    providers: List[ContextProvider] = []
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def add_provider(self, provider: ContextProvider) -> ContextBuilder:
        """Add a context provider."""
        self.providers.append(provider)
        return self
    
    def build_context(self) -> Dict[str, Any]:
        """Build complete context from all providers."""
        context = {}
        
        # Sort providers by priority
        sorted_providers = sorted(self.providers, key=lambda p: p.get_priority())
        
        # Merge context data from all providers
        for provider in sorted_providers:
            provider_data = provider.get_context_data()
            self._deep_merge(context, provider_data)
            
        return context
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source dict into target dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    @classmethod
    def create_default(
        cls, 
        config: ForgeConfig, 
        plugins: List[Plugin], 
        project_root: Path, 
        config_path: Path,
        environment: str = "base"
    ) -> ContextBuilder:
        """Create context builder with default providers."""
        builder = cls()
        
        # Add default providers
        builder.add_provider(ProjectInfoProvider(
            project_root=project_root,
            config_path=config_path
        ))
        
        # Environment-specific variables
        env_vars = config.environments.get(environment, {})
        if env_vars:
            builder.add_provider(EnvironmentProvider(
                environment=environment,
                env_variables=env_vars
            ))
        
        builder.add_provider(VariablesProvider(
            variables=config.variables
        ))
        
        builder.add_provider(PluginContextProvider(
            plugins=plugins
        ))
        
        return builder
