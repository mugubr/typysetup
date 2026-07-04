"""Scaffolding phase of the setup wizard.

Generates the project skeleton files: .gitignore, VSCode configuration and
pyproject.toml. Each step reports success/failure and never raises to the
caller — failures are printed and returned as False.
"""

import logging
from pathlib import Path

from typysetup.core import GitignoreGenerator, PyprojectGenerator, VSCodeConfigGenerator
from typysetup.models import (
    DependencySelection,
    ProjectConfiguration,
    ProjectMetadata,
    SetupType,
)

from .base import console, print_traceback_if_verbose

logger = logging.getLogger(__name__)


class ScaffoldPhase:
    """Generates project scaffolding files (gitignore, VSCode, pyproject)."""

    def __init__(
        self,
        vscode_config_generator: VSCodeConfigGenerator,
        pyproject_generator: PyprojectGenerator,
    ):
        """Initialize with the file generators.

        Args:
            vscode_config_generator: Generates .vscode configuration
            pyproject_generator: Generates pyproject.toml
        """
        self.vscode_config_generator = vscode_config_generator
        self.pyproject_generator = pyproject_generator

    def generate_gitignore(self, project_path: Path) -> bool:
        """Generate .gitignore file.

        Args:
            project_path: Project directory path

        Returns:
            True if successful, False if failed
        """
        try:
            console.print("\n[bold blue]Generating .gitignore...[/bold blue]")
            gitignore_path = GitignoreGenerator.generate_gitignore(project_path)
            console.print(f"[green]✓[/green] .gitignore created at {gitignore_path}")
            return True
        except Exception as e:
            console.print(f"[red]Error generating .gitignore: {e}[/red]")
            print_traceback_if_verbose()
            return False

    def generate_vscode_config(
        self,
        setup_type: SetupType,
        project_config: ProjectConfiguration,
        project_path: Path,
    ) -> bool:
        """Generate VSCode configuration files.

        Args:
            setup_type: Selected setup type
            project_config: Project configuration
            project_path: Project directory path

        Returns:
            True if successful, False if cancelled/failed
        """
        try:
            console.print("\n[bold blue]Generating VSCode configuration...[/bold blue]")
            self.vscode_config_generator.generate(setup_type, project_config, project_path)
            return True
        except Exception as e:
            console.print(f"[red]Error generating VSCode config: {e}[/red]")
            print_traceback_if_verbose()
            return False

    def generate_pyproject_toml(
        self,
        project_path: Path,
        metadata: ProjectMetadata,
        dependency_selection: DependencySelection | None,
        python_version: str,
    ) -> bool:
        """Generate pyproject.toml file.

        Args:
            project_path: Project directory path
            metadata: Project metadata (name, author, ...)
            dependency_selection: Selected dependency groups
            python_version: Python version requirement

        Returns:
            True if successful, False if failed
        """
        try:
            console.print("\n[bold blue]Generating pyproject.toml...[/bold blue]")

            all_packages: list[str] = []
            if dependency_selection:
                all_packages = dependency_selection.all_packages

            self.pyproject_generator.generate_pyproject_toml(
                project_path=project_path,
                metadata=metadata,
                dependencies=all_packages,
                python_version=python_version,
            )

            console.print("[green]✓[/green] pyproject.toml generated successfully")
            return True

        except KeyboardInterrupt:
            console.print("\n[yellow]pyproject.toml generation cancelled by user[/yellow]")
            return False

        except Exception as e:
            console.print(f"[red]Error generating pyproject.toml: {e}[/red]")
            print_traceback_if_verbose()
            return False
