"""Integration tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from typysetup import __version__
from typysetup.main import app
from typysetup.models import SetupType


@pytest.fixture
def cli_runner():
    """Fixture for Typer CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_setup_types():
    """Fixture for sample setup types."""
    return [
        SetupType(
            name="FastAPI",
            slug="fastapi",
            description="Modern async web API",
            python_version="3.10+",
            supported_managers=["uv", "pip", "poetry"],
            dependencies={"core": ["fastapi>=0.104"]},
            tags=["web", "async"],
        ),
        SetupType(
            name="Django",
            slug="django",
            description="Full-stack web framework",
            python_version="3.8+",
            supported_managers=["pip", "poetry"],
            dependencies={"core": ["django>=4.2"]},
            tags=["web"],
        ),
    ]


def test_list_command(cli_runner, sample_setup_types):
    """Test list command displays setup types."""
    with patch("typysetup.main.config_loader.load_all_setup_types") as mock_load:
        mock_load.return_value = sample_setup_types

        result = cli_runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "Available Setup Types" in result.stdout
        assert "FastAPI" in result.stdout
        assert "Django" in result.stdout
        assert "Modern async" in result.stdout or "async web" in result.stdout


def test_list_command_no_types(cli_runner):
    """Test list command when no setup types available."""
    with patch("typysetup.main.config_loader.load_all_setup_types") as mock_load:
        mock_load.return_value = []

        result = cli_runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No setup types found" in result.stdout


def test_list_command_error_handling(cli_runner):
    """Test list command error handling."""
    with patch("typysetup.main.config_loader.load_all_setup_types") as mock_load:
        mock_load.side_effect = Exception("Config load error")

        result = cli_runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "Error loading setup types" in result.stdout


@patch("typysetup.main.SetupOrchestrator")
def test_setup_command_success(mock_orchestrator_class, cli_runner, tmp_path):
    """Test setup command with successful configuration."""
    mock_orchestrator = MagicMock()
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_config = MagicMock()
    mock_config.project_path = str(tmp_path)
    mock_orchestrator.run_setup_wizard.return_value = mock_config

    result = cli_runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 0
    assert "Setup configuration created successfully" in result.stdout


@patch("typysetup.main.SetupOrchestrator")
def test_setup_command_cancelled(mock_orchestrator_class, cli_runner, tmp_path):
    """Test setup command when wizard is cancelled."""
    mock_orchestrator = MagicMock()
    mock_orchestrator_class.return_value = mock_orchestrator
    mock_orchestrator.run_setup_wizard.return_value = None

    result = cli_runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 1


@patch("typysetup.main.SetupOrchestrator")
def test_setup_command_verbose(mock_orchestrator_class, cli_runner, tmp_path):
    """Test setup command with verbose flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator_class.return_value = mock_orchestrator

    mock_config = MagicMock()
    mock_config.project_path = str(tmp_path)
    mock_orchestrator.run_setup_wizard.return_value = mock_config

    result = cli_runner.invoke(app, ["setup", str(tmp_path), "--verbose"])

    assert result.exit_code == 0


def test_version_flag(cli_runner):
    """Test --version flag."""
    result = cli_runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"typysetup version {__version__}" in result.stdout


def test_help_flag(cli_runner):
    """Test --help flag."""
    result = cli_runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Interactive Python environment setup CLI" in result.stdout


def test_no_args_shows_help(cli_runner):
    """Test that no arguments shows usage information."""
    result = cli_runner.invoke(app, [])

    # Typer returns exit code 2 for missing command, which shows usage
    assert result.exit_code == 2
    assert "Usage:" in result.stdout


def test_setup_command_help(cli_runner):
    """Test setup command help."""
    result = cli_runner.invoke(app, ["setup", "--help"])

    assert result.exit_code == 0
    assert "Interactive setup wizard" in result.stdout


def test_list_command_help(cli_runner):
    """Test list command help."""
    result = cli_runner.invoke(app, ["list", "--help"])

    assert result.exit_code == 0
    assert "List all available" in result.stdout
