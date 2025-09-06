# src/solitary_forge/generators/base.py
"""Base classes for file type generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict

from ..models import RenderConfig
from ..validation.validation_system import ValidationResult, Validator


class FileTypeValidator(Validator):
    """Base validator for specific file types."""
    
    @abstractmethod
    def validate_file_specific(self, context: Dict[str, Any], **kwargs) -> ValidationResult:
        """Validate file-type-specific requirements."""
        ...
    
    def validate(self, context: Dict[str, Any], **kwargs) -> ValidationResult:
        """Standard validation interface."""
        return self.validate_file_specific(context, **kwargs)


class FileGenerator(BaseModel, ABC):
    """Base class for file type generators."""
    
    file_type: str
    template_name: str
    output_path: str
    
    model_config = ConfigDict(extra="allow")
    
    @abstractmethod
    def get_required_context_keys(self) -> List[str]:
        """Return list of required context keys for this file type."""
        ...
    
    @abstractmethod
    def get_validators(self) -> List[FileTypeValidator]:
        """Return file-type-specific validators."""
        ...
    
    @abstractmethod
    def post_process_content(self, content: str, context: Dict[str, Any]) -> str:
        """Post-process rendered content if needed."""
        ...
    
    def get_default_template_name(self) -> str:
        """Get default template name for this file type."""
        return self.template_name
    
    def get_render_config(self) -> RenderConfig:
        """Get render configuration for this generator."""
        return RenderConfig(
            template=self.template_name,
            output=self.output_path
        )
    
    def validate_context(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate that context has required keys."""
        missing_keys = []
        required_keys = self.get_required_context_keys()
        
        for key in required_keys:
            if key not in context:
                missing_keys.append(key)
        
        return ValidationResult(
            is_valid=len(missing_keys) == 0,
            validator_name=f"{self.file_type}_context_validator",
            errors=[f"Missing required context key: {key}" for key in missing_keys]
        )
