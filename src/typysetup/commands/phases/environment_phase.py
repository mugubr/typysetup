"""Environment phase of the setup wizard.

Creates the virtual environment and installs the selected dependencies.
Each step reports success/failure and never raises to the caller.
"""

import logging
from pathlib import Path

from typysetup.core import DependencyInstaller, VirtualEnvironmentManager
from typysetup.models import DependencySelection, ProjectConfiguration

from .base import console, print_traceback_if_verbose

logger = logging.getLogger(__name__)


class EnvironmentPhase:
    """Creates the venv and installs dependencies into it."""

    def __init__(
        self,
        venv_manager: VirtualEnvironmentManager,
        dependency_installer: DependencyInstaller,
    ):
        """Initialize with the environment collaborators.

        Args:
            venv_manager: Creates and validates virtual environments
            dependency_installer: Installs packages with the chosen manager
        """
        self.venv_manager = venv_manager
        self.dependency_installer = dependency_installer

    def create_virtual_environment(
        self,
        project_path: Path,
        project_config: ProjectConfiguration,
    ) -> bool:
        """Create Python virtual environment.

        Args:
            project_path: Project directory path
            project_config: Project configuration (updated with venv paths)

        Returns:
            True if successful, False if cancelled/failed
        """
        try:
            console.print("\n[bold blue]Creating virtual environment...[/bold blue]")

            success = self.venv_manager.create_virtual_environment(
                project_path,
                project_config.python_version,
                project_config,
            )

            if not success:
                return False

            console.print("[green]✓[/green] Virtual environment created successfully")
            return True

        except KeyboardInterrupt:
            console.print("\n[yellow]Virtual environment creation cancelled by user[/yellow]")
            return False

        except Exception as e:
            console.print(f"[red]Error creating virtual environment: {e}[/red]")
            print_traceback_if_verbose()
            return False

    def install_dependencies(
        self,
        project_path: Path,
        project_config: ProjectConfiguration,
        dependency_selection: DependencySelection | None,
    ) -> bool:
        """Install project dependencies.

        Args:
            project_path: Project directory path
            project_config: Project configuration
            dependency_selection: Selected dependency groups

        Returns:
            True if successful, False if failed
        """
        if not dependency_selection or not dependency_selection.all_packages:
            console.print("[yellow]No dependencies selected to install.[/yellow]")
            return True

        try:
            console.print("\n[bold blue]Installing dependencies...[/bold blue]")

            success = self.dependency_installer.install_dependencies(
                packages=dependency_selection.all_packages,
                package_manager=project_config.package_manager,
                python_executable=project_config.python_executable,
                project_path=project_path,
                project_config=project_config,
            )

            if not success:
                return False

            console.print("[green]✓[/green] Dependencies installed successfully")
            return True

        except KeyboardInterrupt:
            console.print("\n[yellow]Dependency installation cancelled by user[/yellow]")
            return False

        except Exception as e:
            console.print(f"[red]Error installing dependencies: {e}[/red]")
            print_traceback_if_verbose()
            return False
