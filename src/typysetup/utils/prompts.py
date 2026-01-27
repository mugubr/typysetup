"""Questionary-based prompt manager for interactive setup wizard."""

import logging
from typing import List, Optional

import questionary
from rich.console import Console

from typysetup.models import DependencySelection, ProjectMetadata, SetupType

logger = logging.getLogger(__name__)
console = Console()


class PromptManager:
    """Manages all interactive Questionary prompts for setup wizard.

    Provides methods for:
    - Dependency group selection
    - VSCode extension selection
    - Project metadata collection (name, description, author, email)
    """

    def __init__(self):
        """Initialize prompt manager."""
        self.max_retries = 3

    def prompt_dependency_groups(self, setup_type: SetupType) -> Optional[DependencySelection]:
        """Prompt user to select which dependency groups to install.

        Args:
            setup_type: Setup type with available dependency groups

        Returns:
            DependencySelection instance, or None if cancelled
        """
        console.print("\n[bold blue]Select Dependency Groups[/bold blue]")
        console.print(f"[dim]{setup_type.description}[/dim]\n")

        # Display group information
        groups = setup_type.get_dependency_groups()
        console.print("[bold]Available Groups:[/bold]")
        for group_name in groups:
            count = setup_type.get_group_dependency_count(group_name)
            is_core = " [required]" if group_name == "core" else ""
            console.print(f"  • {group_name}: {count} packages{is_core}")
        console.print()

        # Prepare choice map for display
        choice_map = {}
        for group_name in groups:
            count = setup_type.get_group_dependency_count(group_name)
            choice_text = f"{group_name} ({count} packages)"

            if group_name == "core":
                choice_text += " [required]"

            choice_map[group_name] = choice_text

        # Use checkbox for selections
        selected = questionary.checkbox(
            "Select groups to install (use Space to toggle, Enter to confirm):",
            choices=[
                {
                    "name": choice_map[group_name],
                    "value": group_name,
                    "disabled": group_name == "core",  # Can't deselect core
                }
                for group_name in groups
            ],
        ).ask()

        if selected is None:
            return None

        # Ensure core is always selected
        if "core" not in selected:
            selected.append("core")

        # Build selection dict
        selected_dict = {group: group in selected for group in groups}

        # Get all packages from selected groups
        all_packages = []
        for group_name in selected:
            packages = setup_type.get_group_by_name(group_name)
            if packages:
                all_packages.extend(packages)

        # Create DependencySelection
        try:
            selection = DependencySelection(
                setup_type_slug=setup_type.slug,
                selected_groups=selected_dict,
                all_packages=all_packages,
                group_descriptions={g: f"{g.title()} dependencies" for g in groups},
            )
            return selection
        except ValueError as e:
            console.print(f"[red]Error creating dependency selection: {e}[/red]")
            return None

    def prompt_vscode_extensions(self, setup_type: SetupType) -> Optional[List[str]]:
        """Prompt user to select which VSCode extensions to install.

        Args:
            setup_type: Setup type with recommended extensions

        Returns:
            List of selected extension IDs, or None if cancelled
        """
        if not setup_type.vscode_extensions:
            console.print("[dim]No VSCode extensions recommended for this setup type.[/dim]")
            return []

        console.print("\n[bold blue]VSCode Extensions[/bold blue]")
        console.print("[dim]Recommended extensions for this setup type[/dim]\n")

        # Display available extensions
        choices = []
        for ext_id in setup_type.vscode_extensions:
            # Extract publisher and name for better display
            parts = ext_id.split(".")
            if len(parts) >= 2:
                display_name = f"{parts[0]}.{parts[1]}"
            else:
                display_name = ext_id

            choices.append(
                {
                    "name": display_name,
                    "value": ext_id,
                }
            )

        selected = questionary.checkbox(
            "Select extensions to install (all are optional):",
            choices=choices,
        ).ask()

        if selected is None:
            return None

        return selected

    def prompt_project_name(self) -> Optional[str]:
        """Prompt user for project name with validation.

        Returns:
            Project name, or None if cancelled
        """
        console.print("\n[bold blue]Project Information[/bold blue]\n")

        for attempt in range(self.max_retries):
            project_name = questionary.text(
                "Project name (must be valid Python package name):",
                default="my_project",
                validate=lambda x: self._validate_package_name(x),
            ).ask()

            if project_name is None:
                return None

            try:
                # Use the validator from ProjectMetadata
                ProjectMetadata.is_valid_package_name(project_name)
                return project_name
            except ValueError as e:
                console.print(f"[red]Invalid project name: {e}[/red]")
                if attempt < self.max_retries - 1:
                    console.print("[dim]Please try again.[/dim]\n")
                else:
                    console.print("[red]Maximum retries exceeded. Setup cancelled.[/red]")
                    return None

        return None

    def prompt_project_description(self) -> Optional[str]:
        """Prompt user for optional project description.

        Returns:
            Project description, or None if skipped/cancelled
        """
        description = questionary.text(
            "Project description (optional, press Enter to skip):",
            default="",
            validate=self._validate_description,
        ).ask()

        if description is None:
            return None

        # Return None if empty string (user skipped)
        return description if description.strip() else None

    def prompt_author_name(self) -> Optional[str]:
        """Prompt user for optional author name.

        Returns:
            Author name, or None if skipped/cancelled
        """
        author = questionary.text(
            "Author name (optional, press Enter to skip):",
            default="",
        ).ask()

        if author is None:
            return None

        # Return None if empty string (user skipped)
        return author if author.strip() else None

    def prompt_author_email(self) -> Optional[str]:
        """Prompt user for optional author email with validation.

        Returns:
            Author email, or None if skipped/cancelled
        """
        for attempt in range(self.max_retries):
            email = questionary.text(
                "Author email (optional, press Enter to skip):",
                default="",
                validate=self._validate_email_optional,
            ).ask()

            if email is None:
                return None

            # Return None if empty string (user skipped)
            if not email.strip():
                return None

            # Try to create ProjectMetadata to validate email
            try:
                ProjectMetadata(
                    project_name="temp",  # Dummy value for validation
                    author_email=email,
                )
                return email
            except ValueError as e:
                console.print(f"[red]Invalid email: {e}[/red]")
                if attempt < self.max_retries - 1:
                    console.print("[dim]Please try again.[/dim]\n")
                else:
                    console.print("[yellow]Skipping email. Using author name only.[/yellow]")
                    return None

        return None

    def prompt_collect_all_metadata(self) -> Optional[ProjectMetadata]:
        """Collect all project metadata in sequence.

        Returns:
            ProjectMetadata instance, or None if cancelled
        """
        # Collect project name (required)
        project_name = self.prompt_project_name()
        if project_name is None:
            return None

        # Collect description (optional)
        description = self.prompt_project_description()

        # Collect author (optional)
        author = self.prompt_author_name()

        # Collect email (optional, only if author provided)
        email = None
        if author:
            email = self.prompt_author_email()

        # Create and validate ProjectMetadata
        try:
            metadata = ProjectMetadata(
                project_name=project_name,
                project_description=description,
                author_name=author,
                author_email=email,
            )
            return metadata
        except ValueError as e:
            console.print(f"[red]Error creating project metadata: {e}[/red]")
            return None

    @staticmethod
    def _validate_package_name(name: str) -> bool:
        """Validate package name format.

        Args:
            name: Name to validate

        Returns:
            True if valid, raises exception otherwise
        """
        if not name or len(name) < 3:
            raise questionary.ValidationError(
                message="Project name must be at least 3 characters",
                cursor_position=len(name),
            )

        if not ProjectMetadata.is_valid_package_name(name):
            raise questionary.ValidationError(
                message="Must be lowercase alphanumeric + underscores, no hyphens",
                cursor_position=len(name),
            )

        return True

    @staticmethod
    def _validate_description(description: str) -> bool:
        """Validate description length.

        Args:
            description: Description to validate

        Returns:
            True if valid
        """
        if len(description) > 500:
            raise questionary.ValidationError(
                message="Description must be 500 characters or less",
                cursor_position=len(description),
            )
        return True

    @staticmethod
    def _validate_email_optional(email: str) -> bool:
        """Validate email format (allows empty for skipping).

        Args:
            email: Email to validate (can be empty)

        Returns:
            True if valid
        """
        if not email.strip():
            # Empty is OK (user is skipping)
            return True

        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            raise questionary.ValidationError(
                message="Invalid email format. Expected: user@example.com",
                cursor_position=len(email),
            )

        return True
