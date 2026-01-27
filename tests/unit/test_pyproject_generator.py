"""Unit tests for PyProjectGenerator."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomli_w

from typysetup.core.pyproject_generator import PyprojectGenerator
from typysetup.models import ProjectMetadata

# Use tomllib for Python 3.11+, tomli for earlier versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def project_metadata():
    """Create sample ProjectMetadata."""
    return ProjectMetadata(
        project_name="test_project",
        project_description="A test project",
        author_name="Test Author",
        author_email="test@example.com",
    )


@pytest.fixture
def generator():
    """Create a PyprojectGenerator instance."""
    return PyprojectGenerator()


class TestPyprojectGeneratorInit:
    """Tests for PyprojectGenerator initialization."""

    def test_init_creates_backup_manager(self):
        """Test that __init__ creates FileBackupManager."""
        generator = PyprojectGenerator()
        assert generator.file_backup_manager is not None


class TestBuildConfig:
    """Tests for _build_config method."""

    def test_build_config_minimal(self, generator, project_metadata):
        """Test building config with minimal metadata."""
        config = generator._build_config(
            project_metadata,
            dependencies=[],
            python_version="3.10+",
        )

        assert "project" in config
        assert config["project"]["name"] == "test_project"
        assert config["project"]["version"] == "0.1.0"
        assert config["project"]["description"] == "A test project"
        assert config["project"]["requires-python"] == ">=3.10"

    def test_build_config_with_author(self, generator, project_metadata):
        """Test building config with author information."""
        config = generator._build_config(
            project_metadata,
            dependencies=[],
            python_version="3.11+",
        )

        assert "authors" in config["project"]
        authors = config["project"]["authors"]
        assert len(authors) == 1
        assert authors[0]["name"] == "Test Author"
        assert authors[0]["email"] == "test@example.com"

    def test_build_config_without_email(self, generator):
        """Test building config with author but no email."""
        metadata = ProjectMetadata(
            project_name="test",
            project_description="Test",
            author_name="Author",
        )
        config = generator._build_config(
            metadata,
            dependencies=[],
            python_version="3.10+",
        )

        authors = config["project"]["authors"]
        assert len(authors) == 1
        assert authors[0]["name"] == "Author"
        assert "email" not in authors[0]

    def test_build_config_with_dependencies(self, generator, project_metadata):
        """Test building config with dependencies."""
        dependencies = ["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0"]
        config = generator._build_config(
            project_metadata,
            dependencies=dependencies,
            python_version="3.10+",
        )

        assert "dependencies" in config["project"]
        assert config["project"]["dependencies"] == dependencies

    def test_build_config_removes_python_version_plus(self, generator, project_metadata):
        """Test that + is removed from Python version."""
        config = generator._build_config(
            project_metadata,
            dependencies=[],
            python_version="3.9+",
        )

        assert config["project"]["requires-python"] == ">=3.9"

    def test_build_config_includes_readme(self, generator, project_metadata):
        """Test that README.md is included in config."""
        config = generator._build_config(
            project_metadata,
            dependencies=[],
            python_version="3.10+",
        )

        assert config["project"]["readme"] == "README.md"


class TestGeneratePyprojectToml:
    """Tests for generate_pyproject_toml method."""

    def test_generate_new_pyproject(self, generator, project_metadata, temp_project_dir):
        """Test generating a new pyproject.toml."""
        pyproject_path = temp_project_dir / "pyproject.toml"

        result = generator.generate_pyproject_toml(
            project_path=temp_project_dir,
            metadata=project_metadata,
            dependencies=["fastapi>=0.104.0"],
            python_version="3.10+",
        )

        assert result == pyproject_path
        assert pyproject_path.exists()

        # Verify the content
        if tomllib is None:
            pytest.skip("tomli not available")
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        assert config["project"]["name"] == "test_project"
        assert config["project"]["version"] == "0.1.0"
        assert "fastapi>=0.104.0" in config["project"]["dependencies"]

    def test_generate_pyproject_with_existing_file(
        self, generator, project_metadata, temp_project_dir
    ):
        """Test generating pyproject.toml when file already exists."""
        pyproject_path = temp_project_dir / "pyproject.toml"

        # Create existing file
        existing_config = {"project": {"name": "old_project"}}
        with open(pyproject_path, "wb") as f:
            tomli_w.dump(existing_config, f)

        # Generate new config
        result = generator.generate_pyproject_toml(
            project_path=temp_project_dir,
            metadata=project_metadata,
            dependencies=[],
            python_version="3.10+",
        )

        assert result == pyproject_path
        assert pyproject_path.exists()

        # Verify backup was created
        backup_files = list(temp_project_dir.glob("pyproject.toml.backup*"))
        assert len(backup_files) == 1

    def test_generate_pyproject_backup_created_for_existing_file(
        self, generator, project_metadata, temp_project_dir
    ):
        """Test that backup is created when overwriting existing file."""
        # Create existing file
        pyproject_path = temp_project_dir / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'old_project'")

        # Generate new config - should create backup
        result = generator.generate_pyproject_toml(
            project_path=temp_project_dir,
            metadata=project_metadata,
            dependencies=[],
            python_version="3.10+",
        )

        assert result.exists()

        # Verify backup was created
        backup_files = list(temp_project_dir.glob("pyproject.toml.backup*"))
        assert len(backup_files) == 1, "Expected exactly one backup file"

        # Verify backup contains old content
        if tomllib is None:
            pytest.skip("tomli not available")
        with open(backup_files[0], "rb") as f:
            backup_config = tomllib.load(f)
        assert backup_config["project"]["name"] == "old_project"

    def test_generate_pyproject_with_multiple_dependencies(
        self, generator, project_metadata, temp_project_dir
    ):
        """Test generating pyproject.toml with multiple dependencies."""
        dependencies = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.0",
            "sqlalchemy>=2.0",
        ]

        result = generator.generate_pyproject_toml(
            project_path=temp_project_dir,
            metadata=project_metadata,
            dependencies=dependencies,
            python_version="3.11+",
        )

        assert result.exists()

        # Verify all dependencies are included
        if tomllib is None:
            pytest.skip("tomli not available")
        with open(result, "rb") as f:
            config = tomllib.load(f)

        assert len(config["project"]["dependencies"]) == 4
        for dep in dependencies:
            assert dep in config["project"]["dependencies"]

    def test_generate_pyproject_different_python_versions(
        self, generator, project_metadata, temp_project_dir
    ):
        """Test generating pyproject.toml with different Python versions."""
        for py_version in ["3.8+", "3.9+", "3.10+", "3.11+", "3.12+"]:
            subdir = temp_project_dir / py_version.replace(".", "_").replace("+", "")
            subdir.mkdir(exist_ok=True)

            result = generator.generate_pyproject_toml(
                project_path=subdir,
                metadata=project_metadata,
                dependencies=[],
                python_version=py_version,
            )

            assert result.exists()

            # Verify version is correct
            if tomllib is None:
                pytest.skip("tomli not available")
            with open(result, "rb") as f:
                config = tomllib.load(f)

            expected_version = py_version.rstrip("+")
            assert config["project"]["requires-python"] == f">={expected_version}"


class TestRestoreBackup:
    """Tests for restore_backup method."""

    @patch("typysetup.core.pyproject_generator.FileBackupManager")
    def test_restore_backup_success(self, mock_manager_class):
        """Test successful backup restoration."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        generator = PyprojectGenerator()
        generator.restore_backup(Path("/tmp/pyproject.toml"), Path("/tmp/backup"))

        mock_manager.restore_backup.assert_called_once()

    @patch("typysetup.core.pyproject_generator.FileBackupManager")
    def test_restore_backup_error(self, mock_manager_class):
        """Test backup restoration with error."""
        mock_manager = MagicMock()
        mock_manager.restore_backup.side_effect = Exception("Restore failed")
        mock_manager_class.return_value = mock_manager

        generator = PyprojectGenerator()
        with pytest.raises(IOError):
            generator.restore_backup(Path("/tmp/pyproject.toml"), Path("/tmp/backup"))


