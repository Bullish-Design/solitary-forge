# src/solitary_forge/generators/compose.py
"""Docker Compose generator."""

from __future__ import annotations

import re
from typing import Any, Dict, List

import yaml
from pydantic import Field

from ..validation.validation_system import ValidationResult
from .base import FileGenerator, FileTypeValidator


class ComposeValidator(FileTypeValidator):
    """Validates Docker Compose requirements."""
    
    def validate_file_specific(self, context: Dict[str, Any], **kwargs) -> ValidationResult:
        errors = []
        warnings = []
        variables = context.get("variables", {})
        
        if "container_name" not in variables:
            errors.append("Missing required variable: container_name")
            
        if "container_name" in variables:
            name = variables["container_name"]
            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", name):
                errors.append(f"Invalid container name format: {name}")
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            validator_name=self.get_name(),
            errors=errors,
            warnings=warnings
        )
    
    def get_name(self) -> str:
        return "compose_validator"


class DockerComposeGenerator(FileGenerator):
    """Generator for Docker Compose files."""
    
    file_type: str = Field(default="compose")
    template_name: str = Field(default="docker-compose.yml.j2")
    output_path: str = Field(default="docker-compose.yml")
    compose_version: str = Field(default="3.8")
    development_mode: bool = Field(default=True)
    
    def get_required_context_keys(self) -> List[str]:
        return ["variables"]
    
    def get_validators(self) -> List[FileTypeValidator]:
        return [ComposeValidator()]
    
    def post_process_content(self, content: str, context: Dict[str, Any]) -> str:
        try:
            compose_data = yaml.safe_load(content)
            
            if self.development_mode:
                compose_data = self._add_development_features(compose_data, context)
                
            content = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)
        except yaml.YAMLError:
            pass
            
        return content
    
    def _add_development_features(self, compose_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        services = compose_data.get("services", {})
        
        for service_config in services.values():
            if "restart" not in service_config:
                service_config["restart"] = "unless-stopped"
            service_config["stdin_open"] = True
            service_config["tty"] = True
            
        return compose_data


# src/solitary_forge/generators/nix.py
"""Nix file generators."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from pydantic import Field

from ..validation.validation_system import ValidationResult
from .base import FileGenerator, FileTypeValidator


class NixValidator(FileTypeValidator):
    """Validates Nix requirements."""
    
    def validate_file_specific(self, context: Dict[str, Any], **kwargs) -> ValidationResult:
        errors = []
        warnings = []
        variables = context.get("variables", {})
        
        if "project_name" not in variables:
            warnings.append("project_name recommended for Nix environments")
            
        if "nix_packages" in variables:
            packages = variables["nix_packages"]
            if isinstance(packages, list):
                for pkg in packages:
                    if not re.match(r"^(nixpkgs\.)?[a-zA-Z][a-zA-Z0-9\-_]*$", pkg):
                        warnings.append(f"Potentially invalid Nix package name: {pkg}")
                        
        return ValidationResult(
            is_valid=len(errors) == 0,
            validator_name=self.get_name(),
            errors=errors,
            warnings=warnings
        )
    
    def get_name(self) -> str:
        return "nix_validator"


class DevenvNixGenerator(FileGenerator):
    """Generator for devenv.nix files."""
    
    file_type: str = Field(default="devenv_nix")
    template_name: str = Field(default="devenv.nix.j2")
    output_path: str = Field(default="devenv.nix")
    include_direnv: bool = Field(default=True)
    
    def get_required_context_keys(self) -> List[str]:
        return ["variables"]
    
    def get_validators(self) -> List[FileTypeValidator]:
        return [NixValidator()]
    
    def post_process_content(self, content: str, context: Dict[str, Any]) -> str:
        if self.include_direnv and "direnv.enable" not in content:
            lines = content.split('\n')
            lines.insert(1, "  direnv.enable = true;")
            content = '\n'.join(lines)
        return self._format_nix_syntax(content)
    
    def _format_nix_syntax(self, content: str) -> str:
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.endswith('{'):
                formatted_lines.append('  ' * indent_level + stripped)
                indent_level += 1
            elif stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)
                formatted_lines.append('  ' * indent_level + stripped)
            else:
                formatted_lines.append('  ' * indent_level + stripped)
                
        return '\n'.join(formatted_lines)


class FlakeNixGenerator(FileGenerator):
    """Generator for flake.nix files."""
    
    file_type: str = Field(default="flake_nix")
    template_name: str = Field(default="flake.nix.j2")
    output_path: str = Field(default="flake.nix")
    
    def get_required_context_keys(self) -> List[str]:
        return ["variables"]
    
    def get_validators(self) -> List[FileTypeValidator]:
        return [NixValidator()]
    
    def post_process_content(self, content: str, context: Dict[str, Any]) -> str:
        return self._format_nix_syntax(content)
    
    def _format_nix_syntax(self, content: str) -> str:
        # Same formatting as DevenvNixGenerator
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.endswith('{'):
                formatted_lines.append('  ' * indent_level + stripped)
                indent_level += 1
            elif stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)
                formatted_lines.append('  ' * indent_level + stripped)
            else:
                formatted_lines.append('  ' * indent_level + stripped)
                
        return '\n'.join(formatted_lines)


class HomeNixGenerator(FileGenerator):
    """Generator for home.nix files."""
    
    file_type: str = Field(default="home_nix")
    template_name: str = Field(default="home.nix.j2")
    output_path: str = Field(default="home.nix")
    
    def get_required_context_keys(self) -> List[str]:
        return ["variables"]
    
    def get_validators(self) -> List[FileTypeValidator]:
        return [NixValidator()]
    
    def post_process_content(self, content: str, context: Dict[str, Any]) -> str:
        return self._format_nix_syntax(content)
    
    def _format_nix_syntax(self, content: str) -> str:
        # Same formatting logic
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.endswith('{'):
                formatted_lines.append('  ' * indent_level + stripped)
                indent_level += 1
            elif stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)
                formatted_lines.append('  ' * indent_level + stripped)
            else:
                formatted_lines.append('  ' * indent_level + stripped)
                
        return '\n'.join(formatted_lines)
