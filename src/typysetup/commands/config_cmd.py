"""Config command - display project configuration."""

from pathlib import Path

import typer
from rich.console import Console

from typysetup.core import ProjectConfigLoadError, ProjectConfigManager


class ConfigCommand:
    """Handles displaying project configuration.

    Reads and displays the .typysetup/config.json file
    for a given project directory.
    """

    def __init__(self):
        """Initialize the config command handler."""
        self.console = Console()

    def execute(self, project: str) -> None:
        """Execute the config command to display project configuration.

        Args:
            project: Path to the project directory.
        """
        project_path = Path(project).resolve()

        if not project_path.exists():
            self.console.print(f"[red]Error: Project directory not found: {project_path}[/red]")
            raise typer.Exit(code=1)

        config_manager = ProjectConfigManager(project_path)

        if not config_manager.config_exists():
            self._handle_no_config(project_path)

        self._display_config(config_manager, project_path)

    def _handle_no_config(self, project_path: Path) -> None:
        """Handle case when no configuration exists.

        Args:
            project_path: Path to the project directory.
        """
        self.console.print(f"[yellow]No TyPySetup configuration found in {project_path}[/yellow]")
        self.console.print("[dim]Run 'typysetup setup <path>' to create a new project setup.[/dim]")
        raise typer.Exit(code=1)

    def _display_config(self, config_manager: ProjectConfigManager, project_path: Path) -> None:
        """Display the project configuration.

        Args:
            config_manager: ProjectConfigManager instance.
            project_path: Path to the project directory.
        """
        try:
            config_manager.display_config(project_path=project_path)
        except ProjectConfigLoadError as e:
            self.console.print(f"[red]Error loading configuration: {e}[/red]")
            raise typer.Exit(code=1) from e
        except Exception as e:
            self.console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(code=1) from e
