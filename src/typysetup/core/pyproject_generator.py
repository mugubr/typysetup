"""Generate PEP 621 compliant pyproject.toml files."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import tomli_w

from typysetup.core.file_backup_manager import FileBackupManager
from typysetup.models import ProjectMetadata

logger = logging.getLogger(__name__)


class PyprojectGenerator:
    """Generate and manage pyproject.toml files.

    Handles:
    - PEP 621 compliant pyproject.toml generation
    - Backup of existing files
    - Restoration on failure
    """

    def __init__(self):
        """Initialize the generator with backup manager."""
        self.file_backup_manager = FileBackupManager()

    def generate_pyproject_toml(
        self,
        project_path: Path,
        metadata: ProjectMetadata,
        dependencies: List[str],
        python_version: str,
    ) -> Path:
        """Generate pyproject.toml in the project directory.

        Args:
            project_path: Path to project directory
            metadata: Project metadata (name, description, author)
            dependencies: List of packages to install (e.g., ["fastapi>=0.104.0"])
            python_version: Minimum Python version (e.g., "3.10+")

        Returns:
            Path to generated pyproject.toml

        Raises:
            ValueError: If project metadata is invalid
            IOError: If file operations fail
        """
        project_path = Path(project_path)
        pyproject_path = project_path / "pyproject.toml"

        try:
            # Build the configuration dictionary
            config = self._build_config(metadata, dependencies, python_version)

            # Backup existing file if it exists
            backup_path: Optional[Path] = None
            if pyproject_path.exists():
                logger.info(f"Backing up existing pyproject.toml at {pyproject_path}")
                backup_path = self.file_backup_manager.create_backup(pyproject_path)
                logger.debug(f"Backup created at {backup_path}")

                # Cleanup old backups, keep only 3 most recent
                self.file_backup_manager.cleanup_old_backups(pyproject_path, keep_count=3)

            try:
                # Write the new file
                logger.debug(f"Writing pyproject.toml to {pyproject_path}")
                with open(pyproject_path, "wb") as f:
                    tomli_w.dump(config, f)

                logger.info(f"Successfully generated pyproject.toml at {pyproject_path}")
                return pyproject_path

            except Exception as e:
                # If writing fails, restore backup
                if backup_path:
                    logger.error(f"Failed to write pyproject.toml: {e}. Restoring backup.")
                    self.file_backup_manager.restore_backup(pyproject_path, backup_path)
                raise OSError(f"Failed to generate pyproject.toml: {e}") from e

        except Exception as e:
            logger.error(f"Error generating pyproject.toml: {e}")
            raise

    def _build_config(
        self, metadata: ProjectMetadata, dependencies: List[str], python_version: str
    ) -> Dict[str, Any]:
        """Build the complete pyproject.toml configuration dictionary.

        Args:
            metadata: Project metadata
            dependencies: List of package specifications
            python_version: Minimum Python version (e.g., "3.10+")

        Returns:
            Dictionary suitable for TOML serialization
        """
        # Parse Python version (remove + suffix if present)
        min_version = python_version.rstrip("+")

        # Build [project] section
        project_section = {
            "name": metadata.project_name,
            "version": "0.1.0",
            "description": metadata.project_description or "",
            "requires-python": f">={min_version}",
        }

        # Add author if provided
        if metadata.author_name:
            authors = [{"name": metadata.author_name}]
            if metadata.author_email:
                authors[0]["email"] = metadata.author_email
            project_section["authors"] = authors

        # Add README if likely to exist
        project_section["readme"] = "README.md"

        # Add dependencies
        if dependencies:
            project_section["dependencies"] = dependencies

        # Build complete config
        config = {"project": project_section}

        logger.debug(f"Built config: {config}")
        return config

    def restore_backup(self, pyproject_path: Path, backup_path: Path) -> None:
        """Restore a backup of pyproject.toml.

        Args:
            pyproject_path: Path to original pyproject.toml
            backup_path: Path to backup file

        Raises:
            IOError: If restoration fails
        """
        try:
            logger.info("Restoring pyproject.toml from backup")
            self.file_backup_manager.restore_backup(pyproject_path, backup_path)
            logger.info("Successfully restored pyproject.toml from backup")
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            raise OSError(f"Failed to restore pyproject.toml backup: {e}") from e
