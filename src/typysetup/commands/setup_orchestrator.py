"""Setup orchestrator for coordinating the interactive setup flow."""

import signal
import sys
import time
from pathlib import Path
from typing import Optional

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from typysetup.core import (
    ConfigLoader,
    DependencyInstaller,
    PreferenceManager,
    ProjectConfigManager,
    PyprojectGenerator,
    VirtualEnvironmentManager,
    VSCodeConfigGenerator,
)
from typysetup.models import DependencySelection, ProjectConfiguration, ProjectMetadata, SetupType
from typysetup.utils.paths import ensure_project_directory
from typysetup.utils.prompts import PromptManager
from typysetup.utils.rollback_context import RollbackContext

console = Console()


class SetupOrchestrator:
    """Orchestrates the interactive setup wizard flow.

    Handles:
    - User prompts for setup type, Python version, package manager
    - Directory validation and creation
    - Flow coordination between setup phases
    - User preference loading and saving
    """

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """Initialize orchestrator with optional config loader.

        Args:
            config_loader: ConfigLoader instance. If None, creates one.
        """
        self.config_loader = config_loader or ConfigLoader()
        self.prompt_manager = PromptManager()
        self.vscode_config_generator = VSCodeConfigGenerator()
        self.venv_manager = VirtualEnvironmentManager()
        self.dependency_installer = DependencyInstaller()
        self.pyproject_generator = PyprojectGenerator()
        self.preference_manager = PreferenceManager()
        self.project_config_manager = ProjectConfigManager()
        self.setup_type: Optional[SetupType] = None
        self.project_path: Optional[Path] = None
        self.project_config: Optional[ProjectConfiguration] = None
        self.dependency_selection: Optional[DependencySelection] = None
        self.selected_extensions: Optional[list] = None
        self.project_metadata: Optional[ProjectMetadata] = None
        self.setup_start_time: Optional[float] = None
        self.rollback: Optional[RollbackContext] = None
        self.cancelled = False

    def _signal_handler(self, signum, frame):
        """Handle SIGINT (Ctrl+C) gracefully.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        console.print("\n[yellow]Setup interrupted by user (Ctrl+C)[/yellow]")
        self.cancelled = True
        # Trigger rollback if context exists
        if self.rollback:
            console.print("[dim]Triggering cleanup...[/dim]")
        raise KeyboardInterrupt()

    def run_setup_wizard(self, project_path: str) -> Optional[ProjectConfiguration]:
        """Run the complete interactive setup wizard.

        Args:
            project_path: Path where project will be set up

        Returns:
            ProjectConfiguration if successful, None if cancelled
        """
        console.print("\n[bold blue]TyPySetup - Python Environment Setup Wizard[/bold blue]")
        console.print("[dim]Step-by-step Python environment configuration[/dim]\n")

        # Register signal handler for Ctrl+C
        original_sigint = signal.signal(signal.SIGINT, self._signal_handler)

        # Start timing
        self.setup_start_time = time.time()

        try:
            # Load user preferences
            try:
                preferences = self.preference_manager.load_preferences()
                if preferences.first_run:
                    console.print("[dim]Welcome! This is your first time using TyPySetup.[/dim]\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load preferences: {e}[/yellow]\n")
                preferences = None

            # Validate and normalize project path
            self.project_path = ensure_project_directory(project_path)
            console.print(f"[green]✓[/green] Project directory: {self.project_path}\n")

            # Step 1: Select setup type
            if not self._select_setup_type():
                console.print("[yellow]Setup cancelled.[/yellow]")
                return None

            # Step 2: Select Python version (if multiple options)
            python_version = self._select_python_version()

            # Step 3: Select package manager
            package_manager = self._select_package_manager()

            # Step 4: Confirm initial selections
            if not self._confirm_setup(python_version, package_manager):
                console.print("[yellow]Setup cancelled.[/yellow]")
                return None

            # Step 5: Select dependency groups (Phase 4)
            self.dependency_selection = self._select_dependency_groups()
            if self.dependency_selection is None:
                console.print("[yellow]Setup cancelled.[/yellow]")
                return None

            # Step 6: Select VSCode extensions (Phase 4)
            self.selected_extensions = self._select_vscode_extensions()
            if self.selected_extensions is None:
                self.selected_extensions = []

            # Step 7: Collect project metadata (Phase 4)
            self.project_metadata = self._collect_project_metadata()
            if self.project_metadata is None:
                console.print("[yellow]Setup cancelled.[/yellow]")
                return None

            # Step 8: Final confirmation with all selections
            if not self._confirm_all_selections(python_version, package_manager):
                console.print("[yellow]Setup cancelled.[/yellow]")
                return None

            # Initialize ProjectConfiguration with all Phase 4 data
            # Note: python_executable and venv_path will be set by Phase 6 after venv creation
            self.project_config = ProjectConfiguration(
                project_path=str(self.project_path),
                setup_type_slug=self.setup_type.slug,
                python_version=python_version,
                python_executable="",  # Will be set after venv creation (Phase 6)
                package_manager=package_manager,
                venv_path="",  # Will be set after venv creation (Phase 6)
                status="running",
                dependency_selections=(
                    self.dependency_selection.model_dump() if self.dependency_selection else None
                ),
                selected_extensions=self.selected_extensions,
                project_metadata=(
                    self.project_metadata.model_dump() if self.project_metadata else None
                ),
            )

            # Use rollback context for all file operations
            with RollbackContext() as rollback:
                self.rollback = rollback

                # Step 9: Generate VSCode configuration (Phase 5)
                if not self._generate_vscode_config():
                    console.print(
                        "[yellow]Setup cancelled during VSCode config generation.[/yellow]"
                    )
                    return None

                # Step 10: Create virtual environment (Phase 6)
                if not self._create_virtual_environment():
                    console.print(
                        "[yellow]Setup cancelled during virtual environment creation.[/yellow]"
                    )
                    return None

                # T121: Cancellation prompt after venv creation
                if not self._prompt_continue("Continue to dependency installation?"):
                    console.print("[yellow]Setup cancelled by user.[/yellow]")
                    return None

                # Step 11: Generate pyproject.toml (Phase 7)
                if not self._generate_pyproject_toml():
                    console.print(
                        "[yellow]Setup cancelled during pyproject.toml generation.[/yellow]"
                    )
                    return None

                # Step 12: Install dependencies (Phase 7)
                if not self._install_dependencies():
                    console.print(
                        "[yellow]Setup cancelled during dependency installation.[/yellow]"
                    )
                    return None

                # T121: Cancellation prompt after dependency installation
                if not self._prompt_continue("Continue to finalize setup?"):
                    console.print("[yellow]Setup cancelled by user.[/yellow]")
                    return None

            # Mark setup as successful
            self.project_config.mark_success()

            # T124: Save project configuration
            try:
                self.project_config_manager.save_config(self.project_config, self.project_path)
                console.print("[dim]Project configuration saved to .typysetup/config.json[/dim]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not save project config: {e}[/yellow]")

            # Calculate duration
            duration_seconds = None
            if self.setup_start_time:
                duration_seconds = time.time() - self.setup_start_time

            # Update preferences after successful setup
            try:
                self.preference_manager.update_after_setup(
                    setup_type_slug=self.setup_type.slug,
                    project_path=str(self.project_path),
                    project_name=(
                        self.project_metadata.project_name if self.project_metadata else None
                    ),
                    python_version=self.project_config.python_version,
                    package_manager=self.project_config.package_manager,
                    success=True,
                    duration_seconds=duration_seconds,
                )
            except Exception as e:
                console.print(f"[yellow]Warning: Could not save preferences: {e}[/yellow]")

            # T127-T128: Display comprehensive setup summary
            self._display_setup_summary(duration_seconds)

            return self.project_config

        except KeyboardInterrupt:
            console.print("\n[red]Setup interrupted by user.[/red]")
            # Record failed setup in preferences
            if self.setup_start_time and self.setup_type and self.project_path:
                try:
                    duration_seconds = time.time() - self.setup_start_time
                    self.preference_manager.add_setup_history(
                        setup_type_slug=self.setup_type.slug,
                        project_path=str(self.project_path),
                        project_name=(
                            self.project_metadata.project_name if self.project_metadata else None
                        ),
                        python_version=(
                            self.project_config.python_version if self.project_config else None
                        ),
                        package_manager=(
                            self.project_config.package_manager if self.project_config else None
                        ),
                        success=False,
                        duration_seconds=duration_seconds,
                    )
                except Exception:
                    pass
            return None
        except Exception as e:
            console.print(f"[red]Error during setup: {e}[/red]")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            # Record failed setup in preferences
            if self.setup_start_time and self.setup_type and self.project_path:
                try:
                    duration_seconds = time.time() - self.setup_start_time
                    self.preference_manager.add_setup_history(
                        setup_type_slug=self.setup_type.slug,
                        project_path=str(self.project_path),
                        project_name=(
                            self.project_metadata.project_name if self.project_metadata else None
                        ),
                        python_version=(
                            self.project_config.python_version if self.project_config else None
                        ),
                        package_manager=(
                            self.project_config.package_manager if self.project_config else None
                        ),
                        success=False,
                        duration_seconds=duration_seconds,
                    )
                except Exception:
                    pass
            return None
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_sigint)
            self.rollback = None

    def _prompt_continue(self, message: str) -> bool:
        """Prompt user to continue with next phase.

        Args:
            message: Prompt message

        Returns:
            True if user wants to continue, False otherwise
        """
        try:
            confirm = questionary.confirm(
                f"{message} [Y/n]",
                auto_enter=True,
                default=True,
            ).ask()
            return confirm if confirm is not None else True
        except KeyboardInterrupt:
            return False

    def _display_setup_summary(self, duration_seconds: Optional[float] = None) -> None:
        """Display comprehensive setup summary with next steps.

        Args:
            duration_seconds: Setup duration in seconds
        """
        console.print("\n[bold green]✓ Setup Complete![/bold green]\n")

        # Create main summary panel
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Field", style="dim", width=20)
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Setup Type", self.setup_type.name)
        summary_table.add_row("Python Version", self.project_config.python_version)
        summary_table.add_row("Package Manager", self.project_config.package_manager)

        if duration_seconds:
            duration_str = f"{duration_seconds:.1f}s"
            summary_table.add_row("Duration", duration_str)

        console.print(
            Panel(summary_table, title="[bold]Setup Summary[/bold]", border_style="green")
        )

        # Dependencies table
        if self.project_config.installed_dependencies or self.dependency_selection:
            console.print("\n[bold cyan]Installed Dependencies[/bold cyan]")

            dep_table = Table(show_header=True, box=None, padding=(0, 2))
            dep_table.add_column("Group", style="yellow", width=15)
            dep_table.add_column("Count", style="green", width=10)

            # Count by group - use installed_dependencies or all_packages
            if self.project_config.installed_dependencies:
                # Count from installed dependencies
                group_counts = {}
                for dep in self.project_config.installed_dependencies:
                    group = dep.from_group or "other"
                    group_counts[group] = group_counts.get(group, 0) + 1

                for group, count in group_counts.items():
                    dep_table.add_row(group.title(), str(count))

                total = len(self.project_config.installed_dependencies)
            elif self.dependency_selection:
                # Use dependency selection if no installed deps yet
                selected_groups = self.dependency_selection.get_selected_groups()
                for group in selected_groups:
                    dep_table.add_row(group.title(), "selected")

                total = self.dependency_selection.get_total_package_count()
            else:
                total = 0

            if total > 0:
                dep_table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

            console.print(dep_table)

        # VSCode configuration
        if self.project_config.venv_path or self.selected_extensions:
            console.print("\n[bold cyan]VSCode Configuration[/bold cyan]")
            vscode_dir = self.project_path / ".vscode"
            console.print(f"  Location: [dim]{vscode_dir}[/dim]")
            if self.selected_extensions:
                console.print(
                    f"  Extensions: [green]{len(self.selected_extensions)}[/green] recommended"
                )

        # Virtual environment
        if self.project_config.venv_path:
            console.print("\n[bold cyan]Virtual Environment[/bold cyan]")
            console.print(f"  Location: [dim]{self.project_config.venv_path}[/dim]")

        # Next steps
        console.print("\n[bold cyan]Next Steps[/bold cyan]")
        next_steps = []

        # Activate venv
        if self.project_config.venv_path:
            venv_path = Path(self.project_config.venv_path)
            if sys.platform == "win32":
                activate_cmd = str(venv_path / "Scripts" / "activate")
            else:
                activate_cmd = f"source {venv_path}/bin/activate"
            next_steps.append(f"Activate environment: [cyan]{activate_cmd}[/cyan]")

        # Open in VSCode
        next_steps.append(f"Open in VSCode: [cyan]code {self.project_path}[/cyan]")

        # Setup-specific commands
        if self.setup_type.slug == "fastapi":
            next_steps.append("Run development server: [cyan]fastapi dev main.py[/cyan]")
        elif self.setup_type.slug == "flask":
            next_steps.append("Run development server: [cyan]flask run[/cyan]")
        elif self.setup_type.slug == "django":
            next_steps.append("Run development server: [cyan]python manage.py runserver[/cyan]")
        elif self.setup_type.slug == "pytest":
            next_steps.append("Run tests: [cyan]pytest[/cyan]")
        elif self.setup_type.slug == "jupyter":
            next_steps.append("Start Jupyter: [cyan]jupyter notebook[/cyan]")
        elif self.setup_type.slug == "data-science":
            next_steps.append("Start Jupyter Lab: [cyan]jupyter lab[/cyan]")

        for i, step in enumerate(next_steps, 1):
            console.print(f"  {i}. {step}")

        console.print("\n[dim]Happy coding![/dim]\n")

    def _select_setup_type(self) -> bool:
        """Prompt user to select a setup type.

        Returns:
            True if setup type selected, False if cancelled
        """
        try:
            setup_types = self.config_loader.load_all_setup_types()
            if not setup_types:
                console.print("[red]No setup types available.[/red]")
                return False

            # Display setup types
            self._display_setup_types(setup_types)

            # Get user choice
            choices = [st.name for st in setup_types]
            chosen_name = questionary.select(
                "Select a setup type:",
                choices=choices,
                qmark="→",
                pointer="→",
            ).ask()

            if chosen_name is None:
                return False

            self.setup_type = next((st for st in setup_types if st.name == chosen_name), None)
            return self.setup_type is not None

        except Exception as e:
            console.print(f"[red]Error selecting setup type: {e}[/red]")
            return False

    def _select_python_version(self) -> str:
        """Prompt user to select or confirm Python version.

        Returns:
            Selected Python version string
        """
        if not self.setup_type:
            return "3.10"

        default_version = self.setup_type.python_version

        confirm = questionary.confirm(
            f"Use Python {default_version}?",
            auto_enter=True,
            default=True,
        ).ask()

        if confirm:
            return default_version

        # If user wants different version
        custom_version = questionary.text(
            "Enter Python version (e.g., 3.9, 3.10, 3.11):",
            default=default_version,
        ).ask()

        return custom_version or default_version

    def _select_package_manager(self) -> str:
        """Prompt user to select package manager.

        Uses saved preference as default if available.

        Returns:
            Selected package manager name
        """
        if not self.setup_type or not self.setup_type.supported_managers:
            return "pip"

        if len(self.setup_type.supported_managers) == 1:
            manager = self.setup_type.supported_managers[0]
            console.print(f"[dim]Using package manager: {manager}[/dim]")
            return manager

        # Try to get preferred manager from preferences
        default_manager = self.setup_type.supported_managers[0]
        try:
            preferences = self.preference_manager.get_preferences()
            if (
                preferences.preferred_manager
                and preferences.preferred_manager in self.setup_type.supported_managers
            ):
                default_manager = preferences.preferred_manager
                console.print(f"[dim]Default from preferences: {default_manager}[/dim]")
        except Exception:
            pass

        chosen = questionary.select(
            "Select package manager:",
            choices=self.setup_type.supported_managers,
            default=default_manager,
            qmark="→",
            pointer="→",
        ).ask()

        return chosen or default_manager

    def _confirm_setup(self, python_version: str, package_manager: str) -> bool:
        """Display setup summary and confirm with user.

        Args:
            python_version: Selected Python version
            package_manager: Selected package manager

        Returns:
            True if user confirms, False otherwise
        """
        console.print("\n[bold]Setup Summary:[/bold]")
        console.print(f"  [dim]Setup Type:[/dim]    {self.setup_type.name}")
        console.print(f"  [dim]Python Version:[/dim] {python_version}")
        console.print(f"  [dim]Package Manager:[/dim] {package_manager}")
        console.print(f"  [dim]Project Path:[/dim]    {self.project_path}\n")

        confirm = questionary.confirm(
            "Proceed with setup?",
            auto_enter=True,
            default=True,
        ).ask()

        return confirm if confirm is not None else True

    def _select_dependency_groups(self) -> Optional[DependencySelection]:
        """Prompt user to select which dependency groups to install.

        Returns:
            DependencySelection instance, or None if cancelled
        """
        return self.prompt_manager.prompt_dependency_groups(self.setup_type)

    def _select_vscode_extensions(self) -> Optional[list]:
        """Prompt user to select which VSCode extensions to install.

        Returns:
            List of selected extension IDs, or None if cancelled
        """
        return self.prompt_manager.prompt_vscode_extensions(self.setup_type)

    def _collect_project_metadata(self) -> Optional[ProjectMetadata]:
        """Collect project metadata (name, description, author, email).

        Returns:
            ProjectMetadata instance, or None if cancelled
        """
        return self.prompt_manager.prompt_collect_all_metadata()

    def _confirm_all_selections(self, python_version: str, package_manager: str) -> bool:
        """Display comprehensive summary of all selections and confirm.

        Args:
            python_version: Selected Python version
            package_manager: Selected package manager

        Returns:
            True if user confirms, False otherwise
        """
        console.print("\n[bold]Complete Setup Summary:[/bold]")
        console.print("[dim]═" * 50 + "[/dim]")

        # Setup type info
        console.print(f"  [dim]Setup Type:[/dim]      {self.setup_type.name}")
        console.print(f"  [dim]Description:[/dim]    {self.setup_type.description}")

        # Python & manager
        console.print(f"  [dim]Python Version:[/dim]  {python_version}")
        console.print(f"  [dim]Package Manager:[/dim] {package_manager}")

        # Dependencies
        if self.dependency_selection:
            console.print(
                f"  [dim]Dependencies:[/dim]    {self.dependency_selection.get_readable_summary()}"
            )

        # Extensions
        if self.selected_extensions:
            ext_count = len(self.selected_extensions)
            console.print(f"  [dim]VSCode Extensions:[/dim] {ext_count} selected")

        # Project info
        if self.project_metadata:
            console.print(f"  [dim]Project Name:[/dim]   {self.project_metadata.project_name}")
            if self.project_metadata.author_name:
                console.print(
                    f"  [dim]Author:[/dim]        {self.project_metadata.get_author_string()}"
                )

        console.print(f"  [dim]Project Path:[/dim]   {self.project_path}")
        console.print("[dim]═" * 50 + "[/dim]\n")

        confirm = questionary.confirm(
            "Proceed with setup?",
            auto_enter=True,
            default=True,
        ).ask()

        return confirm if confirm is not None else True

    def _generate_vscode_config(self) -> bool:
        """Generate VSCode configuration files (Phase 5).

        Returns:
            True if successful, False if cancelled/failed
        """
        if not self.setup_type or not self.project_path or not self.project_config:
            console.print("[red]Error: Setup type or project path not set.[/red]")
            return False

        try:
            console.print("\n[bold blue]Generating VSCode configuration...[/bold blue]")
            self.vscode_config_generator.generate(
                self.setup_type, self.project_config, self.project_path
            )
            return True
        except Exception as e:
            console.print(f"[red]Error generating VSCode config: {e}[/red]")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            return False

    def _create_virtual_environment(self) -> bool:
        """Create Python virtual environment (Phase 6).

        Returns:
            True if successful, False if cancelled/failed
        """
        if not self.project_path or not self.project_config:
            console.print("[red]Error: Project path or config not set.[/red]")
            return False

        try:
            console.print("\n[bold blue]Creating virtual environment...[/bold blue]")

            success = self.venv_manager.create_virtual_environment(
                self.project_path,
                self.project_config.python_version,
                self.project_config,
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
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            return False

    def _generate_pyproject_toml(self) -> bool:
        """Generate pyproject.toml file (Phase 7).

        Returns:
            True if successful, False if failed
        """
        if not self.project_path or not self.project_config or not self.project_metadata:
            console.print("[red]Error: Project path, config, or metadata not set.[/red]")
            return False

        try:
            console.print("\n[bold blue]Generating pyproject.toml...[/bold blue]")

            # Get all packages from dependency selection
            all_packages = []
            if self.dependency_selection:
                all_packages = self.dependency_selection.all_packages

            self.pyproject_generator.generate_pyproject_toml(
                project_path=self.project_path,
                metadata=self.project_metadata,
                dependencies=all_packages,
                python_version=self.project_config.python_version,
            )

            console.print("[green]✓[/green] pyproject.toml generated successfully")
            return True

        except KeyboardInterrupt:
            console.print("\n[yellow]pyproject.toml generation cancelled by user[/yellow]")
            return False

        except Exception as e:
            console.print(f"[red]Error generating pyproject.toml: {e}[/red]")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            return False

    def _install_dependencies(self) -> bool:
        """Install project dependencies (Phase 7).

        Returns:
            True if successful, False if failed
        """
        if not self.project_path or not self.project_config:
            console.print("[red]Error: Project path or config not set.[/red]")
            return False

        if not self.dependency_selection or not self.dependency_selection.all_packages:
            console.print("[yellow]No dependencies selected to install.[/yellow]")
            return True

        try:
            console.print("\n[bold blue]Installing dependencies...[/bold blue]")

            success = self.dependency_installer.install_dependencies(
                packages=self.dependency_selection.all_packages,
                package_manager=self.project_config.package_manager,
                python_executable=self.project_config.python_executable,
                project_path=self.project_path,
                project_config=self.project_config,
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
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            return False

    @staticmethod
    def _display_setup_types(setup_types: list[SetupType]) -> None:
        """Display available setup types in a formatted table.

        Args:
            setup_types: List of SetupType instances
        """
        table = Table(title="Available Setup Types", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="magenta")
        table.add_column("Python Version", style="green")
        table.add_column("Package Managers", style="yellow")

        for st in setup_types:
            managers = ", ".join(st.supported_managers)
            table.add_row(st.name, st.description, st.python_version, managers)

        console.print(table)
        console.print()
