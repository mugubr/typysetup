"""Preferences command - manage user preferences."""

import typer
from rich.console import Console
from rich.table import Table

from typysetup.core import PreferenceManager


class PreferencesCommand:
    """Handles user preferences management.

    Provides functionality to view current preferences,
    setup history, and reset preferences to defaults.
    """

    def __init__(self, preference_manager: PreferenceManager | None = None):
        """Initialize with optional preference manager dependency.

        Args:
            preference_manager: PreferenceManager instance. If None, creates one.
        """
        self.preference_manager = preference_manager or PreferenceManager()
        self.console = Console()

    def execute(self, show: bool, reset: bool) -> None:
        """Execute the preferences command.

        Args:
            show: If True, display current preferences.
            reset: If True, reset preferences to defaults.
        """
        if show:
            self._show_preferences()
        elif reset:
            self._reset_preferences()
        else:
            self._show_help()

    def _show_preferences(self) -> None:
        """Display current user preferences."""
        try:
            prefs = self.preference_manager.load_preferences()

            self.console.print("[bold blue]User Preferences[/bold blue]\n")

            self._display_main_preferences_table(prefs)
            self._display_preferred_setup_types(prefs)
            self._display_setup_history(prefs)

            self.console.print(
                f"\n[dim]Preferences file: {self.preference_manager.preferences_path}[/dim]"
            )

        except Exception as e:
            self.console.print(f"[red]Error loading preferences: {e}[/red]")
            raise typer.Exit(code=1) from e

    def _display_main_preferences_table(self, prefs) -> None:
        """Display main preferences in a table.

        Args:
            prefs: UserPreference object with preference data.
        """
        table = Table(title="Current Preferences", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="cyan", width=30)
        table.add_column("Value", style="green")

        table.add_row("Preferred Package Manager", prefs.preferred_manager or "Not set")
        table.add_row("Preferred Python Version", prefs.preferred_python_version or "Not set")
        table.add_row("VSCode Config Merge Mode", prefs.vscode_config_merge_mode)
        table.add_row("First Run", "Yes" if prefs.first_run else "No")
        table.add_row("Schema Version", prefs.version)
        table.add_row("Last Updated", prefs.last_updated.strftime("%Y-%m-%d %H:%M:%S UTC"))

        self.console.print(table)
        self.console.print()

    def _display_preferred_setup_types(self, prefs) -> None:
        """Display preferred setup types list.

        Args:
            prefs: UserPreference object with preference data.
        """
        if prefs.preferred_setup_types:
            self.console.print("[bold cyan]Preferred Setup Types[/bold cyan]")
            for i, setup_type in enumerate(prefs.preferred_setup_types, 1):
                self.console.print(f"  {i}. {setup_type}")
            self.console.print()

    def _display_setup_history(self, prefs) -> None:
        """Display setup history table.

        Args:
            prefs: UserPreference object with preference data.
        """
        if prefs.setup_history:
            history_table = Table(
                title="Recent Setup History", show_header=True, header_style="bold cyan"
            )
            history_table.add_column("Date", style="cyan", width=20)
            history_table.add_column("Setup Type", style="magenta", width=20)
            history_table.add_column("Project", style="yellow", width=25)
            history_table.add_column("Status", style="green", width=10)
            history_table.add_column("Duration", style="blue", width=10)

            for entry in prefs.setup_history[-10:]:
                date_str = entry.timestamp.strftime("%Y-%m-%d %H:%M")
                status = "[green]Success[/green]" if entry.success else "[red]Failed[/red]"
                duration = f"{entry.duration_seconds:.1f}s" if entry.duration_seconds else "N/A"
                project_display = entry.project_name or entry.project_path.split("/")[-1]

                history_table.add_row(
                    date_str, entry.setup_type_slug, project_display, status, duration
                )

            self.console.print(history_table)
            self.console.print(
                f"\n[dim]Showing last {min(10, len(prefs.setup_history))} "
                f"of {len(prefs.setup_history)} total entries[/dim]"
            )
        else:
            self.console.print("[dim]No setup history yet.[/dim]\n")

    def _reset_preferences(self) -> None:
        """Reset preferences to defaults with confirmation."""
        try:
            import questionary

            confirm = questionary.confirm(
                "Are you sure you want to reset all preferences to defaults?",
                default=False,
            ).ask()

            if not confirm:
                self.console.print("[yellow]Reset cancelled.[/yellow]")
                return

            self.preference_manager.reset_to_defaults()
            self.console.print("[green]Preferences reset to defaults successfully![/green]")
            self.console.print(
                f"[dim]Backup created at: "
                f"{self.preference_manager.preferences_path.with_suffix('.json.backup_*')}[/dim]"
            )

        except Exception as e:
            self.console.print(f"[red]Error resetting preferences: {e}[/red]")
            raise typer.Exit(code=1) from e

    def _show_help(self) -> None:
        """Show preferences command help."""
        self.console.print("[bold blue]TyPySetup Preferences[/bold blue]\n")
        self.console.print("Manage your TyPySetup user preferences.\n")
        self.console.print("Commands:")
        self.console.print("  [cyan]--show[/cyan]   Display current preferences and setup history")
        self.console.print("  [cyan]--reset[/cyan]  Reset all preferences to default values\n")
        self.console.print("Example:")
        self.console.print("  [dim]typysetup preferences --show[/dim]")
        self.console.print("  [dim]typysetup preferences --reset[/dim]")
