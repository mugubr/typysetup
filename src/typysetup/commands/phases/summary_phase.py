"""Summary phase of the setup wizard.

Renders the final setup report: what was configured, where, and the
suggested next steps for the user.
"""

import sys
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from typysetup.models import (
    DependencySelection,
    ProjectConfiguration,
    SetupType,
)

from .base import console

# Setup-type specific "next step" commands shown at the end of the wizard
NEXT_STEP_COMMANDS = {
    "fastapi": "Run development server: [cyan]fastapi dev main.py[/cyan]",
    "flask": "Run development server: [cyan]flask run[/cyan]",
    "django": "Run development server: [cyan]python manage.py runserver[/cyan]",
    "pytest": "Run tests: [cyan]pytest[/cyan]",
    "jupyter": "Start Jupyter: [cyan]jupyter notebook[/cyan]",
    "data-science": "Start Jupyter Lab: [cyan]jupyter lab[/cyan]",
}


class SummaryPhase:
    """Displays the final setup summary and next steps."""

    def display_setup_summary(
        self,
        setup_type: SetupType,
        project_path: Path,
        project_config: ProjectConfiguration,
        dependency_selection: DependencySelection | None,
        selected_extensions: list[str] | None,
        duration_seconds: float | None = None,
    ) -> None:
        """Display comprehensive setup summary with next steps.

        Args:
            setup_type: Selected setup type
            project_path: Project directory path
            project_config: Final project configuration
            dependency_selection: Selected dependency groups
            selected_extensions: Selected VSCode extension IDs
            duration_seconds: Setup duration in seconds
        """
        console.print("\n[bold green]✓ Setup Complete![/bold green]\n")

        self._display_summary_panel(setup_type, project_config, duration_seconds)
        self._display_dependencies(project_config, dependency_selection)
        self._display_vscode_info(project_path, project_config, selected_extensions)
        self._display_venv_info(project_config)
        self._display_next_steps(setup_type, project_path, project_config)

        console.print("\n[dim]Happy coding![/dim]\n")

    @staticmethod
    def _display_summary_panel(
        setup_type: SetupType,
        project_config: ProjectConfiguration,
        duration_seconds: float | None,
    ) -> None:
        """Render the main summary panel."""
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Field", style="dim", width=20)
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Setup Type", setup_type.name)
        summary_table.add_row("Python Version", project_config.python_version)
        summary_table.add_row("Package Manager", project_config.package_manager)

        if duration_seconds:
            summary_table.add_row("Duration", f"{duration_seconds:.1f}s")

        console.print(
            Panel(summary_table, title="[bold]Setup Summary[/bold]", border_style="green")
        )

    @staticmethod
    def _display_dependencies(
        project_config: ProjectConfiguration,
        dependency_selection: DependencySelection | None,
    ) -> None:
        """Render the installed dependencies table."""
        if not project_config.installed_dependencies and not dependency_selection:
            return

        console.print("\n[bold cyan]Installed Dependencies[/bold cyan]")

        dep_table = Table(show_header=True, box=None, padding=(0, 2))
        dep_table.add_column("Group", style="yellow", width=15)
        dep_table.add_column("Count", style="green", width=10)

        if project_config.installed_dependencies:
            group_counts: dict[str, int] = {}
            for dep in project_config.installed_dependencies:
                group = dep.from_group or "other"
                group_counts[group] = group_counts.get(group, 0) + 1

            for group, count in group_counts.items():
                dep_table.add_row(group.title(), str(count))

            total = len(project_config.installed_dependencies)
        elif dependency_selection:
            for group in dependency_selection.get_selected_groups():
                dep_table.add_row(group.title(), "selected")

            total = dependency_selection.get_total_package_count()
        else:
            total = 0

        if total > 0:
            dep_table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

        console.print(dep_table)

    @staticmethod
    def _display_vscode_info(
        project_path: Path,
        project_config: ProjectConfiguration,
        selected_extensions: list[str] | None,
    ) -> None:
        """Render the VSCode configuration section."""
        if not project_config.venv_path and not selected_extensions:
            return

        console.print("\n[bold cyan]VSCode Configuration[/bold cyan]")
        vscode_dir = project_path / ".vscode"
        console.print(f"  Location: [dim]{vscode_dir}[/dim]")
        if selected_extensions:
            console.print(f"  Extensions: [green]{len(selected_extensions)}[/green] recommended")

    @staticmethod
    def _display_venv_info(project_config: ProjectConfiguration) -> None:
        """Render the virtual environment section."""
        if not project_config.venv_path:
            return

        console.print("\n[bold cyan]Virtual Environment[/bold cyan]")
        console.print(f"  Location: [dim]{project_config.venv_path}[/dim]")

    @staticmethod
    def _display_next_steps(
        setup_type: SetupType,
        project_path: Path,
        project_config: ProjectConfiguration,
    ) -> None:
        """Render the numbered next-steps list."""
        console.print("\n[bold cyan]Next Steps[/bold cyan]")
        next_steps = []

        if project_config.venv_path:
            venv_path = Path(project_config.venv_path)
            if sys.platform == "win32":
                activate_cmd = str(venv_path / "Scripts" / "activate")
            else:
                activate_cmd = f"source {venv_path}/bin/activate"
            next_steps.append(f"Activate environment: [cyan]{activate_cmd}[/cyan]")

        next_steps.append(f"Open in VSCode: [cyan]code {project_path}[/cyan]")

        setup_command = NEXT_STEP_COMMANDS.get(setup_type.slug)
        if setup_command:
            next_steps.append(setup_command)

        for i, step in enumerate(next_steps, 1):
            console.print(f"  {i}. {step}")
