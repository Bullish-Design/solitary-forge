# src/solitary_forge/validation/validation_system.py
"""Composable validation system for forge configurations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Protocol

from pydantic import BaseModel, ConfigDict
from rich.console import Console

from ..models import ForgeConfig, RenderConfig
from ..plugin import Plugin


class ValidationResult(BaseModel):
    """Result of a validation check."""
    
    is_valid: bool
    validator_name: str
    message: str = ""
    errors: List[str] = []
    warnings: List[str] = []


class Validator(Protocol):
    """Protocol for validation components."""
    
    def validate(self, **kwargs) -> ValidationResult:
        """Perform validation and return result."""
        ...
    
    def get_name(self) -> str:
        """Get validator name for reporting."""
        ...


class PluginValidator(BaseModel):
    """Validates that plugins can be loaded and have templates."""
    
    def validate(self, plugins: List[Plugin], **kwargs) -> ValidationResult:
        """Validate plugin configuration."""
        errors = []
        warnings = []
        
        if not plugins:
            errors.append("No plugins available")
            
        for plugin in plugins:
            if not plugin.has_templates:
                errors.append(f"Plugin '{plugin.name}' has no templates directory")
            
            template_count = len(plugin.list_templates())
            if template_count == 0:
                warnings.append(f"Plugin '{plugin.name}' has no templates")
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            validator_name=self.get_name(),
            errors=errors,
            warnings=warnings
        )
    
    def get_name(self) -> str:
        return "plugin_validator"


class TemplateValidator(BaseModel):
    """Validates that all required templates exist."""
    
    def validate(
        self, 
        render_configs: List[RenderConfig], 
        plugins: List[Plugin], 
        **kwargs
    ) -> ValidationResult:
        """Validate template availability."""
        errors = []
        warnings = []
        
        # Get all available templates
        available_templates = set()
        for plugin in plugins:
            available_templates.update(plugin.list_templates())
            
        # Check each required template
        required_templates = {config.template for config in render_configs}
        
        for template in required_templates:
            if template not in available_templates:
                errors.append(f"Template not found: {template}")
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            validator_name=self.get_name(),
            errors=errors,
            warnings=warnings
        )
    
    def get_name(self) -> str:
        return "template_validator"


class OutputPathValidator(BaseModel):
    """Validates output paths and permissions."""
    
    project_root: Path
    
    def validate(self, render_configs: List[RenderConfig], **kwargs) -> ValidationResult:
        """Validate output paths."""
        errors = []
        warnings = []
        
        output_paths = set()
        
        for config in render_configs:
            output_path = self.project_root / config.output
            
            # Check for duplicate outputs
            if config.output in output_paths:
                errors.append(f"Duplicate output path: {config.output}")
            else:
                output_paths.add(config.output)
            
            # Check if output directory is writable
            output_dir = output_path.parent
            if output_dir.exists() and not output_dir.is_dir():
                errors.append(f"Output directory is not a directory: {output_dir}")
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            validator_name=self.get_name(),
            errors=errors,
            warnings=warnings
        )
    
    def get_name(self) -> str:
        return "output_path_validator"


class ConfigValidator(BaseModel):
    """Validates forge configuration."""
    
    def validate(self, config: ForgeConfig, **kwargs) -> ValidationResult:
        """Validate forge configuration."""
        errors = []
        warnings = []
        
        # Check for required variables
        variables = config.variables
        if not variables.get("project_name"):
            warnings.append("Missing recommended variable: project_name")
            
        # Validate plugin configurations
        for plugin in config.plugins:
            if not plugin.git.startswith(("http://", "https://", "git@")):
                warnings.append(f"Plugin '{plugin.name}' has unusual git URL format")
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            validator_name=self.get_name(),
            errors=errors,
            warnings=warnings
        )
    
    def get_name(self) -> str:
        return "config_validator"


class ValidationSystem(BaseModel):
    """Composable validation system."""
    
    validators: List[Validator] = []
    console: Console = Console()
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def add_validator(self, validator: Validator) -> ValidationSystem:
        """Add a validator to the system."""
        self.validators.append(validator)
        return self
    
    def validate_all(self, **validation_data) -> bool:
        """Run all validators and return overall result."""
        overall_valid = True
        
        for validator in self.validators:
            result = validator.validate(**validation_data)
            
            if not result.is_valid:
                overall_valid = False
                self._report_errors(result)
            else:
                self._report_success(result)
                
            if result.warnings:
                self._report_warnings(result)
                
        return overall_valid
    
    def _report_success(self, result: ValidationResult) -> None:
        """Report successful validation."""
        self.console.print(f"✅ {result.validator_name}: Passed")
    
    def _report_errors(self, result: ValidationResult) -> None:
        """Report validation errors."""
        self.console.print(f"❌ {result.validator_name}: Failed", style="red")
        for error in result.errors:
            self.console.print(f"  • {error}", style="red")
            
    def _report_warnings(self, result: ValidationResult) -> None:
        """Report validation warnings."""
        for warning in result.warnings:
            self.console.print(f"⚠️  {warning}", style="yellow")
    
    @classmethod
    def create_default(cls, project_root: Path) -> ValidationSystem:
        """Create validation system with default validators."""
        system = cls()
        
        system.add_validator(ConfigValidator())
        system.add_validator(PluginValidator())
        system.add_validator(TemplateValidator())
        system.add_validator(OutputPathValidator(project_root=project_root))
        
        return system
