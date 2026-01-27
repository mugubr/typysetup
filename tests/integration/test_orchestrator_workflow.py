"""Integration tests for orchestrator workflow and dependency selection features."""

from pathlib import Path
from unittest.mock import patch

import pytest

from typysetup.commands.setup_orchestrator import SetupOrchestrator
from typysetup.core import ConfigLoader
from typysetup.models import DependencySelection, ProjectMetadata


@pytest.fixture
def config_loader():
    """Create a ConfigLoader for testing."""
    return ConfigLoader()


@pytest.fixture
def orchestrator(config_loader):
    """Create a SetupOrchestrator for testing."""
    return SetupOrchestrator(config_loader=config_loader)


class TestPhase4Orchestrator:
    """Tests for Phase 4 features in SetupOrchestrator."""

    def test_orchestrator_has_prompt_manager(self, orchestrator):
        """Test that orchestrator has PromptManager."""
        assert orchestrator.prompt_manager is not None

    def test_orchestrator_initializes_phase4_attributes(self, orchestrator):
        """Test that orchestrator initializes Phase 4 attributes."""
        assert orchestrator.dependency_selection is None
        assert orchestrator.selected_extensions is None
        assert orchestrator.project_metadata is None

    @patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
    @patch.object(SetupOrchestrator, "_select_setup_type", return_value=True)
    @patch.object(SetupOrchestrator, "_select_python_version", return_value="3.10")
    @patch.object(SetupOrchestrator, "_select_package_manager", return_value="pip")
    @patch.object(SetupOrchestrator, "_confirm_setup", return_value=True)
    @patch.object(SetupOrchestrator, "_select_dependency_groups")
    @patch.object(SetupOrchestrator, "_select_vscode_extensions")
    @patch.object(SetupOrchestrator, "_collect_project_metadata")
    @patch.object(SetupOrchestrator, "_confirm_all_selections", return_value=True)
    @patch.object(SetupOrchestrator, "_generate_vscode_config", return_value=True)
    @patch.object(SetupOrchestrator, "_create_virtual_environment", return_value=True)
    @patch.object(SetupOrchestrator, "_generate_pyproject_toml", return_value=True)
    @patch.object(SetupOrchestrator, "_install_dependencies", return_value=True)
    def test_run_setup_wizard_calls_all_phase4_methods(
        self,
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
    ):
        """Test that run_setup_wizard calls all Phase 4 methods."""
        # Setup
        mock_ensure.return_value = Path("/tmp/test")
        mock_deps.return_value = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True},
            all_packages=["fastapi>=0.104"],
        )
        mock_extensions.return_value = ["ms-python.python"]
        mock_metadata.return_value = ProjectMetadata(project_name="test_project")
        orchestrator.setup_type = orchestrator.config_loader.load_setup_type("fastapi")

        # Execute
        result = orchestrator.run_setup_wizard("/tmp/test")

        # Verify all methods called
        mock_deps.assert_called_once()
        mock_extensions.assert_called_once()
        mock_metadata.assert_called_once()
        mock_confirm_all.assert_called_once()
        assert result is not None

    @patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
    @patch.object(SetupOrchestrator, "_select_setup_type", return_value=True)
    @patch.object(SetupOrchestrator, "_select_python_version", return_value="3.10")
    @patch.object(SetupOrchestrator, "_select_package_manager", return_value="pip")
    @patch.object(SetupOrchestrator, "_confirm_setup", return_value=True)
    @patch.object(SetupOrchestrator, "_select_dependency_groups", return_value=None)
    def test_run_setup_wizard_handles_dependency_selection_cancel(
        self,
        mock_deps,
        mock_confirm,
        mock_manager,
        mock_version,
        mock_type,
        mock_ensure,
        orchestrator,
    ):
        """Test that wizard cancels if dependency selection returns None."""
        mock_ensure.return_value = Path("/tmp/test")
        orchestrator.setup_type = orchestrator.config_loader.load_setup_type("fastapi")

        result = orchestrator.run_setup_wizard("/tmp/test")

        assert result is None

    @patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
    @patch.object(SetupOrchestrator, "_select_setup_type", return_value=True)
    @patch.object(SetupOrchestrator, "_select_python_version", return_value="3.10")
    @patch.object(SetupOrchestrator, "_select_package_manager", return_value="pip")
    @patch.object(SetupOrchestrator, "_confirm_setup", return_value=True)
    @patch.object(SetupOrchestrator, "_select_dependency_groups")
    @patch.object(SetupOrchestrator, "_select_vscode_extensions", return_value=None)
    @patch.object(SetupOrchestrator, "_collect_project_metadata")
    def test_run_setup_wizard_handles_extension_selection_cancel(
        self,
        mock_metadata,
        mock_extensions,
        mock_deps,
        mock_confirm,
        mock_manager,
        mock_version,
        mock_type,
        mock_ensure,
        orchestrator,
    ):
        """Test that wizard continues if extension selection returns None (empty list)."""
        mock_ensure.return_value = Path("/tmp/test")
        mock_deps.return_value = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True},
            all_packages=["fastapi>=0.104"],
        )
        mock_extensions.return_value = None
        mock_metadata.return_value = ProjectMetadata(project_name="test_project")
        orchestrator.setup_type = orchestrator.config_loader.load_setup_type("fastapi")

        result = orchestrator.run_setup_wizard("/tmp/test")

        # Extensions are optional, so wizard should continue
        assert orchestrator.selected_extensions == []

    @patch("typysetup.commands.setup_orchestrator.ensure_project_directory")
    @patch.object(SetupOrchestrator, "_select_setup_type", return_value=True)
    @patch.object(SetupOrchestrator, "_select_python_version", return_value="3.10")
    @patch.object(SetupOrchestrator, "_select_package_manager", return_value="pip")
    @patch.object(SetupOrchestrator, "_confirm_setup", return_value=True)
    @patch.object(SetupOrchestrator, "_select_dependency_groups")
    @patch.object(SetupOrchestrator, "_select_vscode_extensions")
    @patch.object(SetupOrchestrator, "_collect_project_metadata", return_value=None)
    def test_run_setup_wizard_handles_metadata_cancel(
        self,
        mock_metadata,
        mock_extensions,
        mock_deps,
        mock_confirm,
        mock_manager,
        mock_version,
        mock_type,
        mock_ensure,
        orchestrator,
    ):
        """Test that wizard cancels if metadata collection returns None."""
        mock_ensure.return_value = Path("/tmp/test")
        mock_deps.return_value = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True},
            all_packages=["fastapi>=0.104"],
        )
        mock_extensions.return_value = ["ms-python.python"]
        orchestrator.setup_type = orchestrator.config_loader.load_setup_type("fastapi")

        result = orchestrator.run_setup_wizard("/tmp/test")

        assert result is None

    def test_project_configuration_stores_phase4_data(self, orchestrator, config_loader):
        """Test that ProjectConfiguration stores all Phase 4 data."""
        # This would be a full integration test with actual prompts
        # For now, just verify the fields exist
        from typysetup.models import ProjectConfiguration

        deps = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True},
            all_packages=["fastapi>=0.104"],
        )
        metadata = ProjectMetadata(project_name="test_project")
        extensions = ["ms-python.python"]

        config = ProjectConfiguration(
            project_path="/tmp/test",
            setup_type_slug="fastapi",
            python_version="3.10",
            python_executable="/tmp/test/venv/bin/python",
            package_manager="pip",
            venv_path="/tmp/test/venv",
            dependency_selections=deps.model_dump(),
            selected_extensions=extensions,
            project_metadata=metadata.model_dump(),
        )

        assert config.dependency_selections is not None
        assert config.selected_extensions == extensions
        assert config.project_metadata is not None
        assert config.project_metadata["project_name"] == "test_project"

    def test_dependency_selection_in_configuration(self):
        """Test that DependencySelection data is properly stored."""
        from typysetup.models import ProjectConfiguration

        deps = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True, "optional": False},
            all_packages=["fastapi>=0.104", "pytest>=7.0"],
        )

        config = ProjectConfiguration(
            project_path="/tmp/test",
            setup_type_slug="fastapi",
            python_version="3.10",
            python_executable="/tmp/test/venv/bin/python",
            package_manager="pip",
            venv_path="/tmp/test/venv",
            dependency_selections=deps.model_dump(),
        )

        # Verify data is stored
        assert config.dependency_selections["setup_type_slug"] == "fastapi"
        assert config.dependency_selections["selected_groups"]["core"] is True
        assert len(config.dependency_selections["all_packages"]) == 2

    def test_project_metadata_in_configuration(self):
        """Test that ProjectMetadata is properly stored."""
        from typysetup.models import ProjectConfiguration

        metadata = ProjectMetadata(
            project_name="my_project",
            project_description="A test project",
            author_name="Jane Doe",
            author_email="jane@example.com",
        )

        config = ProjectConfiguration(
            project_path="/tmp/test",
            setup_type_slug="fastapi",
            python_version="3.10",
            python_executable="/tmp/test/venv/bin/python",
            package_manager="pip",
            venv_path="/tmp/test/venv",
            project_metadata=metadata.model_dump(),
        )

        # Verify data is stored
        assert config.project_metadata["project_name"] == "my_project"
        assert config.project_metadata["author_name"] == "Jane Doe"
        assert config.project_metadata["author_email"] == "jane@example.com"

    @patch("typysetup.commands.setup_orchestrator.SetupOrchestrator._select_setup_type")
    @patch("typysetup.commands.setup_orchestrator.SetupOrchestrator._select_python_version")
    @patch("typysetup.commands.setup_orchestrator.SetupOrchestrator._select_package_manager")
    @patch("typysetup.commands.setup_orchestrator.SetupOrchestrator._confirm_setup")
    def test_confirm_all_selections_displays_summary(
        self, mock_confirm, mock_manager, mock_version, mock_type, orchestrator, config_loader
    ):
        """Test that _confirm_all_selections displays all selections."""
        orchestrator.setup_type = config_loader.load_setup_type("fastapi")
        orchestrator.project_path = "/tmp/test"
        orchestrator.dependency_selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True},
            all_packages=["fastapi>=0.104", "pytest>=7.0"],
        )
        orchestrator.selected_extensions = ["ms-python.python"]
        orchestrator.project_metadata = ProjectMetadata(project_name="test_project")

        with patch("questionary.confirm") as mock_questionary:
            mock_questionary.return_value.ask.return_value = True
            result = orchestrator._confirm_all_selections("3.10", "pip")

        assert result is True
        assert mock_questionary.called