class TestGeneratePyprojectValidation:
    """Tests for validation in generate_pyproject_toml."""

    def test_generated_file_is_valid_toml(self, generator, project_metadata, temp_project_dir):
        """Test that generated file is valid TOML."""
        result = generator.generate_pyproject_toml(
            project_path=temp_project_dir,
            metadata=project_metadata,
            dependencies=["fastapi>=0.104.0"],
            python_version="3.10+",
        )

        # Should be readable as TOML without errors
        if tomllib is None:
            pytest.skip("tomli not available")
        with open(result, "rb") as f:
            config = tomllib.load(f)

        assert isinstance(config, dict)
        assert "project" in config

    def test_generated_file_has_required_fields(
        self, generator, project_metadata, temp_project_dir
    ):
        """Test that generated file has all required fields."""
        result = generator.generate_pyproject_toml(
            project_path=temp_project_dir,
            metadata=project_metadata,
            dependencies=[],
            python_version="3.10+",
        )

        if tomllib is None:
            pytest.skip("tomli not available")
        with open(result, "rb") as f:
            config = tomllib.load(f)

        project_section = config["project"]
        assert "name" in project_section
        assert "version" in project_section
        assert "requires-python" in project_section

    def test_generated_file_pep_621_compliant(self, generator, project_metadata, temp_project_dir):
        """Test that generated file is PEP 621 compliant."""
        result = generator.generate_pyproject_toml(
            project_path=temp_project_dir,
            metadata=project_metadata,
            dependencies=["fastapi>=0.104.0"],
            python_version="3.10+",
        )

        if tomllib is None:
            pytest.skip("tomli not available")
        with open(result, "rb") as f:
            config = tomllib.load(f)

        # PEP 621 requires these fields
        assert "project" in config
        assert isinstance(config["project"], dict)

        # Check that version is a string, not a list
        assert isinstance(config["project"]["version"], str)
        assert isinstance(config["project"]["name"], str)
