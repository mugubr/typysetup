"""Unit tests for DependencyInstaller."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from typysetup.core.dependency_installer import DependencyInstaller
from typysetup.models import ProjectConfiguration, ProjectMetadata


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def project_config(temp_project_dir):
    """Create a sample ProjectConfiguration."""
    return ProjectConfiguration(
        project_path=str(temp_project_dir),
        setup_type_slug="fastapi_project",
        python_version="3.10+",
        python_executable="/venv/bin/python",
        package_manager="pip",
        venv_path=str(temp_project_dir / "venv"),
    )


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
def installer():
    """Create a DependencyInstaller instance."""
    return DependencyInstaller()


class TestDependencyInstallerInit:
    """Tests for DependencyInstaller initialization."""

    def test_init_sets_timeouts(self):
        """Test that __init__ sets appropriate timeouts."""
        installer = DependencyInstaller()
        assert installer.timeout_pip == 600
        assert installer.timeout_uv == 600
        assert installer.timeout_poetry == 900


class TestExtractPackageName:
    """Tests for _extract_package_name method."""

    def test_extract_simple_package(self, installer):
        """Test extraction of simple package name."""
        assert installer._extract_package_name("fastapi") == "fastapi"

    def test_extract_with_version_specifier(self, installer):
        """Test extraction with version specifier."""
        assert installer._extract_package_name("fastapi>=0.104.0") == "fastapi"

    def test_extract_with_extras(self, installer):
        """Test extraction with package extras."""
        assert installer._extract_package_name("uvicorn[standard]>=0.24.0") == "uvicorn"

    def test_extract_with_multiple_extras(self, installer):
        """Test extraction with multiple extras."""
        assert installer._extract_package_name("requests[security,socks]>=2.28.0") == "requests"

    def test_extract_with_complex_version(self, installer):
        """Test extraction with complex version specifier."""
        assert installer._extract_package_name("django>=3.2,<4.0") == "django"

    def test_extract_with_multiple_operators(self, installer):
        """Test extraction with multiple comparison operators."""
        assert installer._extract_package_name("pytest>=7.0,!=7.1.0,<8.0") == "pytest"


class TestParseInstalledPackages:
    """Tests for _parse_installed_packages method."""

    def test_parse_pip_output_single_package(self, installer):
        """Test parsing pip output with single package."""
        output = "Successfully installed fastapi-0.104.1"
        packages = installer._parse_installed_packages(output, "pip")
        assert len(packages) == 1
        assert packages[0] == ("fastapi", "0.104.1")

    def test_parse_pip_output_multiple_packages(self, installer):
        """Test parsing pip output with multiple packages."""
        output = "Successfully installed fastapi-0.104.1 uvicorn-0.24.0 pydantic-2.5.0"
        packages = installer._parse_installed_packages(output, "pip")
        assert len(packages) == 3
        assert ("fastapi", "0.104.1") in packages
        assert ("uvicorn", "0.24.0") in packages
        assert ("pydantic", "2.5.0") in packages

    def test_parse_uv_output(self, installer):
        """Test parsing uv output."""
        output = "Installed 3 packages\nSuccessfully installed fastapi-0.104.1 uvicorn-0.24.0"
        packages = installer._parse_installed_packages(output, "uv")
        assert len(packages) >= 1
        assert ("fastapi", "0.104.1") in packages or ("uvicorn", "0.24.0") in packages

    def test_parse_poetry_output(self, installer):
        """Test parsing poetry output."""
        output = (
            "Installing fastapi (0.104.1)\nInstalling uvicorn (0.24.0)\nInstalling pydantic (2.5.0)"
        )
        packages = installer._parse_installed_packages(output, "poetry")
        assert len(packages) == 3
        assert ("fastapi", "0.104.1") in packages
        assert ("uvicorn", "0.24.0") in packages
        assert ("pydantic", "2.5.0") in packages

    def test_parse_empty_output(self, installer):
        """Test parsing empty output."""
        packages = installer._parse_installed_packages("", "pip")
        assert packages == []

    def test_parse_no_matches(self, installer):
        """Test parsing output with no package matches."""
        output = "This is some random output"
        packages = installer._parse_installed_packages(output, "pip")
        assert packages == []


class TestGetInstalledVersion:
    """Tests for _get_installed_version method."""

    @patch("subprocess.run")
    def test_get_version_found(self, mock_run, installer):
        """Test getting version when package is found."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Name: fastapi\nVersion: 0.104.1\nSummary: FastAPI"
        mock_run.return_value = mock_result

        version = installer._get_installed_version("fastapi", "/venv/bin/python")
        assert version == "0.104.1"

    @patch("subprocess.run")
    def test_get_version_not_found(self, mock_run, installer):
        """Test getting version when package is not found."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        version = installer._get_installed_version("nonexistent", "/venv/bin/python")
        assert version is None

    @patch("subprocess.run")
    def test_get_version_exception(self, mock_run, installer):
        """Test getting version when exception occurs."""
        mock_run.side_effect = Exception("Test error")

        version = installer._get_installed_version("fastapi", "/venv/bin/python")
        assert version is None


class TestInstallWithPip:
    """Tests for _install_with_pip method."""

    @patch("subprocess.run")
    def test_install_pip_success(self, mock_run, installer):
        """Test successful pip installation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully installed fastapi-0.104.1"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = installer._install_with_pip(["fastapi>=0.104.0"], "/venv/bin/python")

        assert result.returncode == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0][0] == "/venv/bin/python"
        assert "-m" in args[0]
        assert "pip" in args[0]
        assert "install" in args[0]
        assert kwargs["timeout"] == 600

    @patch("subprocess.run")
    def test_install_pip_failure(self, mock_run, installer):
        """Test failed pip installation."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Package not found"
        mock_run.return_value = mock_result

        result = installer._install_with_pip(["nonexistent"], "/venv/bin/python")

        assert result.returncode == 1


class TestInstallWithUv:
    """Tests for _install_with_uv method."""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_install_uv_success(self, mock_run, mock_which, installer):
        """Test successful uv installation."""
        mock_which.return_value = "/usr/bin/uv"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Installed 1 package"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = installer._install_with_uv(["fastapi>=0.104.0"], "/venv/bin/python")

        assert result.returncode == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0][0] == "uv"
        assert "pip" in args[0]
        assert "install" in args[0]
        assert "--python" in args[0]
        assert kwargs["timeout"] == 600

    @patch("shutil.which")
    def test_install_uv_not_found(self, mock_which, installer):
        """Test uv installation when uv is not available."""
        mock_which.return_value = None

        with pytest.raises(FileNotFoundError):
            installer._install_with_uv(["fastapi>=0.104.0"], "/venv/bin/python")


class TestInstallWithPoetry:
    """Tests for _install_with_poetry method."""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_install_poetry_success(self, mock_run, mock_which, installer, temp_project_dir):
        """Test successful poetry installation."""
        mock_which.return_value = "/usr/bin/poetry"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Installing fastapi (0.104.1)"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = installer._install_with_poetry(["fastapi>=0.104.0"], temp_project_dir)

        assert result.returncode == 0
        # Should be called twice: once for config, once for install
        assert mock_run.call_count >= 1

    @patch("shutil.which")
    def test_install_poetry_not_found(self, mock_which, installer, temp_project_dir):
        """Test poetry installation when poetry is not available."""
        mock_which.return_value = None

        with pytest.raises(FileNotFoundError):
            installer._install_with_poetry(["fastapi>=0.104.0"], temp_project_dir)


class TestInstallDependencies:
    """Tests for install_dependencies method."""

    @patch.object(DependencyInstaller, "_install_with_pip")
    @patch.object(DependencyInstaller, "_parse_installed_packages")
    def test_install_dependencies_empty_list(
        self, mock_parse, mock_install, installer, project_config
    ):
        """Test installation with empty package list."""
        result = installer.install_dependencies(
            packages=[],
            package_manager="pip",
            python_executable="/venv/bin/python",
            project_path=Path("/tmp/project"),
            project_config=project_config,
        )

        assert result is True
        mock_install.assert_not_called()

    @patch.object(DependencyInstaller, "_install_with_pip")
    @patch.object(DependencyInstaller, "_parse_installed_packages")
    def test_install_dependencies_pip_success(
        self, mock_parse, mock_install, installer, project_config
    ):
        """Test successful installation with pip."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully installed fastapi-0.104.1"
        mock_install.return_value = mock_result
        mock_parse.return_value = [("fastapi", "0.104.1")]

        result = installer.install_dependencies(
            packages=["fastapi>=0.104.0"],
            package_manager="pip",
            python_executable="/venv/bin/python",
            project_path=Path("/tmp/project"),
            project_config=project_config,
        )

        assert result is True
        assert project_config.installed_dependencies[0].name == "fastapi"

    @patch.object(DependencyInstaller, "_install_with_pip")
    def test_install_dependencies_pip_failure(self, mock_install, installer, project_config):
        """Test failed installation with pip."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Package not found"
        mock_install.return_value = mock_result

        result = installer.install_dependencies(
            packages=["nonexistent"],
            package_manager="pip",
            python_executable="/venv/bin/python",
            project_path=Path("/tmp/project"),
            project_config=project_config,
        )

        assert result is False

    @patch.object(DependencyInstaller, "_install_with_pip")
    def test_install_dependencies_timeout(self, mock_install, installer, project_config):
        """Test installation timeout."""
        mock_install.side_effect = subprocess.TimeoutExpired("pip install", 600)

        result = installer.install_dependencies(
            packages=["fastapi>=0.104.0"],
            package_manager="pip",
            python_executable="/venv/bin/python",
            project_path=Path("/tmp/project"),
            project_config=project_config,
        )

        assert result is False

    @patch.object(DependencyInstaller, "_install_with_uv")
    @patch.object(DependencyInstaller, "_parse_installed_packages")
    def test_install_dependencies_uv(self, mock_parse, mock_install, installer, project_config):
        """Test installation with uv."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Installed 1 package"
        mock_install.return_value = mock_result
        mock_parse.return_value = [("fastapi", "0.104.1")]

        result = installer.install_dependencies(
            packages=["fastapi>=0.104.0"],
            package_manager="uv",
            python_executable="/venv/bin/python",
            project_path=Path("/tmp/project"),
            project_config=project_config,
        )

        assert result is True

    @patch.object(DependencyInstaller, "_install_with_poetry")
    @patch.object(DependencyInstaller, "_parse_installed_packages")
    def test_install_dependencies_poetry(self, mock_parse, mock_install, installer, project_config):
        """Test installation with poetry."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Installing fastapi (0.104.1)"
        mock_install.return_value = mock_result
        mock_parse.return_value = [("fastapi", "0.104.1")]

        result = installer.install_dependencies(
            packages=["fastapi>=0.104.0"],
            package_manager="poetry",
            python_executable="/venv/bin/python",
            project_path=Path("/tmp/project"),
            project_config=project_config,
        )

        assert result is True
