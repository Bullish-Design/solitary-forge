# src/solitary_forge/generators/registry.py
"""Registry and factory for file generators."""

from __future__ import annotations

from typing import Dict, List, Type

from pydantic import BaseModel, ConfigDict

from .base import FileGenerator
from .compose import DockerComposeGenerator
from .dockerfile import DockerfileGenerator
from .nix import DevenvNixGenerator, FlakeNixGenerator, HomeNixGenerator


class GeneratorRegistry(BaseModel):
    """Registry for managing file generators."""
    
    generators: Dict[str, Type[FileGenerator]] = {}
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def register(self, file_type: str, generator_class: Type[FileGenerator]) -> None:
        """Register a generator for a file type."""
        self.generators[file_type] = generator_class
    
    def create_generator(self, file_type: str, **kwargs) -> FileGenerator:
        """Create generator instance for file type."""
        if file_type not in self.generators:
            raise ValueError(f"No generator registered for file type: {file_type}")
            
        generator_class = self.generators[file_type]
        return generator_class(**kwargs)
    
    def get_available_types(self) -> List[str]:
        """Get list of available file types."""
        return list(self.generators.keys())
    
    def auto_detect_generators(self, template_names: List[str]) -> List[FileGenerator]:
        """Auto-detect generators based on template names."""
        detected = []
        
        for template in template_names:
            if template.startswith("Dockerfile"):
                detected.append(self.create_generator("dockerfile", template_name=template))
            elif "compose" in template.lower():
                detected.append(self.create_generator("compose", template_name=template))
            elif template.endswith("devenv.nix.j2"):
                detected.append(self.create_generator("devenv_nix", template_name=template))
            elif template.endswith("flake.nix.j2"):
                detected.append(self.create_generator("flake_nix", template_name=template))
            elif template.endswith("home.nix.j2"):
                detected.append(self.create_generator("home_nix", template_name=template))
                
        return detected


def create_default_registry() -> GeneratorRegistry:
    """Create registry with default generators."""
    registry = GeneratorRegistry()
    
    registry.register("dockerfile", DockerfileGenerator)
    registry.register("compose", DockerComposeGenerator)
    registry.register("devenv_nix", DevenvNixGenerator)
    registry.register("flake_nix", FlakeNixGenerator)
    registry.register("home_nix", HomeNixGenerator)
    
    return registry


# Global registry instance
default_registry = create_default_registry()
