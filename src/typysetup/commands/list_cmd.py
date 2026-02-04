"""List command - show available setup type templates."""

import typer
from rich.console import Console
from rich.table import Table

from typysetup.core import ConfigLoader


class ListCommand:
    """Handles listing available setup type templates.

    Displays all configured setup types in a formatted table
    with name, description, Python version, and supported managers.
    """

    def __init__(self, config_loader: ConfigLoader):
        """Initialize with config loader dependency.

        Args:
            config_loader: ConfigLoader instance for loading setup types.
        """
        self.config_loader = config_loader
        self.console = Console()

    def execute(self) -> None:
        """Execute the list command to display available setup types."""
        self.console.print("[bold blue]Available Setup Types[/bold blue]\n")

        try:
            setup_types = self.config_loader.load_all_setup_types()

            if not setup_types:
                self.console.print("[yellow]No setup types found.[/yellow]")
                return

            self._display_setup_types_table(setup_types)

        except Exception as e:
            self.console.print(f"[red]Error loading setup types: {e}[/red]")
            raise typer.Exit(code=1) from e

    def _display_setup_types_table(self, setup_types: list) -> None:
        """Display setup types in a formatted table.

        Args:
            setup_types: List of SetupType objects to display.
        """
        table = Table(title="TyPySetup Templates", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="magenta")
        table.add_column("Python Version", style="green")
        table.add_column("Package Managers", style="yellow")
        table.add_column("Tags", style="blue")

        for setup_type in setup_types:
            managers = ", ".join(setup_type.supported_managers)
            tags = ", ".join(setup_type.tags) if setup_type.tags else "—"
            table.add_row(
                setup_type.name,
                setup_type.description,
                setup_type.python_version,
                managers,
                tags,
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {len(setup_types)} setup types available[/dim]")
