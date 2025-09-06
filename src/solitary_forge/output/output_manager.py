# src/solitary_forge/output/output_manager.py
"""Output management for rendered templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Protocol

from pydantic import BaseModel, ConfigDict
from rich.console import Console

from ..exceptions import TemplateError
from ..models import RenderConfig


class OutputStrategy(Protocol):
    """Protocol for different output strategies."""
    
    def write_output(self, path: Path, content: str) -> None:
        """Write content to specified path."""
        ...
    
    def prepare_output_dir(self, path: Path) -> None:
        """Prepare output directory for writing."""
        ...


class FileSystemOutputStrategy(BaseModel):
    """Standard filesystem output strategy."""
    
    encoding: str = "utf-8"
    create_dirs: bool = True
    overwrite: bool = True
    
    def write_output(self, path: Path, content: str) -> None:
        """Write content to filesystem."""
        if not self.overwrite and path.exists():
            raise TemplateError(f"Output file already exists: {path}")
            
        if self.create_dirs:
            self.prepare_output_dir(path)
            
        with open(path, "w", encoding=self.encoding) as f:
            f.write(content)
    
    def prepare_output_dir(self, path: Path) -> None:
        """Create parent directories if needed."""
        path.parent.mkdir(parents=True, exist_ok=True)


class DryRunOutputStrategy(BaseModel):
    """Output strategy that logs instead of writing files."""
    
    console: Console = Console()
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def write_output(self, path: Path, content: str) -> None:
        """Log what would be written."""
        self.console.print(f"[yellow]DRY RUN[/yellow] Would write to: [cyan]{path}[/cyan]")
        self.console.print(f"Content length: {len(content)} characters")
    
    def prepare_output_dir(self, path: Path) -> None:
        """Log directory creation."""
        if not path.parent.exists():
            self.console.print(f"[yellow]DRY RUN[/yellow] Would create dir: [cyan]{path.parent}[/cyan]")


class OutputManager(BaseModel):
    """Manages output of rendered templates."""
    
    project_root: Path
    output_strategy: OutputStrategy
    console: Console = Console()
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def write_rendered_templates(
        self,
        rendered_content: Dict[str, str],
        render_configs: List[RenderConfig]
    ) -> Dict[str, Path]:
        """Write rendered templates to their output locations."""
        rendered_files = {}
        config_map = {config.template: config for config in render_configs}
        
        for template_name, content in rendered_content.items():
            if template_name not in config_map:
                raise TemplateError(f"No render config found for template: {template_name}")
                
            config = config_map[template_name]
            output_path = self.project_root / config.output
            
            try:
                self.output_strategy.write_output(output_path, content)
                rendered_files[template_name] = output_path
                self._log_success(template_name, config.output)
            except Exception as e:
                raise TemplateError(f"Failed to write {config.output}: {e}")
                
        return rendered_files
    
    def _log_success(self, template_name: str, output_path: str) -> None:
        """Log successful template rendering."""
        self.console.print(f"  ✓ {template_name} → [cyan]{output_path}[/cyan]")
    
    @classmethod
    def create_filesystem(cls, project_root: Path, **kwargs) -> OutputManager:
        """Create output manager with filesystem strategy."""
        strategy = FileSystemOutputStrategy(**kwargs)
        return cls(project_root=project_root, output_strategy=strategy)
    
    @classmethod
    def create_dry_run(cls, project_root: Path) -> OutputManager:
        """Create output manager with dry run strategy."""
        strategy = DryRunOutputStrategy()
        return cls(project_root=project_root, output_strategy=strategy)
