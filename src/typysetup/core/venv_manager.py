"""Virtual environment creation and management."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from venv import EnvBuilder

from rich.console import Console

from typysetup.models.project_config import ProjectConfiguration
from typysetup.utils.paths import (
    get_venv_path,
    get_venv_python_executable,
)
from typysetup.utils.rollback_context import RollbackContext

logger = logging.getLogger(__name__)
console = Console()


class VirtualEnvironmentManager:
    """Manages Python virtual environment creation and validation.

    Handles:
    - Python executable discovery (version-aware)
    - Virtual environment creation using venv.EnvBuilder
    - Validation of created environment
    - ProjectConfiguration updates with actual paths
    - Rollback on failure with cleanup
    """

    def __init__(self) -> None:
        """Initialize the virtual environment manager."""
        self.console = console

    def create_virtual_environment(
        self, project_path: Path, python_version: str, project_config: ProjectConfiguration
    ) -> bool:
        """Create and validate virtual environment.

        Creates a Python virtual environment with pip and upgrades
        installed. Updates ProjectConfiguration with actual paths after
        successful creation.

        Args:
            project_path: Path to project directory
            python_version: Requested Python version (e.g., "3.11", "3.10+")
            project_config: ProjectConfiguration instance to update after creation

        Returns:
            True if creation and validation successful, False otherwise

        Raises:
            FileNotFoundError: If suitable Python executable not found
            RuntimeError: If venv creation or validation fails
        """
        venv_path = get_venv_path(project_path)

        with RollbackContext() as rollback:
            try:
                # Step 1: Discover suitable Python executable
                console.print("[dim]  Searching for Python executable...[/dim]")
                python_exe = self.discover_python_executable(python_version)

                if python_exe is None:
                    raise FileNotFoundError(
                        f"Python {python_version} not found. "
                        f"Please install Python or verify it's in your PATH."
                    )

                console.print(f"[dim]  Found: {python_exe}[/dim]")

                # Step 2: Validate Python version
                if not self.validate_python_version(python_exe, python_version):
                    actual_version = self._get_python_version(python_exe)
                    raise RuntimeError(
                        f"Python version mismatch. "
                        f"Requested: {python_version}, Found: {actual_version}"
                    )

                # Step 3: Create virtual environment directory
                console.print(f"[dim]  Creating venv at {venv_path}...[/dim]")
                builder = EnvBuilder(with_pip=True, upgrade_deps=True)
                builder.create(str(venv_path))

                # Register rollback: remove venv directory on any exception
                rollback.register_cleanup(
                    lambda: shutil.rmtree(venv_path, ignore_errors=True),
                    f"Remove virtual environment directory {venv_path}",
                )

                # Step 4: Validate venv structure
                if not self.validate_venv_structure(venv_path):
                    raise RuntimeError(
                        "Virtual environment structure is invalid or incomplete. "
                        "Creation may have failed."
                    )

                # Step 5: Validate venv executable
                if not self.validate_venv_executable(venv_path):
                    raise RuntimeError(
                        "Virtual environment Python executable does not work. "
                        "Try a different Python version."
                    )

                # Step 6: Validate pip installation
                if not self.validate_pip_installed(venv_path):
                    raise RuntimeError(
                        "pip is not available in the virtual environment. "
                        "Dependency installation will not work."
                    )

                # Step 7: Update ProjectConfiguration with actual paths
                self.update_project_config(project_config, venv_path)

                return True

            except FileNotFoundError as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"Python executable not found: {e}")
                return False

            except RuntimeError as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"Virtual environment creation failed: {e}")
                return False

            except KeyboardInterrupt:
                console.print("\n[yellow]Virtual environment creation cancelled by user[/yellow]")
                logger.info("Virtual environment creation cancelled by user")
                return False

            except Exception as e:
                console.print(f"[red]Unexpected error: {e}[/red]")
                logger.exception(f"Unexpected error during venv creation: {e}")
                return False

    def discover_python_executable(self, requested_version: str) -> Optional[Path]:
        """Find suitable Python executable in system PATH.

        Search order:
        1. python{major}.{minor} (e.g., python3.11)
        2. python{major} (e.g., python3)
        3. python
        4. sys.executable (fallback)

        Args:
            requested_version: Version string (e.g., "3.11", "3.10+")

        Returns:
            Path to Python executable or None if not found
        """
        # Parse version string (handle "3.11", "3.10+", "3.8+")
        version_parts = requested_version.rstrip("+").split(".")

        # List of executables to try, in order of preference
        candidates = []

        if len(version_parts) >= 2:
            # Try specific version (e.g., python3.11)
            major, minor = version_parts[0], version_parts[1]
            candidates.append(f"python{major}.{minor}")

        if version_parts:
            # Try major version only (e.g., python3)
            major = version_parts[0]
            candidates.append(f"python{major}")

        # Generic fallback
        candidates.extend(["python", "python3"])

        # Try each candidate in PATH
        for candidate in candidates:
            exe_path = shutil.which(candidate)
            if exe_path:
                exe_path_obj = Path(exe_path)
                # Validate the executable is actually usable before returning
                if self._is_executable_valid(exe_path_obj):
                    logger.debug(f"Found valid Python executable: {exe_path}")
                    return exe_path_obj
                else:
                    logger.debug(f"Skipping invalid Python executable: {exe_path}")

        # Final fallback: use current interpreter
        logger.debug(f"Using current interpreter as fallback: {sys.executable}")
        return Path(sys.executable)

    def validate_python_version(self, python_path: Path, min_version: str) -> bool:
        """Verify Python version meets minimum requirement.

        Args:
            python_path: Path to Python executable
            min_version: Minimum version required (e.g., "3.10", "3.11")

        Returns:
            True if version is sufficient, False otherwise
        """
        try:
            actual_version = self._get_python_version(python_path)

            if actual_version is None:
                logger.warning(f"Could not determine version for {python_path}")
                return False

            # Parse versions for comparison
            actual_major, actual_minor = self._parse_version(actual_version)
            min_major, min_minor = self._parse_version(min_version.rstrip("+"))

            # Compare versions
            if actual_major > min_major or (
                actual_major == min_major and actual_minor >= min_minor
            ):
                logger.debug(f"Python version {actual_version} meets requirement {min_version}")
                return True

            logger.warning(
                f"Python version {actual_version} does not meet requirement {min_version}"
            )
            return False

        except Exception as e:
            logger.error(f"Error validating Python version: {e}")
            return False

    def _is_executable_valid(self, python_path: Path) -> bool:
        """Check if a Python executable is actually usable.

        Tests the executable by running it with --version to ensure
        it's not a broken symlink or inaccessible shim.

        Args:
            python_path: Path to Python executable

        Returns:
            True if executable can run, False otherwise
        """
        try:
            result = subprocess.run(
                [str(python_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.debug(f"Executable is valid: {python_path}")
                return True
            else:
                logger.debug(f"Executable returned non-zero exit code: {python_path}")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Executable validation failed for {python_path}: {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error validating executable {python_path}: {e}")
            return False

    def validate_venv_structure(self, venv_path: Path) -> bool:
        """Validate virtual environment directory structure.

        Checks for essential files/directories that should exist
        in a valid virtual environment.

        Args:
            venv_path: Path to virtual environment directory

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            venv_path = Path(venv_path)

            # Check if venv directory exists
            if not venv_path.exists():
                logger.warning(f"Venv directory does not exist: {venv_path}")
                return False

            # Check for pyvenv.cfg configuration file
            pyvenv_cfg = venv_path / "pyvenv.cfg"
            if not pyvenv_cfg.exists():
                logger.warning(f"Missing pyvenv.cfg: {pyvenv_cfg}")
                return False

            # Check for Python executable
            python_exe = get_venv_python_executable(venv_path)
            if not python_exe.exists():
                logger.warning(f"Python executable not found: {python_exe}")
                return False

            logger.debug(f"Venv structure is valid: {venv_path}")
            return True

        except Exception as e:
            logger.error(f"Error validating venv structure: {e}")
            return False

    def validate_venv_executable(self, venv_path: Path) -> bool:
        """Verify venv Python executable works.

        Runs `python --version` in the virtual environment to confirm
        the interpreter is functional.

        Args:
            venv_path: Path to virtual environment directory

        Returns:
            True if executable works, False otherwise
        """
        try:
            python_exe = get_venv_python_executable(venv_path)

            if not python_exe.exists():
                logger.warning(f"Python executable not found: {python_exe}")
                return False

            result = subprocess.run(
                [str(python_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(
                    f"Python executable failed with code {result.returncode}: {result.stderr}"
                )
                return False

            logger.debug(f"Python executable is functional: {result.stdout.strip()}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Python version check timed out for {venv_path}")
            return False

        except Exception as e:
            logger.error(f"Error validating venv executable: {e}")
            return False

    def validate_pip_installed(self, venv_path: Path) -> bool:
        """Verify pip package manager is available.

        Required for Phase 7 (dependency installation).

        Args:
            venv_path: Path to virtual environment directory

        Returns:
            True if pip is available, False otherwise
        """
        try:
            python_exe = get_venv_python_executable(venv_path)

            result = subprocess.run(
                [str(python_exe), "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(f"pip check failed with code {result.returncode}: {result.stderr}")
                return False

            if "pip" not in result.stdout.lower():
                logger.warning(f"pip not found in output: {result.stdout}")
                return False

            logger.debug(f"pip is available: {result.stdout.strip()}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"pip version check timed out for {venv_path}")
            return False

        except Exception as e:
            logger.error(f"Error validating pip installation: {e}")
            return False

    def update_project_config(self, project_config: ProjectConfiguration, venv_path: Path) -> None:
        """Update ProjectConfiguration with actual venv paths.

        Replaces any hardcoded or placeholder paths with actual paths
        determined after venv creation.

        Args:
            project_config: ProjectConfiguration instance to update
            venv_path: Path to created virtual environment
        """
        try:
            venv_path = Path(venv_path)

            # Get actual executable path (cross-platform)
            python_exe = get_venv_python_executable(venv_path)

            # Update configuration
            project_config.python_executable = str(python_exe)
            project_config.venv_path = str(venv_path)

            logger.debug(
                f"Updated ProjectConfiguration: "
                f"venv_path={venv_path}, python_executable={python_exe}"
            )

        except Exception as e:
            logger.error(f"Error updating ProjectConfiguration: {e}")
            raise

    # Helper methods

    def _get_python_version(self, python_path: Path) -> Optional[str]:
        """Get Python version string from executable.

        Args:
            python_path: Path to Python executable

        Returns:
            Version string (e.g., "3.11.5") or None if error
        """
        try:
            result = subprocess.run(
                [str(python_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                return None

            # Parse "Python 3.11.5" -> "3.11.5"
            output = result.stdout.strip()
            if output.startswith("Python "):
                return output[7:]  # Remove "Python " prefix

            return output

        except Exception as e:
            logger.error(f"Error getting Python version from {python_path}: {e}")
            return None

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        """Parse version string to (major, minor) tuple.

        Args:
            version_str: Version string (e.g., "3.11", "3.11.5")

        Returns:
            Tuple of (major, minor) as integers
        """
        try:
            parts = version_str.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            return (major, minor)
        except (ValueError, IndexError):
            logger.warning(f"Could not parse version string: {version_str}")
            return (0, 0)
