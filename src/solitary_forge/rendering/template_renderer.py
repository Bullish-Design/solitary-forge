# src/solitary_forge/rendering/template_renderer.py
"""Template rendering engine for solitary-forge."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Protocol

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from pydantic import BaseModel, ConfigDict

from ..exceptions import TemplateError
from ..models import RenderConfig


class TemplateLoader(Protocol):
    """Protocol for template loading strategies."""
    
    def get_template_paths(self) -> List[str]:
        """Get list of template search paths."""
        ...
    
    def validate_paths(self) -> bool:
        """Validate that template paths are accessible."""
        ...


class PluginTemplateLoader(BaseModel):
    """Template loader that uses plugin template directories."""
    
    template_paths: List[Path]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def get_template_paths(self) -> List[str]:
        """Get list of template search paths."""
        return [str(path) for path in self.template_paths if path.exists()]
    
    def validate_paths(self) -> bool:
        """Validate that template paths are accessible."""
        return all(path.exists() and path.is_dir() for path in self.template_paths)


class JinjaTemplateRenderer(BaseModel):
    """Jinja2-based template renderer."""
    
    template_loader: TemplateLoader
    trim_blocks: bool = True
    lstrip_blocks: bool = True
    autoescape: bool = False
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def create_environment(self) -> Environment:
        """Create and configure Jinja2 environment."""
        template_paths = self.template_loader.get_template_paths()
        
        if not template_paths:
            raise TemplateError("No template directories available")
            
        return Environment(
            loader=FileSystemLoader(template_paths),
            trim_blocks=self.trim_blocks,
            lstrip_blocks=self.lstrip_blocks,
            autoescape=self.autoescape
        )
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a single template with context."""
        env = self.create_environment()
        
        try:
            template = env.get_template(template_name)
            return template.render(context)
        except TemplateNotFound:
            raise TemplateError(f"Template not found: {template_name}")
        except Exception as e:
            raise TemplateError(f"Failed to render {template_name}: {e}")
    
    def render_templates(
        self, 
        render_configs: List[RenderConfig], 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Render multiple templates."""
        results = {}
        env = self.create_environment()
        
        for config in render_configs:
            try:
                template = env.get_template(config.template)
                rendered_content = template.render(context)
                results[config.template] = rendered_content
            except TemplateNotFound:
                raise TemplateError(f"Template not found: {config.template}")
            except Exception as e:
                raise TemplateError(f"Failed to render {config.template}: {e}")
                
        return results
    
    def validate_templates(self, template_names: List[str]) -> List[str]:
        """Validate that all templates exist. Returns list of missing templates."""
        env = self.create_environment()
        missing = []
        
        for template_name in template_names:
            try:
                env.get_template(template_name)
            except TemplateNotFound:
                missing.append(template_name)
                
        return missing
