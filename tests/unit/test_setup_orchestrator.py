"""Tests for SetupOrchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from typysetup.commands.setup_orchestrator import SetupOrchestrator
from typysetup.models import SetupType


@pytest.fixture
def setup_types():
    """Fixture for sample setup types."""
    return [
        SetupType(
            name="FastAPI",
            slug="fastapi",
            description="Modern async web API",
            python_version="3.10+",
            supported_managers=["uv", "pip", "poetry"],
            dependencies={"core": ["fastapi>=0.104"]},
        ),
        SetupType(
            name="Django",
            slug="django",
            description="Full-stack web framework",
            python_version="3.8+",
            supported_managers=["pip", "poetry"],
            dependencies={"core": ["django>=4.2"]},
        ),
    ]


@pytest.fixture
def mock_config_loader(setup_types):
    """Fixture for mocked ConfigLoader."""
    loader = MagicMock()
    loader.load_all_setup_types.return_value = setup_types
    return loader


@pytest.fixture
def orchestrator(mock_config_loader):
    """Fixture for SetupOrchestrator instance."""
    return SetupOrchestrator(config_loader=mock_config_loader)


def test_orchestrator_initialization(mock_config_loader):
    """Test orchestrator initializes with config loader."""
    orch = SetupOrchestrator(config_loader=mock_config_loader)
    assert orch.config_loader is mock_config_loader
    assert orch.setup_type is None
    assert orch.project_path is None
    assert orch.project_config is None


def test_orchestrator_initialization_default_loader():
    """Test orchestrator creates default config loader."""
    orch = SetupOrchestrator()
    assert orch.config_loader is not None


@patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
@patch("typysetup.commands.setup_orchestrator.questionary.select")
@patch("typysetup.commands.setup_orchestrator.questionary.confirm")
def test_select_setup_type_success(
    mock_confirm, mock_select, mock_ensure, orchestrator, setup_types
):
    """Test successfully selecting a setup type."""
    mock_ensure.return_value = "/tmp/test_project"
    mock_select.return_value.ask.return_value = "FastAPI"

    result = orchestrator._select_setup_type()

    assert result is True
    assert orchestrator.setup_type is not None
    assert orchestrator.setup_type.name == "FastAPI"


@patch("typysetup.commands.setup_orchestrator.questionary.select")
def test_select_setup_type_cancelled(mock_select, orchestrator):
    """Test setup type selection when user cancels."""
    mock_select.return_value.ask.return_value = None

    result = orchestrator._select_setup_type()

    assert result is False
    assert orchestrator.setup_type is None


def test_select_setup_type_no_types_available(orchestrator):
    """Test selecting when no setup types are available."""
    orchestrator.config_loader.load_all_setup_types.return_value = []

    result = orchestrator._select_setup_type()

    assert result is False


@patch("typysetup.commands.setup_orchestrator.questionary.confirm")
def test_select_python_version_default(mock_confirm, orchestrator, setup_types):
    """Test selecting default Python version."""
    orchestrator.setup_type = setup_types[0]
    mock_confirm.return_value.ask.return_value = True

    version = orchestrator._select_python_version()

    assert version == "3.10+"


@patch("typysetup.commands.setup_orchestrator.questionary.confirm")
@patch("typysetup.commands.setup_orchestrator.questionary.text")
def test_select_python_version_custom(mock_text, mock_confirm, orchestrator, setup_types):
    """Test selecting custom Python version."""
    orchestrator.setup_type = setup_types[0]
    mock_confirm.return_value.ask.return_value = False
    mock_text.return_value.ask.return_value = "3.9"

    version = orchestrator._select_python_version()

    assert version == "3.9"


@patch("typysetup.commands.setup_orchestrator.questionary.select")
def test_select_package_manager_multiple(mock_select, orchestrator, setup_types):
    """Test selecting from multiple package managers."""
    orchestrator.setup_type = setup_types[0]
    mock_select.return_value.ask.return_value = "poetry"

    manager = orchestrator._select_package_manager()

    assert manager == "poetry"


def test_select_package_manager_single(orchestrator, setup_types):
    """Test when only one package manager is available."""
    from unittest.mock import patch

    orchestrator.setup_type = setup_types[1]  # Django only has pip, poetry

    with patch("questionary.select") as mock_select:
        mock_select.return_value.ask.return_value = "pip"
        manager = orchestrator._select_package_manager()

        # Should return selected manager
        assert manager in orchestrator.setup_type.supported_managers


def test_select_package_manager_none_setup_type(orchestrator):
    """Test package manager selection with no setup type."""
    orchestrator.setup_type = None

    manager = orchestrator._select_package_manager()

    assert manager == "pip"


@patch("typysetup.commands.setup_orchestrator.questionary.confirm")
def test_confirm_setup_success(mock_confirm, orchestrator, setup_types):
    """Test confirming setup configuration."""
    orchestrator.setup_type = setup_types[0]
    orchestrator.project_path = "/tmp/test"
    mock_confirm.return_value.ask.return_value = True

    result = orchestrator._confirm_setup("3.10", "pip")

    assert result is True


@patch("typysetup.commands.setup_orchestrator.questionary.confirm")
def test_confirm_setup_cancelled(mock_confirm, orchestrator, setup_types):
    """Test cancelling setup confirmation."""
    orchestrator.setup_type = setup_types[0]
    orchestrator.project_path = "/tmp/test"
    mock_confirm.return_value.ask.return_value = False

    result = orchestrator._confirm_setup("3.10", "pip")

    assert result is False


def test_display_setup_types(orchestrator, setup_types):
    """Test displaying setup types table."""
    # This should not raise any exceptions
    orchestrator._display_setup_types(setup_types)


@patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
@patch.object(SetupOrchestrator, "_select_setup_type")
@patch.object(SetupOrchestrator, "_select_python_version")
@patch.object(SetupOrchestrator, "_select_package_manager")
@patch.object(SetupOrchestrator, "_confirm_setup")
@patch.object(SetupOrchestrator, "_select_dependency_groups")
@patch.object(SetupOrchestrator, "_select_vscode_extensions")
@patch.object(SetupOrchestrator, "_collect_project_metadata")
@patch.object(SetupOrchestrator, "_confirm_all_selections")
@patch.object(SetupOrchestrator, "_generate_vscode_config")
@patch.object(SetupOrchestrator, "_create_virtual_environment")
@patch.object(SetupOrchestrator, "_generate_pyproject_toml")
@patch.object(SetupOrchestrator, "_install_dependencies")
def test_run_setup_wizard_success(
    mock_install_deps,
    mock_pyproject,
    mock_create_venv,
    mock_vscode_config,
    mock_confirm_all,
    mock_metadata,
    mock_extensions,
    mock_deps,
    mock_confirm,
    mock_manager,
    mock_version,
    mock_type,
    mock_ensure,
    orchestrator,
    setup_types,
):
    """Test running complete setup wizard successfully."""
    from pathlib import Path

    from typysetup.models import DependencySelection, ProjectMetadata

    mock_ensure.return_value = Path("/tmp/test_project")
    mock_type.return_value = True
    mock_version.return_value = "3.10"
    mock_manager.return_value = "pip"
    mock_confirm.return_value = True
    mock_deps.return_value = DependencySelection(
        setup_type_slug="fastapi",
        selected_groups={"core": True},
        all_packages=["fastapi>=0.104"],
    )
    mock_extensions.return_value = []
    mock_metadata.return_value = ProjectMetadata(project_name="test_project")
    mock_confirm_all.return_value = True
    mock_vscode_config.return_value = True
    mock_create_venv.return_value = True
    mock_pyproject.return_value = True
    mock_install_deps.return_value = True
    orchestrator.setup_type = setup_types[0]

    result = orchestrator.run_setup_wizard("/tmp/test_project")

    assert result is not None
    assert result.project_path == "/tmp/test_project"
    assert result.setup_type_slug == "fastapi"
    assert result.python_version == "3.10"
    assert result.package_manager == "pip"


@patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
@patch.object(SetupOrchestrator, "_select_setup_type")
def test_run_setup_wizard_type_selection_cancelled(mock_type, mock_ensure, orchestrator):
    """Test setup wizard when type selection is cancelled."""
    mock_ensure.return_value = "/tmp/test_project"
    mock_type.return_value = False

    result = orchestrator.run_setup_wizard("/tmp/test_project")

    assert result is None


@patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
def test_run_setup_wizard_keyboard_interrupt(mock_ensure, orchestrator):
    """Test setup wizard handling keyboard interrupt."""
    mock_ensure.side_effect = KeyboardInterrupt()

    result = orchestrator.run_setup_wizard("/tmp/test_project")

    assert result is None


@patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
def test_run_setup_wizard_exception(mock_ensure, orchestrator):
    """Test setup wizard error handling."""
    mock_ensure.side_effect = ValueError("Invalid path")

    result = orchestrator.run_setup_wizard("/tmp/test_project")

    assert result is None
