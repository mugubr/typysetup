"""Main Typer application entry point."""

import logging
from typing import Optional

import typer
from rich.console import Console

from typysetup import __version__
from typysetup.commands.config_cmd import ConfigCommand
from typysetup.commands.help_cmd import HelpCommand
from typysetup.commands.history_cmd import HistoryCommand
from typysetup.commands.list_cmd import ListCommand
from typysetup.commands.preferences_cmd import PreferencesCommand
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

# Initialize shared dependencies
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


@app.command("list")
def list_types() -> None:
    """List all available setup type templates."""
    cmd = ListCommand(config_loader)
    cmd.execute()


@app.command()
def preferences(
    show: bool = typer.Option(False, "--show", help="Show current preferences"),
    reset: bool = typer.Option(False, "--reset", help="Reset to defaults"),
) -> None:
    """Manage user preferences."""
    cmd = PreferencesCommand()
    cmd.execute(show, reset)


@app.command()
def config(
    project: str = typer.Argument(..., help="Project directory path"),
    show: bool = typer.Option(True, "--show", help="Show project configuration"),
) -> None:
    """Display project configuration from .typysetup/config.json."""
    cmd = ConfigCommand()
    cmd.execute(project)


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent setups to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
) -> None:
    """Show recent setup history."""
    cmd = HistoryCommand()
    cmd.execute(limit, verbose)


@app.command("help")
def help_topic(
    topic: Optional[str] = typer.Argument(None, help="Specific topic to get help for"),
) -> None:
    """
    Show detailed help and usage examples.

    Topics: setup, list, preferences, config, history, workflows
    """
    cmd = HelpCommand()
    cmd.execute(topic)


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
