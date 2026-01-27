"""File backup and restore manager for safe config updates."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class FileBackupManager:
    """Manages file backups with timestamped naming for rollback support."""

    BACKUP_SUFFIX = ".backup"

    def __init__(self):
        """Initialize backup manager."""
        pass

    @staticmethod
    def create_backup(filepath: Path) -> Optional[Path]:
        """Create a timestamped backup of a file.

        Args:
            filepath: Path to file to backup

        Returns:
            Path to backup file, or None if file doesn't exist

        Example:
            backup_path = manager.create_backup(Path(".vscode/settings.json"))
            # Creates: .vscode/settings.json.backup.20260111T120000Z
        """
        filepath = Path(filepath)

        if not filepath.exists():
            return None

        # Create backup filename with ISO timestamp including microseconds
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%dT%H%M%S") + f".{now.microsecond:06d}Z"
        backup_path = (
            filepath.parent / f"{filepath.name}{FileBackupManager.BACKUP_SUFFIX}.{timestamp}"
        )

        try:
            shutil.copy2(filepath, backup_path)
            return backup_path
        except OSError as e:
            raise OSError(f"Failed to create backup of {filepath}: {e}") from e

    @staticmethod
    def restore_backup(filepath: Path, backup_path: Path) -> None:
        """Restore a file from backup.

        Args:
            filepath: Path where file should be restored
            backup_path: Path to backup file

        Raises:
            FileNotFoundError: If backup doesn't exist
            IOError: If restore fails
        """
        filepath = Path(filepath)
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            shutil.copy2(backup_path, filepath)
        except OSError as e:
            raise OSError(f"Failed to restore backup {backup_path} to {filepath}: {e}") from e

    @staticmethod
    def list_backups(filepath: Path) -> List[Path]:
        """List all backups for a file, sorted by timestamp (newest first).

        Args:
            filepath: Path to file

        Returns:
            List of backup paths, sorted newest first
        """
        filepath = Path(filepath)
        backup_pattern = f"{filepath.name}{FileBackupManager.BACKUP_SUFFIX}.*"

        backups = list(filepath.parent.glob(backup_pattern))
        # Sort by timestamp in filename (newest first)
        backups.sort(reverse=True)

        return backups

    @staticmethod
    def cleanup_backup(backup_path: Path) -> None:
        """Remove a backup file.

        Args:
            backup_path: Path to backup file

        Raises:
            FileNotFoundError: If backup doesn't exist
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            backup_path.unlink()
        except OSError as e:
            raise OSError(f"Failed to delete backup {backup_path}: {e}") from e

    @staticmethod
    def cleanup_old_backups(filepath: Path, keep_count: int = 3) -> None:
        """Remove old backups, keeping only the most recent.

        Args:
            filepath: Path to file
            keep_count: Number of backups to keep (default: 3)
        """
        backups = FileBackupManager.list_backups(filepath)

        for backup_path in backups[keep_count:]:
            try:
                FileBackupManager.cleanup_backup(backup_path)
            except (OSError, FileNotFoundError):
                # Continue cleaning even if one fails
                pass
