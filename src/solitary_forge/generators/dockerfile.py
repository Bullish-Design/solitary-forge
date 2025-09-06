# src/solitary_forge/generators/dockerfile.py
"""Dockerfile-specific generator and validation."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from pydantic import Field

from ..validation.validation_system import ValidationResult
from .base import FileGenerator, FileTypeValidator


class DockerfileValidator(FileTypeValidator):
    """Validates Dockerfile-specific requirements."""
    
    def validate_file_specific(self, context: Dict[str, Any], **kwargs) -> ValidationResult:
        """Validate Dockerfile context requirements."""
        errors = []
        warnings = []
        
        variables = context.get("variables", {})
        
        # Check for base image
        if "base_image" not in variables:
            errors.append("Missing required variable: base_image")
        elif not variables["base_image"]:
            errors.append("base_image cannot be empty")
            
        # Check for workdir
        if "workdir" in variables:
            workdir = variables["workdir"]
            if not workdir.startswith("/"):
                warnings.append("workdir should be an absolute path")
                
        # Validate image name format if present
        if "base_image" in variables:
            image = variables["base_image"]
            if not self._is_valid_docker_image(image):
                errors.append(f"Invalid Docker image format: {image}")
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            validator_name=self.get_name(),
            errors=errors,
            warnings=warnings
        )
    
    def _is_valid_docker_image(self, image: str) -> bool:
        """Check if Docker image name is valid."""
        # Basic validation for Docker image format
        pattern = r"^[a-z0-9]+([\.\-\_][a-z0-9]+)*(/[a-z0-9]+([\.\-\_][a-z0-9]+)*)*(:[a-zA-Z0-9][\w\.\-]{0,127})?$"
        return bool(re.match(pattern, image, re.IGNORECASE))
    
    def get_name(self) -> str:
        return "dockerfile_validator"


class DockerfileGenerator(FileGenerator):
    """Generator for Dockerfile files."""
    
    file_type: str = Field(default="dockerfile")
    template_name: str = Field(default="Dockerfile.j2")
    output_path: str = Field(default="Dockerfile")
    
    # Dockerfile-specific configuration
    multi_stage: bool = Field(default=False)
    optimize_layers: bool = Field(default=True)
    include_healthcheck: bool = Field(default=False)
    
    def get_required_context_keys(self) -> List[str]:
        """Required context for Dockerfile generation."""
        return ["variables"]
    
    def get_validators(self) -> List[FileTypeValidator]:
        """Get Dockerfile-specific validators."""
        return [DockerfileValidator()]
    
    def post_process_content(self, content: str, context: Dict[str, Any]) -> str:
        """Post-process Dockerfile content."""
        if self.optimize_layers:
            content = self._optimize_run_commands(content)
            
        if self.include_healthcheck and "HEALTHCHECK" not in content:
            content = self._add_default_healthcheck(content)
            
        return content
    
    def _optimize_run_commands(self, content: str) -> str:
        """Combine consecutive RUN commands to reduce layers."""
        lines = content.split('\n')
        optimized_lines = []
        run_buffer = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('RUN '):
                run_buffer.append(stripped[4:])  # Remove 'RUN '
            else:
                if run_buffer:
                    # Combine buffered RUN commands
                    combined_run = "RUN " + " && \\\n    ".join(run_buffer)
                    optimized_lines.append(combined_run)
                    run_buffer = []
                optimized_lines.append(line)
                
        # Handle any remaining RUN commands
        if run_buffer:
            combined_run = "RUN " + " && \\\n    ".join(run_buffer)
            optimized_lines.append(combined_run)
            
        return '\n'.join(optimized_lines)
    
    def _add_default_healthcheck(self, content: str) -> str:
        """Add basic healthcheck if none exists."""
        healthcheck = "\n# Health check\nHEALTHCHECK --interval=30s --timeout=3s --retries=3 \\\n  CMD curl -f http://localhost:8080/health || exit 1\n"
        
        # Insert before CMD/ENTRYPOINT
        lines = content.split('\n')
        insert_index = len(lines)
        
        for i, line in enumerate(lines):
            if line.strip().startswith(('CMD', 'ENTRYPOINT')):
                insert_index = i
                break
                
        lines.insert(insert_index, healthcheck)
        return '\n'.join(lines)
