"""History command - show recent setup history."""

import typer
from rich.console import Console
from rich.table import Table

from typysetup.core import PreferenceManager


class HistoryCommand:
    """Handles displaying setup history.

    Shows recent setup operations with status, duration,
    and project details.
    """

    def __init__(self, preference_manager: PreferenceManager | None = None):
        """Initialize with optional preference manager dependency.

        Args:
            preference_manager: PreferenceManager instance. If None, creates one.
        """
        self.preference_manager = preference_manager or PreferenceManager()
        self.console = Console()

    def execute(self, limit: int, verbose: bool) -> None:
        """Execute the history command.

        Args:
            limit: Maximum number of entries to display.
            verbose: If True, show additional columns.
        """
        try:
            prefs = self.preference_manager.load_preferences()

            if not prefs.setup_history:
                self._handle_no_history()
                return

            self._display_history(prefs, limit, verbose)

        except Exception as e:
            self.console.print(f"[red]Error loading history: {e}[/red]")
            raise typer.Exit(code=1) from e

    def _handle_no_history(self) -> None:
        """Handle case when no history exists."""
        self.console.print("[yellow]No setup history found.[/yellow]")
        self.console.print(
            "[dim]Complete a setup with 'typysetup setup <path>' to see history.[/dim]"
        )

    def _display_history(self, prefs, limit: int, verbose: bool) -> None:
        """Display the setup history table.

        Args:
            prefs: UserPreference object with setup history.
            limit: Maximum number of entries to display.
            verbose: If True, show additional columns.
        """
        self.console.print("\n[bold blue]Setup History[/bold blue]\n")

        history_table = self._create_history_table(verbose)
        recent_entries = self._get_recent_entries(prefs.setup_history, limit)

        for entry in recent_entries:
            row = self._format_history_row(entry, verbose)
            history_table.add_row(*row)

        self.console.print(history_table)
        self._display_summary(prefs.setup_history, limit)

    def _create_history_table(self, verbose: bool) -> Table:
        """Create the history table with appropriate columns.

        Args:
            verbose: If True, include additional columns.

        Returns:
            Configured Table instance.
        """
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Date", style="cyan", width=20)
        table.add_column("Status", style="white", width=10)
        table.add_column("Setup Type", style="magenta", width=18)
        table.add_column("Project", style="yellow", width=30)

        if verbose:
            table.add_column("Python", style="green", width=8)
            table.add_column("Manager", style="blue", width=10)

        table.add_column("Duration", style="dim", width=10)
        return table

    def _get_recent_entries(self, history: list, limit: int) -> list:
        """Get the most recent history entries.

        Args:
            history: Full history list.
            limit: Maximum entries to return.

        Returns:
            List of recent entries, newest first.
        """
        if limit and limit > 0:
            sliced = history[-limit:]
        else:
            sliced = history
        return list(reversed(sliced))

    def _format_history_row(self, entry, verbose: bool) -> list:
        """Format a history entry as a table row.

        Args:
            entry: SetupHistoryEntry object.
            verbose: If True, include additional fields.

        Returns:
            List of formatted cell values.
        """
        date_str = entry.timestamp.strftime("%Y-%m-%d %H:%M")
        status_icon = "[green]✓[/green]" if entry.success else "[red]✗[/red]"
        duration_str = f"{entry.duration_seconds:.1f}s" if entry.duration_seconds else "—"

        if entry.project_name:
            project_display = entry.project_name
        else:
            project_display = entry.project_path.split("/")[-1]
            if len(project_display) > 28:
                project_display = project_display[:25] + "..."

        row = [date_str, status_icon, entry.setup_type_slug, project_display]

        if verbose:
            row.append(entry.python_version or "—")
            row.append(entry.package_manager or "—")

        row.append(duration_str)
        return row

    def _display_summary(self, history: list, limit: int) -> None:
        """Display history summary statistics.

        Args:
            history: Full history list.
            limit: Display limit used.
        """
        total = len(history)
        successful = sum(1 for e in history if e.success)
        failed = total - successful

        self.console.print(
            f"\n[dim]Total: {total} setups | "
            f"[green]✓ {successful} successful[/green] | "
            f"[red]✗ {failed} failed[/red][/dim]\n"
        )

        if total > limit:
            self.console.print(
                f"[dim]Showing {limit} most recent. Use --limit to see more.[/dim]\n"
            )
