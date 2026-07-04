"""Interactive selection phase of the setup wizard.

Owns every user-facing prompt that gathers input before any file is touched:
setup type, Python version, package manager, dependency groups, VSCode
extensions, project metadata, and the confirmation dialogs.
"""

import logging
from pathlib import Path

import questionary
from rich.table import Table

from typysetup.core import ConfigLoader, PreferenceManager
from typysetup.models import DependencySelection, ProjectMetadata, SetupType
from typysetup.utils.prompts import PromptManager

from .base import console

logger = logging.getLogger(__name__)

FALLBACK_PYTHON_VERSION = "3.11"
FALLBACK_PACKAGE_MANAGER = "pip"


class SelectionPhase:
    """Collects all interactive selections for the setup wizard."""

    def __init__(
        self,
        config_loader: ConfigLoader,
        prompt_manager: PromptManager,
        preference_manager: PreferenceManager,
    ):
        """Initialize with the collaborators used by the prompts.

        Args:
            config_loader: Loads available setup types
            prompt_manager: Handles dependency/extension/metadata prompts
            preference_manager: Supplies saved user preferences as defaults
        """
        self.config_loader = config_loader
        self.prompt_manager = prompt_manager
        self.preference_manager = preference_manager

    def select_setup_type(self) -> SetupType | None:
        """Prompt user to select a setup type.

        Returns:
            The chosen SetupType, or None if unavailable/cancelled
        """
        try:
            setup_types = self.config_loader.load_all_setup_types()
            if not setup_types:
                console.print("[red]No setup types available.[/red]")
                return None

            self.display_setup_types(setup_types)

            choices = [st.name for st in setup_types]
            chosen_name = questionary.select(
                "Select a setup type:",
                choices=choices,
                qmark="→",
                pointer="→",
            ).ask()

            if chosen_name is None:
                return None

            return next((st for st in setup_types if st.name == chosen_name), None)

        except Exception as e:
            console.print(f"[red]Error selecting setup type: {e}[/red]")
            return None

    def select_python_version(self, setup_type: SetupType | None) -> str:
        """Prompt user to select or confirm Python version.

        Args:
            setup_type: Selected setup type providing the default version

        Returns:
            Selected Python version string
        """
        if not setup_type:
            return FALLBACK_PYTHON_VERSION

        default_version = setup_type.python_version

        confirm = questionary.confirm(
            f"Use Python {default_version}?",
            auto_enter=True,
            default=True,
        ).ask()

        if confirm:
            return default_version

        custom_version = questionary.text(
            "Enter Python version (e.g., 3.11, 3.12, 3.13):",
            default=default_version,
        ).ask()

        return custom_version or default_version

    def select_package_manager(self, setup_type: SetupType | None) -> str:
        """Prompt user to select package manager.

        Uses saved preference as default if available.

        Args:
            setup_type: Selected setup type providing supported managers

        Returns:
            Selected package manager name
        """
        if not setup_type or not setup_type.supported_managers:
            return FALLBACK_PACKAGE_MANAGER

        if len(setup_type.supported_managers) == 1:
            manager: str = setup_type.supported_managers[0]
            console.print(f"[dim]Using package manager: {manager}[/dim]")
            return manager

        default_manager = setup_type.supported_managers[0]
        try:
            preferences = self.preference_manager.get_preferences()
            if (
                preferences.preferred_manager
                and preferences.preferred_manager in setup_type.supported_managers
            ):
                default_manager = preferences.preferred_manager
                console.print(f"[dim]Default from preferences: {default_manager}[/dim]")
        except Exception as preference_error:
            logger.warning(f"Could not read preferred manager from preferences: {preference_error}")

        chosen = questionary.select(
            "Select package manager:",
            choices=setup_type.supported_managers,
            default=default_manager,
            qmark="→",
            pointer="→",
        ).ask()

        return chosen or default_manager

    def confirm_setup(
        self,
        setup_type: SetupType,
        project_path: Path,
        python_version: str,
        package_manager: str,
    ) -> bool:
        """Display setup summary and confirm with user.

        Args:
            setup_type: Selected setup type
            project_path: Project directory path
            python_version: Selected Python version
            package_manager: Selected package manager

        Returns:
            True if user confirms, False otherwise
        """
        console.print("\n[bold]Setup Summary:[/bold]")
        console.print(f"  [dim]Setup Type:[/dim]    {setup_type.name}")
        console.print(f"  [dim]Python Version:[/dim] {python_version}")
        console.print(f"  [dim]Package Manager:[/dim] {package_manager}")
        console.print(f"  [dim]Project Path:[/dim]    {project_path}\n")

        confirm = questionary.confirm(
            "Proceed with setup?",
            auto_enter=True,
            default=True,
        ).ask()

        return confirm if confirm is not None else True

    def select_dependency_groups(self, setup_type: SetupType) -> DependencySelection | None:
        """Prompt user to select which dependency groups to install.

        Args:
            setup_type: Selected setup type

        Returns:
            DependencySelection instance, or None if cancelled
        """
        return self.prompt_manager.prompt_dependency_groups(setup_type)

    def select_vscode_extensions(self, setup_type: SetupType) -> list[str] | None:
        """Prompt user to select which VSCode extensions to install.

        Args:
            setup_type: Selected setup type

        Returns:
            List of selected extension IDs, or None if cancelled
        """
        return self.prompt_manager.prompt_vscode_extensions(setup_type)

    def collect_project_metadata(self) -> ProjectMetadata | None:
        """Collect project metadata (name, description, author, email).

        Returns:
            ProjectMetadata instance, or None if cancelled
        """
        return self.prompt_manager.prompt_collect_all_metadata()

    def confirm_all_selections(
        self,
        setup_type: SetupType,
        project_path: Path,
        python_version: str,
        package_manager: str,
        dependency_selection: DependencySelection | None,
        selected_extensions: list[str] | None,
        project_metadata: ProjectMetadata | None,
    ) -> bool:
        """Display comprehensive summary of all selections and confirm.

        Args:
            setup_type: Selected setup type
            project_path: Project directory path
            python_version: Selected Python version
            package_manager: Selected package manager
            dependency_selection: Selected dependency groups
            selected_extensions: Selected VSCode extension IDs
            project_metadata: Collected project metadata

        Returns:
            True if user confirms, False otherwise
        """
        console.print("\n[bold]Complete Setup Summary:[/bold]")
        console.print("[dim]═" * 50 + "[/dim]")

        console.print(f"  [dim]Setup Type:[/dim]      {setup_type.name}")
        console.print(f"  [dim]Description:[/dim]    {setup_type.description}")

        console.print(f"  [dim]Python Version:[/dim]  {python_version}")
        console.print(f"  [dim]Package Manager:[/dim] {package_manager}")

        if dependency_selection:
            console.print(
                f"  [dim]Dependencies:[/dim]    {dependency_selection.get_readable_summary()}"
            )

        if selected_extensions:
            ext_count = len(selected_extensions)
            console.print(f"  [dim]VSCode Extensions:[/dim] {ext_count} selected")

        if project_metadata:
            console.print(f"  [dim]Project Name:[/dim]   {project_metadata.project_name}")
            if project_metadata.author_name:
                console.print(f"  [dim]Author:[/dim]        {project_metadata.get_author_string()}")

        console.print(f"  [dim]Project Path:[/dim]   {project_path}")
        console.print("[dim]═" * 50 + "[/dim]\n")

        confirm = questionary.confirm(
            "Proceed with setup?",
            auto_enter=True,
            default=True,
        ).ask()

        return confirm if confirm is not None else True

    def prompt_continue(self, message: str) -> bool:
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

    @staticmethod
    def display_setup_types(setup_types: list[SetupType]) -> None:
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
