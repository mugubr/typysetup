"""Setup orchestrator for coordinating the interactive setup flow.

The orchestrator drives the wizard flow and owns the shared state; the
actual work of each step lives in the phase classes under
``typysetup.commands.phases``.
"""

import logging
import signal
import sys
import time
from pathlib import Path
from types import FrameType

from rich.console import Console

from typysetup.commands.phases import (
    EnvironmentPhase,
    ScaffoldPhase,
    SelectionPhase,
    SummaryPhase,
)
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
logger = logging.getLogger(__name__)


class SetupOrchestrator:
    """Orchestrates the interactive setup wizard flow.

    Coordinates the wizard phases:
    - SelectionPhase: user prompts for setup type, version, manager, ...
    - ScaffoldPhase: .gitignore, VSCode config and pyproject.toml
    - EnvironmentPhase: venv creation and dependency installation
    - SummaryPhase: final report

    Also handles preference loading/saving, setup history and rollback.
    """

    def __init__(self, config_loader: ConfigLoader | None = None):
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

        # Wizard phases share the collaborators above
        self.selection_phase = SelectionPhase(
            self.config_loader, self.prompt_manager, self.preference_manager
        )
        self.scaffold_phase = ScaffoldPhase(self.vscode_config_generator, self.pyproject_generator)
        self.environment_phase = EnvironmentPhase(self.venv_manager, self.dependency_installer)
        self.summary_phase = SummaryPhase()

        self.setup_type: SetupType | None = None
        self.project_path: Path | None = None
        self.project_config: ProjectConfiguration | None = None
        self.dependency_selection: DependencySelection | None = None
        self.selected_extensions: list[str] | None = None
        self.project_metadata: ProjectMetadata | None = None
        self.setup_start_time: float | None = None
        self.rollback: RollbackContext | None = None
        self.cancelled = False

    def _signal_handler(self, signum: int, frame: FrameType | None) -> None:
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

    def run_setup_wizard(self, project_path: str) -> ProjectConfiguration | None:
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

            # Validate and normalize project path
            self.project_path = ensure_project_directory(project_path)
            console.print(f"[green]✓[/green] Project directory: {self.project_path}\n")

            # Generate .gitignore (Phase 1)
            if not self._generate_gitignore():
                console.print("[yellow]Setup cancelled during .gitignore generation.[/yellow]")
                return None

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
            # Note: python_executable and venv_path will be set after venv creation
            assert self.setup_type is not None  # guaranteed by _select_setup_type
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
            self._record_failed_setup()
            return None
        except Exception as e:
            console.print(f"[red]Error during setup: {e}[/red]")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            self._record_failed_setup()
            return None
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_sigint)
            self.rollback = None

    def _record_failed_setup(self) -> None:
        """Record a failed/cancelled setup in the preference history."""
        if not (self.setup_start_time and self.setup_type and self.project_path):
            return

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
        except Exception as history_error:
            logger.warning(f"Could not record setup history: {history_error}")

    # -- Phase delegates -------------------------------------------------
    #
    # These thin wrappers keep the orchestrator's historical private API
    # (used heavily by tests) while the real logic lives in the phases.

    def _prompt_continue(self, message: str) -> bool:
        """Prompt user to continue with next phase."""
        return self.selection_phase.prompt_continue(message)

    def _select_setup_type(self) -> bool:
        """Prompt user to select a setup type.

        Returns:
            True if setup type selected, False if cancelled
        """
        self.setup_type = self.selection_phase.select_setup_type()
        return self.setup_type is not None

    def _select_python_version(self) -> str:
        """Prompt user to select or confirm Python version."""
        return self.selection_phase.select_python_version(self.setup_type)

    def _select_package_manager(self) -> str:
        """Prompt user to select package manager."""
        return self.selection_phase.select_package_manager(self.setup_type)

    def _confirm_setup(self, python_version: str, package_manager: str) -> bool:
        """Display setup summary and confirm with user."""
        if self.setup_type is None or self.project_path is None:
            console.print("[red]Error: Setup type or project path not set.[/red]")
            return False
        return self.selection_phase.confirm_setup(
            self.setup_type, self.project_path, python_version, package_manager
        )

    def _select_dependency_groups(self) -> DependencySelection | None:
        """Prompt user to select which dependency groups to install."""
        if self.setup_type is None:
            return None
        return self.selection_phase.select_dependency_groups(self.setup_type)

    def _select_vscode_extensions(self) -> list[str] | None:
        """Prompt user to select which VSCode extensions to install."""
        if self.setup_type is None:
            return None
        return self.selection_phase.select_vscode_extensions(self.setup_type)

    def _collect_project_metadata(self) -> ProjectMetadata | None:
        """Collect project metadata (name, description, author, email)."""
        return self.selection_phase.collect_project_metadata()

    def _confirm_all_selections(self, python_version: str, package_manager: str) -> bool:
        """Display comprehensive summary of all selections and confirm."""
        if self.setup_type is None or self.project_path is None:
            console.print("[red]Error: Setup type or project path not set.[/red]")
            return False
        return self.selection_phase.confirm_all_selections(
            self.setup_type,
            self.project_path,
            python_version,
            package_manager,
            self.dependency_selection,
            self.selected_extensions,
            self.project_metadata,
        )

    def _generate_gitignore(self) -> bool:
        """Generate .gitignore file (Phase 1)."""
        if not self.project_path:
            console.print("[red]Error: Project path not set.[/red]")
            return False
        return self.scaffold_phase.generate_gitignore(self.project_path)

    def _generate_vscode_config(self) -> bool:
        """Generate VSCode configuration files (Phase 5)."""
        if not self.setup_type or not self.project_path or not self.project_config:
            console.print("[red]Error: Setup type or project path not set.[/red]")
            return False
        return self.scaffold_phase.generate_vscode_config(
            self.setup_type, self.project_config, self.project_path
        )

    def _create_virtual_environment(self) -> bool:
        """Create Python virtual environment (Phase 6)."""
        if not self.project_path or not self.project_config:
            console.print("[red]Error: Project path or config not set.[/red]")
            return False
        return self.environment_phase.create_virtual_environment(
            self.project_path, self.project_config
        )

    def _generate_pyproject_toml(self) -> bool:
        """Generate pyproject.toml file (Phase 7)."""
        if not self.project_path or not self.project_config or not self.project_metadata:
            console.print("[red]Error: Project path, config, or metadata not set.[/red]")
            return False
        return self.scaffold_phase.generate_pyproject_toml(
            self.project_path,
            self.project_metadata,
            self.dependency_selection,
            self.project_config.python_version,
        )

    def _install_dependencies(self) -> bool:
        """Install project dependencies (Phase 7)."""
        if not self.project_path or not self.project_config:
            console.print("[red]Error: Project path or config not set.[/red]")
            return False
        return self.environment_phase.install_dependencies(
            self.project_path, self.project_config, self.dependency_selection
        )

    def _display_setup_summary(self, duration_seconds: float | None = None) -> None:
        """Display comprehensive setup summary with next steps."""
        if not self.setup_type or not self.project_path or not self.project_config:
            return
        self.summary_phase.display_setup_summary(
            self.setup_type,
            self.project_path,
            self.project_config,
            self.dependency_selection,
            self.selected_extensions,
            duration_seconds,
        )

    @staticmethod
    def _display_setup_types(setup_types: list[SetupType]) -> None:
        """Display available setup types in a formatted table."""
        SelectionPhase.display_setup_types(setup_types)
