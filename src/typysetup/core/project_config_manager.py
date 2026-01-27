"""Project configuration persistence manager with atomic file operations."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from typysetup.models.project_config import ProjectConfiguration

logger = logging.getLogger(__name__)
console = Console()


class ProjectConfigLoadError(Exception):
    """Raised when project configuration cannot be loaded."""

    pass


class ProjectConfigSaveError(Exception):
    """Raised when project configuration cannot be saved."""

    pass


class ProjectConfigManager:
    """Manages project-specific configuration with atomic writes.

    Handles loading, saving project configuration stored in JSON format
    at {project_dir}/.typysetup/config.json. Provides atomic write operations
    to prevent file corruption.
    """

    CONFIG_DIR_NAME = ".typysetup"
    CONFIG_FILE_NAME = "config.json"

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize project config manager.

        Args:
            project_path: Path to project directory. If provided, config path
                will be resolved to {project_path}/.typysetup/config.json
        """
        self.project_path = Path(project_path) if project_path else None
        self._config_path: Optional[Path] = None
        if self.project_path:
            self._config_path = self._get_config_path(self.project_path)

    def _get_config_path(self, project_path: Path) -> Path:
        """Get path to config file for given project.

        Args:
            project_path: Project directory path

        Returns:
            Path to .typysetup/config.json
        """
        return project_path / self.CONFIG_DIR_NAME / self.CONFIG_FILE_NAME

    def _ensure_config_dir(self, project_path: Path) -> Path:
        """Ensure .typysetup directory exists in project.

        Args:
            project_path: Project directory path

        Returns:
            Path to .typysetup directory

        Raises:
            ProjectConfigSaveError: If directory cannot be created
        """
        config_dir = project_path / self.CONFIG_DIR_NAME
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir
        except Exception as e:
            raise ProjectConfigSaveError(f"Cannot create config directory {config_dir}: {e}") from e

    def load_config(self, project_path: Optional[Path] = None) -> Optional[ProjectConfiguration]:
        """Load project configuration from disk.

        Args:
            project_path: Optional project path. Uses instance path if not provided.

        Returns:
            ProjectConfiguration instance if file exists, None otherwise

        Raises:
            ProjectConfigLoadError: If config file exists but cannot be loaded
        """
        if project_path:
            config_path = self._get_config_path(Path(project_path))
        elif self._config_path:
            config_path = self._config_path
        else:
            raise ProjectConfigLoadError("No project path specified")

        if not config_path.exists():
            logger.debug(f"Config file not found: {config_path}")
            return None

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)

            # Parse datetime from ISO format
            if "created_at" in data and isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"].rstrip("Z"))

            # Validate with Pydantic model
            config = ProjectConfiguration(**data)
            logger.debug(f"Loaded project config from {config_path}")
            return config

        except json.JSONDecodeError as e:
            raise ProjectConfigLoadError(f"Invalid JSON in config file: {e}") from e

        except ValidationError as e:
            raise ProjectConfigLoadError(f"Config validation failed: {e}") from e

        except PermissionError as e:
            raise ProjectConfigLoadError(f"Permission denied reading config: {e}") from e

        except Exception as e:
            raise ProjectConfigLoadError(f"Error loading config: {e}") from e

    def save_config(
        self, config: ProjectConfiguration, project_path: Optional[Path] = None
    ) -> None:
        """Save project configuration to disk with atomic write.

        Writes to a temporary file first, then renames to ensure atomicity.

        Args:
            config: ProjectConfiguration instance to save
            project_path: Optional project path. Uses config.project_path if not provided.

        Raises:
            ProjectConfigSaveError: If configuration cannot be saved
        """
        # Determine project path
        if project_path:
            target_path = Path(project_path)
        elif config.project_path:
            target_path = Path(config.project_path)
        elif self.project_path:
            target_path = self.project_path
        else:
            raise ProjectConfigSaveError("No project path specified")

        # Ensure .typysetup directory exists
        config_dir = self._ensure_config_dir(target_path)
        config_path = config_dir / self.CONFIG_FILE_NAME

        # Create backup of existing file if it exists
        if config_path.exists():
            backup_path = config_path.with_suffix(".json.backup")
            try:
                shutil.copy2(config_path, backup_path)
                logger.debug(f"Created backup at {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")

        # Write to temporary file first (atomic write)
        temp_path = config_path.with_suffix(".json.tmp")
        try:
            # Convert to JSON-serializable dict
            data = config.model_dump(mode="json")

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()  # Ensure data is written

            # Atomic rename (overwrites existing file)
            temp_path.replace(config_path)
            logger.info(f"Saved project config to {config_path}")

        except PermissionError as e:
            raise ProjectConfigSaveError(f"Permission denied writing config: {e}") from e

        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise ProjectConfigSaveError(f"Error saving config: {e}") from e

    def display_config(
        self, config: Optional[ProjectConfiguration] = None, project_path: Optional[Path] = None
    ) -> None:
        """Display project configuration in formatted Rich output.

        Args:
            config: Optional ProjectConfiguration to display. If not provided,
                will load from project_path.
            project_path: Optional project path to load config from.

        Raises:
            ProjectConfigLoadError: If config cannot be loaded
        """
        # Load config if not provided
        if config is None:
            config = self.load_config(project_path)
            if config is None:
                console.print("[yellow]No configuration found for this project.[/yellow]")
                return

        # Main configuration panel
        console.print("\n[bold blue]Project Configuration[/bold blue]\n")

        # Basic info table
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("Field", style="dim")
        info_table.add_column("Value", style="cyan")

        info_table.add_row("Setup Type", config.setup_type_slug)
        info_table.add_row("Python Version", config.python_version)
        info_table.add_row("Package Manager", config.package_manager)
        info_table.add_row("Status", self._format_status(config.status))
        info_table.add_row("Created", config.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"))

        # Paths
        info_table.add_row("Project Path", config.project_path)
        if config.venv_path:
            info_table.add_row("Virtual Environment", config.venv_path)
        if config.python_executable:
            info_table.add_row("Python Executable", config.python_executable)

        console.print(Panel(info_table, title="[bold]Configuration[/bold]", border_style="blue"))

        # Project metadata
        if config.project_metadata:
            metadata = config.project_metadata
            console.print("\n[bold cyan]Project Metadata[/bold cyan]")
            meta_table = Table(show_header=False, box=None, padding=(0, 2))
            meta_table.add_column("Field", style="dim")
            meta_table.add_column("Value", style="green")

            if metadata.get("project_name"):
                meta_table.add_row("Name", metadata["project_name"])
            if metadata.get("description"):
                meta_table.add_row("Description", metadata["description"])
            if metadata.get("author_name"):
                meta_table.add_row("Author", metadata["author_name"])
            if metadata.get("author_email"):
                meta_table.add_row("Email", metadata["author_email"])

            console.print(meta_table)

        # Dependencies
        if config.installed_dependencies:
            console.print("\n[bold cyan]Installed Dependencies[/bold cyan]")
            dep_counts = self._count_dependencies_by_group(config)
            console.print(f"  Total: [green]{len(config.installed_dependencies)}[/green] packages")
            for group, count in dep_counts.items():
                console.print(f"  {group.title()}: [yellow]{count}[/yellow] packages")

        # VSCode extensions
        if config.selected_extensions:
            console.print("\n[bold cyan]VSCode Extensions[/bold cyan]")
            console.print(f"  [green]{len(config.selected_extensions)}[/green] extensions selected")
            if len(config.selected_extensions) <= 10:
                for ext in config.selected_extensions:
                    console.print(f"  • [dim]{ext}[/dim]")

        # Config file location
        if project_path:
            config_path = self._get_config_path(Path(project_path))
        elif self._config_path:
            config_path = self._config_path
        else:
            config_path = Path(config.project_path) / self.CONFIG_DIR_NAME / self.CONFIG_FILE_NAME

        console.print(f"\n[dim]Configuration file: {config_path}[/dim]\n")

    def _format_status(self, status: str) -> str:
        """Format status with color.

        Args:
            status: Status string

        Returns:
            Formatted status with Rich color codes
        """
        status_colors = {
            "success": "[green]Success[/green]",
            "partial": "[yellow]Partial[/yellow]",
            "failed": "[red]Failed[/red]",
            "running": "[blue]Running[/blue]",
            "pending": "[dim]Pending[/dim]",
        }
        return status_colors.get(status, status)

    def _count_dependencies_by_group(self, config: ProjectConfiguration) -> dict[str, int]:
        """Count installed dependencies by group.

        Args:
            config: ProjectConfiguration instance

        Returns:
            Dictionary mapping group names to counts
        """
        counts: dict[str, int] = {}
        for dep in config.installed_dependencies:
            group = dep.from_group or "other"
            counts[group] = counts.get(group, 0) + 1
        return counts

    def config_exists(self, project_path: Optional[Path] = None) -> bool:
        """Check if project configuration exists.

        Args:
            project_path: Optional project path to check

        Returns:
            True if config file exists, False otherwise
        """
        if project_path:
            config_path = self._get_config_path(Path(project_path))
        elif self._config_path:
            config_path = self._config_path
        else:
            return False

        return config_path.exists()
