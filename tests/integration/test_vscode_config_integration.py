"""Integration tests for VSCode config generation with SetupOrchestrator."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from typysetup.commands.setup_orchestrator import SetupOrchestrator
from typysetup.core import ConfigLoader


@pytest.fixture
def config_loader():
    """Create a ConfigLoader for testing."""
    return ConfigLoader()


@pytest.fixture
def orchestrator(config_loader):
    """Create a SetupOrchestrator for testing."""
    return SetupOrchestrator(config_loader=config_loader)


class TestVSCodeConfigIntegration:
    """Integration tests for VSCode config generation."""

    def test_generate_vscode_config_phase5(self, orchestrator, config_loader):
        """Test Phase 5: Generate VSCode configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Load setup type
            setup_type = config_loader.load_setup_type("fastapi")
            assert setup_type is not None

            # Create project config
            from typysetup.models import ProjectConfiguration

            project_config = ProjectConfiguration(
                project_path=str(project_path),
                setup_type_slug="fastapi",
                python_version="3.10.5",
                python_executable=str(project_path / "venv" / "bin" / "python"),
                package_manager="uv",
                venv_path=str(project_path / "venv"),
                selected_extensions=["ms-python.vscode-pylance"],
            )

            # Generate VSCode config
            result = orchestrator._generate_vscode_config()
            orchestrator.setup_type = setup_type
            orchestrator.project_path = project_path
            orchestrator.project_config = project_config

            result = orchestrator._generate_vscode_config()

            # Verify files were created
            vscode_dir = project_path / ".vscode"
            assert vscode_dir.exists()
            assert (vscode_dir / "settings.json").exists()
            assert (vscode_dir / "extensions.json").exists()
            assert (vscode_dir / "launch.json").exists()

    def test_vscode_config_contains_setup_settings(self, orchestrator, config_loader):
        """Test that VSCode config includes setup type settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            setup_type = config_loader.load_setup_type("fastapi")
            from typysetup.models import ProjectConfiguration

            project_config = ProjectConfiguration(
                project_path=str(project_path),
                setup_type_slug="fastapi",
                python_version="3.10.5",
                python_executable=str(project_path / "venv" / "bin" / "python"),
                package_manager="uv",
                venv_path=str(project_path / "venv"),
            )

            orchestrator.setup_type = setup_type
            orchestrator.project_path = project_path
            orchestrator.project_config = project_config

            orchestrator._generate_vscode_config()

            # Verify settings include setup type values
            settings_file = project_path / ".vscode" / "settings.json"
            settings = json.loads(settings_file.read_text())
            assert "python.linting.enabled" in settings

    def test_vscode_config_includes_selected_extensions(self, orchestrator, config_loader):
        """Test that VSCode config includes selected extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            setup_type = config_loader.load_setup_type("fastapi")
            from typysetup.models import ProjectConfiguration

            project_config = ProjectConfiguration(
                project_path=str(project_path),
                setup_type_slug="fastapi",
                python_version="3.10.5",
                python_executable=str(project_path / "venv" / "bin" / "python"),
                package_manager="uv",
                venv_path=str(project_path / "venv"),
                selected_extensions=["charliermarsh.ruff", "ms-python.vscode-pylance"],
            )

            orchestrator.setup_type = setup_type
            orchestrator.project_path = project_path
            orchestrator.project_config = project_config

            orchestrator._generate_vscode_config()

            # Verify extensions include both setup + selected
            ext_file = project_path / ".vscode" / "extensions.json"
            extensions = json.loads(ext_file.read_text())
            recs = extensions["recommendations"]
            assert "charliermarsh.ruff" in recs
            assert "ms-python.vscode-pylance" in recs

    def test_vscode_config_merges_with_existing(self, orchestrator, config_loader):
        """Test that VSCode config merges with existing settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            vscode_dir = project_path / ".vscode"
            vscode_dir.mkdir()

            # Create existing settings with settings NOT in fastapi setup type
            existing_settings = {
                "editor.wordWrap": "on",  # Not in fastapi setup type
                "[javascript]": {"editor.defaultFormatter": "esbenp.prettier-vscode"},
            }
            (vscode_dir / "settings.json").write_text(json.dumps(existing_settings))

            setup_type = config_loader.load_setup_type("fastapi")
            from typysetup.models import ProjectConfiguration

            project_config = ProjectConfiguration(
                project_path=str(project_path),
                setup_type_slug="fastapi",
                python_version="3.10.5",
                python_executable=str(project_path / "venv" / "bin" / "python"),
                package_manager="uv",
                venv_path=str(project_path / "venv"),
            )

            orchestrator.setup_type = setup_type
            orchestrator.project_path = project_path
            orchestrator.project_config = project_config

            orchestrator._generate_vscode_config()

            # Verify merge
            settings = json.loads((vscode_dir / "settings.json").read_text())
            assert settings["editor.wordWrap"] == "on"  # Existing preserved (not in setup)
            assert settings["editor.formatOnSave"] is True  # New from setup (takes precedence)
            assert settings["python.linting.enabled"] is True  # New from setup

    def test_vscode_config_creates_backup(self, orchestrator, config_loader):
        """Test that existing config files are backed up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            vscode_dir = project_path / ".vscode"
            vscode_dir.mkdir()

            # Create existing settings
            existing_settings = {"existing": True}
            settings_file = vscode_dir / "settings.json"
            settings_file.write_text(json.dumps(existing_settings))

            setup_type = config_loader.load_setup_type("fastapi")
            from typysetup.models import ProjectConfiguration

            project_config = ProjectConfiguration(
                project_path=str(project_path),
                setup_type_slug="fastapi",
                python_version="3.10.5",
                python_executable=str(project_path / "venv" / "bin" / "python"),
                package_manager="uv",
                venv_path=str(project_path / "venv"),
            )

            orchestrator.setup_type = setup_type
            orchestrator.project_path = project_path
            orchestrator.project_config = project_config

            orchestrator._generate_vscode_config()

            # Verify backup exists
            backups = list(vscode_dir.glob("settings.json.backup.*"))
            assert len(backups) > 0

    def test_vscode_launch_config_generation(self, orchestrator, config_loader):
        """Test that launch.json is properly generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            setup_type = config_loader.load_setup_type("fastapi")
            from typysetup.models import ProjectConfiguration

            project_config = ProjectConfiguration(
                project_path=str(project_path),
                setup_type_slug="fastapi",
                python_version="3.10.5",
                python_executable=str(project_path / "venv" / "bin" / "python"),
                package_manager="uv",
                venv_path=str(project_path / "venv"),
            )

            orchestrator.setup_type = setup_type
            orchestrator.project_path = project_path
            orchestrator.project_config = project_config

            orchestrator._generate_vscode_config()

            # Verify launch.json structure
            launch_file = project_path / ".vscode" / "launch.json"
            launch = json.loads(launch_file.read_text())
            assert launch["version"] == "0.2.0"
            assert "configurations" in launch
            assert isinstance(launch["configurations"], list)

    def test_generate_vscode_config_error_handling(self, orchestrator):
        """Test error handling in VSCode config generation."""
        # Set up incomplete state
        orchestrator.setup_type = None
        orchestrator.project_path = Path("/tmp/test")
        orchestrator.project_config = None

        # Should return False without crashing
        result = orchestrator._generate_vscode_config()
        assert result is False

    def test_full_setup_wizard_with_vscode_phase(self, orchestrator):
        """Test that Phase 5 runs in complete setup wizard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(orchestrator, "_select_setup_type", return_value=True):
                with patch.object(orchestrator, "_select_python_version", return_value="3.10"):
                    with patch.object(orchestrator, "_select_package_manager", return_value="uv"):
                        with patch.object(orchestrator, "_confirm_setup", return_value=True):
                            with patch.object(
                                orchestrator, "_select_dependency_groups"
                            ) as mock_deps:
                                with patch.object(
                                    orchestrator, "_select_vscode_extensions"
                                ) as mock_ext:
                                    with patch.object(
                                        orchestrator, "_collect_project_metadata"
                                    ) as mock_meta:
                                        with patch.object(
                                            orchestrator,
                                            "_confirm_all_selections",
                                            return_value=True,
                                        ):
                                            from typysetup.models import (
                                                DependencySelection,
                                                ProjectMetadata,
                                            )

                                            # Setup mocks
                                            orchestrator.setup_type = (
                                                orchestrator.config_loader.load_setup_type(
                                                    "fastapi"
                                                )
                                            )
                                            mock_deps.return_value = DependencySelection(
                                                setup_type_slug="fastapi",
                                                selected_groups={"core": True},
                                                all_packages=["fastapi>=0.104"],
                                            )
                                            mock_ext.return_value = []
                                            mock_meta.return_value = ProjectMetadata(
                                                project_name="test_project"
                                            )

                                            result = orchestrator.run_setup_wizard(tmpdir)

                                            # Verify Phase 5 ran
                                            vscode_dir = Path(tmpdir) / ".vscode"
                                            assert vscode_dir.exists()
                                            assert (vscode_dir / "settings.json").exists()
