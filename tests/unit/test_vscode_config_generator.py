"""Unit tests for VSCode config generator and backup manager."""

import json
import tempfile
from pathlib import Path

import pytest

from typysetup.core.file_backup_manager import FileBackupManager
from typysetup.core.vscode_config_generator import VSCodeConfigGenerator
from typysetup.models import ProjectConfiguration
from typysetup.models.builder import SetupTypeBuilder


@pytest.fixture
def temp_vscode_dir():
    """Create a temporary .vscode directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vscode_dir = Path(tmpdir) / ".vscode"
        vscode_dir.mkdir()
        yield vscode_dir


@pytest.fixture
def sample_setup_type():
    """Create a sample setup type with VSCode config."""
    return (
        SetupTypeBuilder()
        .with_name("FastAPI")
        .with_slug("fastapi")
        .with_description("Web API with FastAPI framework")
        .with_python_version("3.10+")
        .with_supported_managers(["uv"])
        .add_dependency("core", "fastapi>=0.104.0")
        .with_vscode_settings(
            {
                "python.linting.enabled": True,
                "python.formatting.provider": "black",
            }
        )
        .add_vscode_extension("ms-python.python")
        .with_vscode_launch_config(
            {
                "name": "Python: FastAPI",
                "type": "python",
                "request": "launch",
                "module": "uvicorn",
                "args": ["main:app", "--reload"],
            }
        )
        .build()
    )


@pytest.fixture
def sample_project_config(temp_vscode_dir):
    """Create a sample project configuration."""
    return ProjectConfiguration(
        project_path=str(temp_vscode_dir.parent),
        setup_type_slug="fastapi",
        python_version="3.10.5",
        package_manager="uv",
        selected_extensions=["charliermarsh.ruff"],
    )


class TestFileBackupManager:
    """Tests for FileBackupManager."""

    def test_create_backup(self, temp_vscode_dir):
        """Test creating a backup file."""
        original_file = temp_vscode_dir / "settings.json"
        original_file.write_text('{"test": true}')

        manager = FileBackupManager()
        backup_path = manager.create_backup(original_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert "settings.json.backup" in str(backup_path)

    def test_create_backup_nonexistent(self, temp_vscode_dir):
        """Test creating backup of non-existent file."""
        nonexistent = temp_vscode_dir / "nonexistent.json"
        manager = FileBackupManager()
        result = manager.create_backup(nonexistent)

        assert result is None

    def test_restore_backup(self, temp_vscode_dir):
        """Test restoring from backup."""
        original_file = temp_vscode_dir / "settings.json"
        original_file.write_text('{"original": true}')

        manager = FileBackupManager()
        backup_path = manager.create_backup(original_file)

        # Modify original file
        original_file.write_text('{"modified": true}')

        # Restore
        manager.restore_backup(original_file, backup_path)

        assert original_file.read_text() == '{"original": true}'

    def test_list_backups(self, temp_vscode_dir):
        """Test listing backups."""
        import time

        original_file = temp_vscode_dir / "settings.json"
        original_file.write_text('{"test": true}')

        manager = FileBackupManager()
        backup1 = manager.create_backup(original_file)
        time.sleep(0.1)  # Ensure different timestamps
        backup2 = manager.create_backup(original_file)

        backups = manager.list_backups(original_file)
        assert len(backups) >= 2
        assert backup1 in backups
        assert backup2 in backups

    def test_cleanup_backup(self, temp_vscode_dir):
        """Test deleting a backup."""
        original_file = temp_vscode_dir / "settings.json"
        original_file.write_text('{"test": true}')

        manager = FileBackupManager()
        backup_path = manager.create_backup(original_file)
        assert backup_path.exists()

        manager.cleanup_backup(backup_path)
        assert not backup_path.exists()


class TestVSCodeConfigGenerator:
    """Tests for VSCodeConfigGenerator."""

    def test_load_existing_settings(self, temp_vscode_dir):
        """Test loading existing settings.json."""
        settings_file = temp_vscode_dir / "settings.json"
        test_settings = {"python.linting.enabled": True}
        settings_file.write_text(json.dumps(test_settings))

        generator = VSCodeConfigGenerator()
        result = generator._load_existing_settings(temp_vscode_dir)

        assert result == test_settings

    def test_load_missing_settings(self, temp_vscode_dir):
        """Test loading non-existent settings.json."""
        generator = VSCodeConfigGenerator()
        result = generator._load_existing_settings(temp_vscode_dir)

        assert result is None

    def test_load_existing_extensions(self, temp_vscode_dir):
        """Test loading existing extensions.json."""
        ext_file = temp_vscode_dir / "extensions.json"
        test_extensions = {"recommendations": ["ms-python.python"]}
        ext_file.write_text(json.dumps(test_extensions))

        generator = VSCodeConfigGenerator()
        result = generator._load_existing_extensions(temp_vscode_dir)

        assert result == ["ms-python.python"]

    def test_write_settings_json(self, temp_vscode_dir):
        """Test writing settings.json."""
        test_settings = {
            "python.linting.enabled": True,
            "python.formatting.provider": "black",
        }

        generator = VSCodeConfigGenerator()
        generator._write_settings_json(temp_vscode_dir, test_settings)

        settings_file = temp_vscode_dir / "settings.json"
        assert settings_file.exists()
        written = json.loads(settings_file.read_text())
        assert written == test_settings

    def test_write_extensions_json(self, temp_vscode_dir):
        """Test writing extensions.json."""
        test_extensions = ["ms-python.python", "charliermarsh.ruff"]

        generator = VSCodeConfigGenerator()
        generator._write_extensions_json(temp_vscode_dir, test_extensions)

        ext_file = temp_vscode_dir / "extensions.json"
        assert ext_file.exists()
        written = json.loads(ext_file.read_text())
        assert written["recommendations"] == test_extensions

    def test_write_launch_json(self, temp_vscode_dir):
        """Test writing launch.json."""
        launch_config = {
            "version": "0.2.0",
            "configurations": [{"name": "Python", "type": "python", "request": "launch"}],
        }

        generator = VSCodeConfigGenerator()
        generator._write_launch_json(temp_vscode_dir, launch_config)

        launch_file = temp_vscode_dir / "launch.json"
        assert launch_file.exists()
        written = json.loads(launch_file.read_text())
        assert written["version"] == "0.2.0"

    def test_merge_settings(self, temp_vscode_dir):
        """Test merging settings."""
        existing = {"editor.formatOnSave": False}
        new = {"python.linting.enabled": True}

        generator = VSCodeConfigGenerator()
        result = generator._merge_settings(existing, new)

        assert result["editor.formatOnSave"] is False
        assert result["python.linting.enabled"] is True

    def test_merge_extensions(self, temp_vscode_dir):
        """Test merging extensions."""
        existing = ["ms-python.python"]
        new = ["ms-python.python", "charliermarsh.ruff"]

        generator = VSCodeConfigGenerator()
        result = generator._merge_extensions(existing, new)

        assert len(result) == 2
        assert "ms-python.python" in result
        assert "charliermarsh.ruff" in result
