"""Main Typer application entry point."""

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from typysetup import __version__
from typysetup.commands.setup_orchestrator import SetupOrchestrator
from typysetup.core import ConfigLoader

app = typer.Typer(
    name="typysetup",
    help="Interactive Python environment setup CLI for VSCode",
    no_args_is_help=True,
)

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize config loader
config_loader = ConfigLoader()


@app.command()
def setup(
    path: str = typer.Argument(..., help="Project directory path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
) -> None:
    """
    Interactive setup wizard for Python environment.

    Guides you through selecting a project type, configuring dependencies,
    and setting up VSCode integration.
    """
    if verbose:
        logging.getLogger("typysetup").setLevel(logging.DEBUG)

    orchestrator = SetupOrchestrator(config_loader)
    project_config = orchestrator.run_setup_wizard(path)

    if project_config:
        console.print("\n[green]✓ Setup configuration created successfully![/green]")
        logger.info(f"Setup created at {project_config.project_path}")
    else:
        raise typer.Exit(code=1)


@app.command()
def list() -> None:
    """List all available setup type templates."""
    console.print("[bold blue]Available Setup Types[/bold blue]\n")

    try:
        setup_types = config_loader.load_all_setup_types()

        if not setup_types:
            console.print("[yellow]No setup types found.[/yellow]")
            return

        # Display in table format
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

        console.print(table)
        console.print(f"\n[dim]Total: {len(setup_types)} setup types available[/dim]")

    except Exception as e:
        console.print(f"[red]Error loading setup types: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def preferences(
    show: bool = typer.Option(False, "--show", help="Show current preferences"),
    reset: bool = typer.Option(False, "--reset", help="Reset to defaults"),
) -> None:
    """Manage user preferences."""
    from typysetup.core import PreferenceManager

    pref_manager = PreferenceManager()

    if show:
        try:
            prefs = pref_manager.load_preferences()

            console.print("[bold blue]User Preferences[/bold blue]\n")

            # Create main preferences table
            table = Table(title="Current Preferences", show_header=True, header_style="bold cyan")
            table.add_column("Setting", style="cyan", width=30)
            table.add_column("Value", style="green")

            table.add_row("Preferred Package Manager", prefs.preferred_manager or "Not set")
            table.add_row("Preferred Python Version", prefs.preferred_python_version or "Not set")
            table.add_row("VSCode Config Merge Mode", prefs.vscode_config_merge_mode)
            table.add_row("First Run", "Yes" if prefs.first_run else "No")
            table.add_row("Schema Version", prefs.version)
            table.add_row("Last Updated", prefs.last_updated.strftime("%Y-%m-%d %H:%M:%S UTC"))

            console.print(table)
            console.print()

            # Preferred setup types
            if prefs.preferred_setup_types:
                console.print("[bold cyan]Preferred Setup Types[/bold cyan]")
                for i, setup_type in enumerate(prefs.preferred_setup_types, 1):
                    console.print(f"  {i}. {setup_type}")
                console.print()

            # Setup history
            if prefs.setup_history:
                history_table = Table(
                    title="Recent Setup History", show_header=True, header_style="bold cyan"
                )
                history_table.add_column("Date", style="cyan", width=20)
                history_table.add_column("Setup Type", style="magenta", width=20)
                history_table.add_column("Project", style="yellow", width=25)
                history_table.add_column("Status", style="green", width=10)
                history_table.add_column("Duration", style="blue", width=10)

                # Show last 10 entries
                for entry in prefs.setup_history[-10:]:
                    date_str = entry.timestamp.strftime("%Y-%m-%d %H:%M")
                    status = "[green]Success[/green]" if entry.success else "[red]Failed[/red]"
                    duration = f"{entry.duration_seconds:.1f}s" if entry.duration_seconds else "N/A"
                    project_display = entry.project_name or entry.project_path.split("/")[-1]

                    history_table.add_row(
                        date_str, entry.setup_type_slug, project_display, status, duration
                    )

                console.print(history_table)
                console.print(
                    f"\n[dim]Showing last {min(10, len(prefs.setup_history))} of {len(prefs.setup_history)} total entries[/dim]"
                )
            else:
                console.print("[dim]No setup history yet.[/dim]\n")

            # Show file location
            console.print(f"\n[dim]Preferences file: {pref_manager.preferences_path}[/dim]")

        except Exception as e:
            console.print(f"[red]Error loading preferences: {e}[/red]")
            raise typer.Exit(code=1) from e

    elif reset:
        try:
            # Confirm reset
            import questionary

            confirm = questionary.confirm(
                "Are you sure you want to reset all preferences to defaults?",
                default=False,
            ).ask()

            if not confirm:
                console.print("[yellow]Reset cancelled.[/yellow]")
                return

            pref_manager.reset_to_defaults()
            console.print("[green]Preferences reset to defaults successfully![/green]")
            console.print(
                f"[dim]Backup created at: {pref_manager.preferences_path.with_suffix('.json.backup_*')}[/dim]"
            )

        except Exception as e:
            console.print(f"[red]Error resetting preferences: {e}[/red]")
            raise typer.Exit(code=1) from e

    else:
        console.print("[bold blue]TyPySetup Preferences[/bold blue]\n")
        console.print("Manage your TyPySetup user preferences.\n")
        console.print("Commands:")
        console.print("  [cyan]--show[/cyan]   Display current preferences and setup history")
        console.print("  [cyan]--reset[/cyan]  Reset all preferences to default values\n")
        console.print("Example:")
        console.print("  [dim]typysetup preferences --show[/dim]")
        console.print("  [dim]typysetup preferences --reset[/dim]")


@app.command()
def config(
    project: str = typer.Argument(..., help="Project directory path"),
    show: bool = typer.Option(True, "--show", help="Show project configuration"),
) -> None:
    """Display project configuration from .typysetup/config.json."""
    from pathlib import Path

    from typysetup.core import ProjectConfigLoadError, ProjectConfigManager

    project_path = Path(project).resolve()

    if not project_path.exists():
        console.print(f"[red]Error: Project directory not found: {project_path}[/red]")
        raise typer.Exit(code=1)

    config_manager = ProjectConfigManager(project_path)

    if not config_manager.config_exists():
        console.print(f"[yellow]No TyPySetup configuration found in {project_path}[/yellow]")
        console.print("[dim]Run 'typysetup setup <path>' to create a new project setup.[/dim]")
        raise typer.Exit(code=1)

    try:
        config_manager.display_config(project_path=project_path)
    except ProjectConfigLoadError as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent setups to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
) -> None:
    """Show recent setup history."""
    from typysetup.core import PreferenceManager

    pref_manager = PreferenceManager()

    try:
        prefs = pref_manager.load_preferences()

        if not prefs.setup_history:
            console.print("[yellow]No setup history found.[/yellow]")
            console.print(
                "[dim]Complete a setup with 'typysetup setup <path>' to see history.[/dim]"
            )
            return

        # Display history table
        console.print("\n[bold blue]Setup History[/bold blue]\n")

        history_table = Table(show_header=True, header_style="bold cyan")
        history_table.add_column("Date", style="cyan", width=20)
        history_table.add_column("Status", style="white", width=10)
        history_table.add_column("Setup Type", style="magenta", width=18)
        history_table.add_column("Project", style="yellow", width=30)

        if verbose:
            history_table.add_column("Python", style="green", width=8)
            history_table.add_column("Manager", style="blue", width=10)

        history_table.add_column("Duration", style="dim", width=10)

        # Show last N entries (reversed to show newest first)
        history_list = prefs.setup_history if prefs.setup_history else []
        if limit and limit > 0:
            sliced_history = history_list[-limit:]
        else:
            sliced_history = history_list
        recent_entries = list(reversed(sliced_history))

        for entry in recent_entries:
            date_str = entry.timestamp.strftime("%Y-%m-%d %H:%M")
            status_icon = "[green]✓[/green]" if entry.success else "[red]✗[/red]"
            duration_str = f"{entry.duration_seconds:.1f}s" if entry.duration_seconds else "—"

            # Get project name or extract from path
            if entry.project_name:
                project_display = entry.project_name
            else:
                project_display = entry.project_path.split("/")[-1]
                # Truncate if too long
                if len(project_display) > 28:
                    project_display = project_display[:25] + "..."

            row = [
                date_str,
                status_icon,
                entry.setup_type_slug,
                project_display,
            ]

            if verbose:
                row.append(entry.python_version or "—")
                row.append(entry.package_manager or "—")

            row.append(duration_str)
            history_table.add_row(*row)

        console.print(history_table)

        # Summary statistics
        total = len(prefs.setup_history)
        successful = sum(1 for e in prefs.setup_history if e.success)
        failed = total - successful

        console.print(
            f"\n[dim]Total: {total} setups | "
            f"[green]✓ {successful} successful[/green] | "
            f"[red]✗ {failed} failed[/red][/dim]\n"
        )

        if total > limit:
            console.print(f"[dim]Showing {limit} most recent. Use --limit to see more.[/dim]\n")

    except Exception as e:
        console.print(f"[red]Error loading history: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def help(
    topic: Optional[str] = typer.Argument(None, help="Specific topic to get help for"),
) -> None:
    """
    Show detailed help and usage examples.

    Topics: setup, list, preferences, config, history, workflows
    """
    if not topic:
        # General help
        console.print("[bold blue]TyPySetup - Python Environment Setup CLI[/bold blue]\n")
        console.print(
            "A powerful CLI tool for automating Python environment setup with VSCode integration.\n"
        )

        console.print("[bold cyan]Quick Start:[/bold cyan]")
        console.print(
            "  1. [dim]typysetup list[/dim]                    # See available project types"
        )
        console.print("  2. [dim]typysetup setup /path/to/project[/dim]  # Start interactive setup")
        console.print(
            "  3. [dim]cd /path/to/project && source venv/bin/activate[/dim]  # Activate environment\n"
        )

        console.print("[bold cyan]Common Commands:[/bold cyan]")
        console.print("  [cyan]typysetup setup <path>[/cyan]       Run interactive setup wizard")
        console.print("  [cyan]typysetup list[/cyan]               List available setup types")
        console.print("  [cyan]typysetup preferences --show[/cyan] View your preferences")
        console.print("  [cyan]typysetup config <path>[/cyan]      Show project configuration")
        console.print("  [cyan]typysetup history[/cyan]            View recent setup history\n")

        console.print("[bold cyan]Common Workflows:[/bold cyan]")
        console.print("  • [bold]New FastAPI Project:[/bold]")
        console.print("    [dim]mkdir my-api && typysetup setup my-api[/dim]")
        console.print("    [dim]# Select 'FastAPI' from the menu[/dim]\n")

        console.print("  • [bold]Data Science Project:[/bold]")
        console.print("    [dim]typysetup setup ml-project[/dim]")
        console.print("    [dim]# Select 'Data Science' from the menu[/dim]\n")

        console.print("  • [bold]Check Configuration:[/bold]")
        console.print("    [dim]typysetup config /path/to/project[/dim]\n")

        console.print("[bold cyan]Get Help on Specific Topics:[/bold cyan]")
        console.print("  [dim]typysetup help setup[/dim]       # Detailed setup command help")
        console.print("  [dim]typysetup help workflows[/dim]   # Common workflow examples")
        console.print("  [dim]typysetup help preferences[/dim] # Managing preferences\n")

        console.print("[dim]For command-specific help, use: typysetup <command> --help[/dim]")

    elif topic.lower() == "setup":
        console.print("[bold blue]Setup Command Help[/bold blue]\n")
        console.print("[bold]Usage:[/bold] typysetup setup <path> [options]\n")

        console.print("[bold cyan]What it does:[/bold cyan]")
        console.print("  • Guides you through interactive project type selection")
        console.print("  • Creates Python virtual environment")
        console.print("  • Installs dependencies (uv/pip/poetry)")
        console.print("  • Generates VSCode configuration")
        console.print("  • Saves preferences for future use\n")

        console.print("[bold cyan]Options:[/bold cyan]")
        console.print("  [cyan]--verbose, -v[/cyan]  Enable detailed logging output\n")

        console.print("[bold cyan]Examples:[/bold cyan]")
        console.print("  [dim]# Basic setup[/dim]")
        console.print("  typysetup setup my-project\n")

        console.print("  [dim]# Setup with verbose output[/dim]")
        console.print("  typysetup setup my-project --verbose\n")

        console.print("  [dim]# Setup existing directory[/dim]")
        console.print("  typysetup setup /home/user/existing-project\n")

    elif topic.lower() == "workflows":
        console.print("[bold blue]Common Workflows[/bold blue]\n")

        console.print("[bold cyan]1. Starting a New FastAPI Project[/bold cyan]")
        console.print("  mkdir my-api")
        console.print("  cd my-api")
        console.print("  typysetup setup .")
        console.print("  [dim]# Select 'FastAPI' from the menu[/dim]")
        console.print("  [dim]# Choose package manager (uv recommended)[/dim]")
        console.print("  source venv/bin/activate")
        console.print("  code .  [dim]# Open in VSCode[/dim]\n")

        console.print("[bold cyan]2. Data Science Project with Jupyter[/bold cyan]")
        console.print("  typysetup setup ml-analysis")
        console.print("  [dim]# Select 'Data Science'[/dim]")
        console.print("  cd ml-analysis")
        console.print("  source venv/bin/activate")
        console.print("  jupyter notebook  [dim]# Start Jupyter[/dim]\n")

        console.print("[bold cyan]3. CLI Tool Development[/bold cyan]")
        console.print("  typysetup setup my-cli-tool")
        console.print("  [dim]# Select 'CLI Tool'[/dim]")
        console.print("  cd my-cli-tool")
        console.print("  source venv/bin/activate")
        console.print("  [dim]# Start coding with Typer/Click[/dim]\n")

        console.print("[bold cyan]4. Checking Existing Project[/bold cyan]")
        console.print("  typysetup config /path/to/project")
        console.print("  [dim]# View setup configuration[/dim]\n")

        console.print("[bold cyan]5. Viewing Setup History[/bold cyan]")
        console.print("  typysetup history")
        console.print("  typysetup history --limit 20 --verbose")
        console.print("  [dim]# See all your recent setups[/dim]\n")

    elif topic.lower() == "preferences":
        console.print("[bold blue]Managing Preferences[/bold blue]\n")

        console.print("[bold cyan]View Current Preferences:[/bold cyan]")
        console.print("  typysetup preferences --show\n")

        console.print("[bold cyan]Reset to Defaults:[/bold cyan]")
        console.print("  typysetup preferences --reset\n")

        console.print("[bold cyan]What Gets Saved:[/bold cyan]")
        console.print("  • Preferred package manager (uv/pip/poetry)")
        console.print("  • Preferred Python version")
        console.print("  • Favorite setup types")
        console.print("  • Setup history (last 20 setups)")
        console.print("  • VSCode config merge preferences\n")

        console.print("[bold cyan]Preferences Location:[/bold cyan]")
        console.print("  Linux/macOS: [dim]~/.typysetup/preferences.json[/dim]")
        console.print("  Windows:     [dim]%APPDATA%\\typysetup\\preferences.json[/dim]\n")

    else:
        console.print(f"[yellow]Unknown help topic: {topic}[/yellow]")
        console.print(
            "\n[dim]Available topics: setup, list, preferences, config, history, workflows[/dim]"
        )
        console.print("[dim]Run 'typysetup help' for general help[/dim]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version",
        is_flag=True,
        is_eager=True,
    ),
) -> None:
    """TyPySetup - Interactive Python environment setup for VSCode."""
    if version:
        console.print(f"typysetup version {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
