"""Tests for ProjectConfigManager."""

import json

import pytest

from typysetup.core.project_config_manager import (
    ProjectConfigLoadError,
    ProjectConfigManager,
    ProjectConfigSaveError,
)
from typysetup.models.project_config import ProjectConfiguration


class TestProjectConfigManager:
    """Test suite for ProjectConfigManager."""

    def test_init_with_project_path(self, tmp_path):
        """Test initialization with project path."""
        manager = ProjectConfigManager(tmp_path)
        assert manager.project_path == tmp_path
        assert manager._config_path == tmp_path / ".typysetup" / "config.json"

    def test_init_without_project_path(self):
        """Test initialization without project path."""
        manager = ProjectConfigManager()
        assert manager.project_path is None
        assert manager._config_path is None

    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration."""
        manager = ProjectConfigManager(tmp_path)

        # Create config
        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/path/to/python",
            package_manager="uv",
            venv_path="/path/to/venv",
            status="success",
        )

        # Save config
        manager.save_config(config)

        # Verify file exists
        config_file = tmp_path / ".typysetup" / "config.json"
        assert config_file.exists()

        # Load config
        loaded_config = manager.load_config()
        assert loaded_config is not None
        assert loaded_config.project_path == str(tmp_path)
        assert loaded_config.setup_type_slug == "fastapi"
        assert loaded_config.python_version == "3.11"
        assert loaded_config.package_manager == "uv"
        assert loaded_config.status == "success"

    def test_load_nonexistent_config(self, tmp_path):
        """Test loading nonexistent configuration."""
        manager = ProjectConfigManager(tmp_path)
        config = manager.load_config()
        assert config is None

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates .typysetup directory."""
        manager = ProjectConfigManager(tmp_path)

        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="flask",
            python_version="3.10",
            python_executable="/usr/bin/python3",
            package_manager="pip",
            venv_path="/path/to/venv",
        )

        manager.save_config(config)

        pysetup_dir = tmp_path / ".typysetup"
        assert pysetup_dir.exists()
        assert pysetup_dir.is_dir()

    def test_save_creates_backup(self, tmp_path):
        """Test that save creates backup of existing file."""
        manager = ProjectConfigManager(tmp_path)

        # Create first config
        config1 = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="django",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="pip",
            venv_path="/path/to/venv",
        )
        manager.save_config(config1)

        # Save second config (should create backup)
        config2 = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="flask",
            python_version="3.10",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
        )
        manager.save_config(config2)

        # Verify backup exists
        backup_file = tmp_path / ".typysetup" / "config.json.backup"
        assert backup_file.exists()

        # Verify main file has new data
        loaded = manager.load_config()
        assert loaded.setup_type_slug == "flask"

    def test_save_with_metadata(self, tmp_path):
        """Test saving configuration with project metadata."""
        manager = ProjectConfigManager(tmp_path)

        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
            project_metadata={
                "project_name": "my-project",
                "description": "Test project",
                "author_name": "Test Author",
                "author_email": "test@example.com",
            },
        )

        manager.save_config(config)
        loaded = manager.load_config()

        assert loaded.project_metadata is not None
        assert loaded.project_metadata["project_name"] == "my-project"
        assert loaded.project_metadata["author_name"] == "Test Author"

    def test_save_with_dependencies(self, tmp_path):
        """Test saving configuration with dependency selections."""
        manager = ProjectConfigManager(tmp_path)

        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
            dependency_selections={
                "core_dependencies": ["fastapi", "uvicorn"],
                "dev_dependencies": ["pytest", "black"],
            },
        )

        manager.save_config(config)
        loaded = manager.load_config()

        assert loaded.dependency_selections is not None
        assert "core_dependencies" in loaded.dependency_selections
        assert "fastapi" in loaded.dependency_selections["core_dependencies"]

    def test_load_invalid_json(self, tmp_path):
        """Test loading configuration with invalid JSON."""
        manager = ProjectConfigManager(tmp_path)

        # Create invalid JSON file
        config_dir = tmp_path / ".typysetup"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(ProjectConfigLoadError, match="Invalid JSON"):
            manager.load_config()

    def test_load_invalid_schema(self, tmp_path):
        """Test loading configuration with invalid schema."""
        manager = ProjectConfigManager(tmp_path)

        # Create file with invalid schema
        config_dir = tmp_path / ".typysetup"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"

        invalid_data = {
            "project_path": str(tmp_path),
            "setup_type_slug": "fastapi",
            "python_version": "3.11",
            # Missing required fields
        }

        with open(config_file, "w") as f:
            json.dump(invalid_data, f)

        with pytest.raises(ProjectConfigLoadError, match="validation failed"):
            manager.load_config()

    def test_config_exists(self, tmp_path):
        """Test config_exists method."""
        manager = ProjectConfigManager(tmp_path)

        assert not manager.config_exists()

        # Create config
        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
        )
        manager.save_config(config)

        assert manager.config_exists()

    def test_save_without_project_path(self):
        """Test saving without project path raises error."""
        manager = ProjectConfigManager()

        config = ProjectConfiguration(
            project_path="",  # Empty path
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
        )

        with pytest.raises(ProjectConfigSaveError, match="No project path"):
            manager.save_config(config)

    def test_load_with_different_project_path(self, tmp_path):
        """Test loading config from different path than initialized."""
        manager = ProjectConfigManager()

        # Create config in tmp_path
        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="flask",
            python_version="3.10",
            python_executable="/usr/bin/python3",
            package_manager="pip",
            venv_path="/path/to/venv",
        )

        # Save using explicit path
        manager.save_config(config, tmp_path)

        # Load using explicit path
        loaded = manager.load_config(tmp_path)
        assert loaded is not None
        assert loaded.setup_type_slug == "flask"

    def test_display_config(self, tmp_path, capsys):
        """Test display_config method."""
        manager = ProjectConfigManager(tmp_path)

        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
            status="success",
            project_metadata={
                "project_name": "test-project",
                "description": "A test project",
            },
        )

        # Display should not raise
        manager.display_config(config)

    def test_display_nonexistent_config(self, tmp_path, capsys):
        """Test displaying nonexistent configuration."""
        manager = ProjectConfigManager(tmp_path)

        # Should print warning message
        manager.display_config(project_path=tmp_path)
        captured = capsys.readouterr()
        assert "No configuration found" in captured.out

    def test_atomic_write_on_error(self, tmp_path):
        """Test that atomic write cleans up temp file on error."""
        manager = ProjectConfigManager(tmp_path)

        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
        )

        # Save normally first
        manager.save_config(config)

        # Verify no temp file exists
        temp_file = tmp_path / ".typysetup" / "config.json.tmp"
        assert not temp_file.exists()

    def test_count_dependencies_by_group(self, tmp_path):
        """Test dependency counting by group."""
        manager = ProjectConfigManager(tmp_path)

        config = ProjectConfiguration(
            project_path=str(tmp_path),
            setup_type_slug="fastapi",
            python_version="3.11",
            python_executable="/usr/bin/python3",
            package_manager="uv",
            venv_path="/path/to/venv",
        )

        # Add dependencies
        config.add_dependency("fastapi", "0.100.0", "uv", "core")
        config.add_dependency("uvicorn", "0.20.0", "uv", "core")
        config.add_dependency("pytest", "7.0.0", "uv", "dev")

        counts = manager._count_dependencies_by_group(config)
        assert counts["core"] == 2
        assert counts["dev"] == 1

    def test_format_status(self, tmp_path):
        """Test status formatting with colors."""
        manager = ProjectConfigManager(tmp_path)

        assert "Success" in manager._format_status("success")
        assert "Failed" in manager._format_status("failed")
        assert "Partial" in manager._format_status("partial")
        assert "Running" in manager._format_status("running")
        assert "Pending" in manager._format_status("pending")
