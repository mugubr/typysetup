"""Install project dependencies using pip, uv, or poetry."""

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console

from typysetup.core.file_backup_manager import FileBackupManager
from typysetup.models import ProjectConfiguration
from typysetup.utils.rollback_context import RollbackContext

logger = logging.getLogger(__name__)
console = Console()


class DependencyInstaller:
    """Install dependencies using selected package manager.

    Handles:
    - Installation with pip, uv, or poetry
    - Package version extraction
    - Installation verification
    - Error handling and reporting
    """

    def __init__(self):
        """Initialize the dependency installer."""
        self.timeout_pip = 600  # 10 minutes for pip
        self.timeout_uv = 600  # 10 minutes for uv
        self.timeout_poetry = 900  # 15 minutes for poetry (lock file generation)

    def install_dependencies(
        self,
        packages: List[str],
        package_manager: str,
        python_executable: str,
        project_path: Path,
        project_config: ProjectConfiguration,
    ) -> bool:
        """Install dependencies using selected package manager.

        Args:
            packages: List of package specifications (e.g., ["fastapi>=0.104.0"])
            package_manager: Package manager to use ("pip", "uv", or "poetry")
            python_executable: Path to Python executable in venv
            project_path: Path to project directory
            project_config: ProjectConfiguration to update with installed packages

        Returns:
            True if installation succeeded, False otherwise
        """
        if not packages:
            logger.warning("No packages to install")
            return True

        with RollbackContext():
            try:
                logger.info(f"Installing {len(packages)} packages with {package_manager}")

                # Execute installation
                if package_manager == "uv":
                    result = self._install_with_uv(packages, python_executable)
                elif package_manager == "poetry":
                    result = self._install_with_poetry(packages, project_path)
                else:  # Default to pip
                    result = self._install_with_pip(packages, python_executable)

                # Check if installation succeeded
                if result.returncode != 0:
                    logger.error(f"Installation failed with {package_manager}: {result.stderr}")
                    return False

                # Parse and track installed packages
                installed_packages = self._parse_installed_packages(result.stdout, package_manager)

                if installed_packages:
                    for name, version in installed_packages:
                        project_config.add_dependency(
                            name=name,
                            version=version,
                            manager=package_manager,
                        )
                    logger.info(f"Tracked {len(installed_packages)} installed packages")
                else:
                    # Try to get versions from pip show
                    for package_spec in packages:
                        package_name = self._extract_package_name(package_spec)
                        version = self._get_installed_version(package_name, python_executable)
                        if version:
                            project_config.add_dependency(
                                name=package_name,
                                version=version,
                                manager=package_manager,
                            )

                logger.info("Dependencies installed successfully")
                return True

            except subprocess.TimeoutExpired:
                logger.error(f"Installation timed out with {package_manager}")
                return False
            except FileNotFoundError as e:
                logger.error(f"Package manager not found: {e}")
                return False
            except Exception as e:
                logger.error(f"Error during installation: {e}")
                return False

    def _install_with_pip(
        self, packages: List[str], python_executable: str
    ) -> subprocess.CompletedProcess:
        """Install packages using pip.

        Args:
            packages: List of package specifications
            python_executable: Path to Python executable

        Returns:
            CompletedProcess with installation results
        """
        cmd = [
            python_executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            *packages,
        ]

        logger.debug(f"Running pip install: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout_pip,
        )

        return result

    def _install_with_uv(
        self, packages: List[str], python_executable: str
    ) -> subprocess.CompletedProcess:
        """Install packages using uv.

        Args:
            packages: List of package specifications
            python_executable: Path to Python executable in venv

        Returns:
            CompletedProcess with installation results
        """
        # Check if uv is available
        if not shutil.which("uv"):
            raise FileNotFoundError("uv package manager not found in PATH")

        cmd = [
            "uv",
            "pip",
            "install",
            "--python",
            python_executable,
            *packages,
        ]

        logger.debug(f"Running uv install: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout_uv,
        )

        return result

    def _install_with_poetry(
        self, packages: List[str], project_path: Path
    ) -> subprocess.CompletedProcess:
        """Install packages using poetry.

        Note: Poetry installation is more complex as it requires pyproject.toml
        to be generated first with dependencies. This method assumes pyproject.toml
        exists with proper dependencies section.

        Args:
            packages: List of package specifications (informational)
            project_path: Path to project directory

        Returns:
            CompletedProcess with installation results
        """
        # Check if poetry is available
        if not shutil.which("poetry"):
            raise FileNotFoundError("poetry package manager not found in PATH")

        # Configure poetry to use the existing venv
        config_cmd = [
            "poetry",
            "config",
            "virtualenvs.create",
            "false",
        ]

        logger.debug(f"Configuring poetry: {' '.join(config_cmd)}")
        subprocess.run(config_cmd, capture_output=True, timeout=30)

        # Run poetry install
        cmd = [
            "poetry",
            "install",
            "--no-interaction",
        ]

        logger.debug(f"Running poetry install: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=self.timeout_poetry,
        )

        return result

    def _parse_installed_packages(self, output: str, package_manager: str) -> List[Tuple[str, str]]:
        """Parse installed packages and versions from installation output.

        Args:
            output: stdout from package manager
            package_manager: Name of package manager (pip, uv, poetry)

        Returns:
            List of (package_name, version) tuples
        """
        packages: List[Tuple[str, str]] = []

        if package_manager == "pip":
            # Pip output format: "Successfully installed package1-version package2-version ..."
            match = re.search(r"Successfully installed (.+)", output)
            if match:
                installed = match.group(1).split()
                for item in installed:
                    # Format is "package-version"
                    if "-" in item:
                        parts = item.rsplit("-", 1)
                        if len(parts) == 2:
                            packages.append((parts[0], parts[1]))

        elif package_manager == "uv":
            # UV output similar to pip
            match = re.search(r"Installed \d+ package", output)
            if match:
                # Try to extract from "Successfully installed" line
                for line in output.split("\n"):
                    if "Successfully installed" in line:
                        installed = line.replace("Successfully installed", "").strip()
                        for item in installed.split():
                            if "-" in item:
                                parts = item.rsplit("-", 1)
                                if len(parts) == 2:
                                    packages.append((parts[0], parts[1]))

        elif package_manager == "poetry":
            # Poetry output is more verbose, extract from "Installing" lines
            for line in output.split("\n"):
                # Format: "Installing package (version)"
                match = re.search(r"Installing\s+(\S+)\s+\(([^)]+)\)", line)
                if match:
                    packages.append((match.group(1), match.group(2)))

        logger.debug(f"Parsed {len(packages)} packages from {package_manager} output")
        return packages

    def _get_installed_version(self, package_name: str, python_executable: str) -> Optional[str]:
        """Get installed version of a package.

        Args:
            package_name: Name of the package
            python_executable: Path to Python executable

        Returns:
            Version string or None if package not found
        """
        try:
            result = subprocess.run(
                [python_executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()

            return None

        except Exception as e:
            logger.debug(f"Failed to get version for {package_name}: {e}")
            return None

    def _extract_package_name(self, package_spec: str) -> str:
        """Extract package name from specification.

        Args:
            package_spec: Package specification (e.g., "fastapi>=0.104.0", "uvicorn[standard]>=0.24.0")

        Returns:
            Package name only
        """
        # Remove version specifiers and extras
        # Format: package[extra1,extra2]>=version,<version2
        # Extract just the package name before [ or >= or > or < or == or !=

        # First remove extras (everything in brackets)
        package_name = re.sub(r"\[.*?\]", "", package_spec)

        # Then remove version specifiers
        package_name = re.split(r"[><=!~]", package_name)[0].strip()

        return package_name

    def _restore_pyproject(self, pyproject_path: Path, backup_path: Path) -> None:
        """Restore pyproject.toml from backup on rollback.

        Args:
            pyproject_path: Path to original pyproject.toml
            backup_path: Path to backup file
        """
        try:
            file_backup_manager = FileBackupManager()
            file_backup_manager.restore_backup(pyproject_path, backup_path)
            logger.info("Restored pyproject.toml from backup")
        except Exception as e:
            logger.warning(f"Failed to restore pyproject.toml backup: {e}")
