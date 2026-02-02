"""VSCode configuration generator for workspace settings and extensions."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from typysetup.core.file_backup_manager import FileBackupManager
from typysetup.models import ProjectConfiguration, SetupType, VSCodeConfiguration

console = Console()


class VSCodeConfigGenerator:
    """Generates and manages VSCode workspace configuration files."""

    def __init__(self):
        """Initialize the VSCode config generator."""
        self.backup_manager = FileBackupManager()
        self.backups: Dict[str, Path] = {}  # Track created backups for rollback

    def generate(
        self,
        setup_type: SetupType,
        project_config: ProjectConfiguration,
        project_path: Path,
    ) -> bool:
        """Generate VSCode configuration for the project.

        Args:
            setup_type: Setup type with VSCode configuration
            project_config: Project configuration
            project_path: Path to project directory

        Returns:
            True if successful, False if cancelled/failed

        Raises:
            IOError: If file operations fail
        """
        project_path = Path(project_path)
        vscode_dir = project_path / ".vscode"

        try:
            # Create .vscode directory if needed
            vscode_dir.mkdir(parents=True, exist_ok=True)

            # Load existing configurations
            existing_settings = self._load_existing_settings(vscode_dir)
            existing_extensions = self._load_existing_extensions(vscode_dir)
            existing_launch = self._load_existing_launch_config(vscode_dir)

            # Create configuration from setup type
            setup_config = VSCodeConfiguration.from_setup_type(setup_type)

            # Add selected extensions from project config
            if project_config.selected_extensions:
                setup_config.extensions.extend(project_config.selected_extensions)

            # Backup existing files
            self._backup_existing_configs(vscode_dir)

            # Merge configurations
            merged_settings = self._merge_settings(existing_settings or {}, setup_config.settings)
            merged_extensions = self._merge_extensions(
                existing_extensions or [], setup_config.extensions
            )
            merged_launch = self._merge_launch_configs(
                existing_launch or {"configurations": []},
                {"configurations": setup_config.launch_configurations},
            )

            # Write configuration files
            self._write_settings_json(vscode_dir, merged_settings)
            self._write_extensions_json(vscode_dir, merged_extensions)
            self._write_launch_json(vscode_dir, merged_launch)

            console.print("[green]✓[/green] VSCode configuration generated successfully")
            return True

        except Exception as e:
            console.print(f"[red]Error generating VSCode config: {e}[/red]")
            self._restore_from_backups(vscode_dir)
            raise

    def _load_existing_settings(self, vscode_dir: Path) -> Optional[Dict[str, Any]]:
        """Load existing .vscode/settings.json if it exists.

        Args:
            vscode_dir: Path to .vscode directory

        Returns:
            Settings dict or None if file doesn't exist
        """
        settings_path = vscode_dir / "settings.json"

        if not settings_path.exists():
            return None

        try:
            with open(settings_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[yellow]Warning: Could not read existing settings.json: {e}[/yellow]")
            return None

    def _load_existing_extensions(self, vscode_dir: Path) -> Optional[List[str]]:
        """Load existing .vscode/extensions.json if it exists.

        Args:
            vscode_dir: Path to .vscode directory

        Returns:
            List of extension IDs or None if file doesn't exist
        """
        extensions_path = vscode_dir / "extensions.json"

        if not extensions_path.exists():
            return None

        try:
            with open(extensions_path, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("recommendations", [])
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[yellow]Warning: Could not read existing extensions.json: {e}[/yellow]")
            return None

    def _load_existing_launch_config(self, vscode_dir: Path) -> Optional[Dict[str, Any]]:
        """Load existing .vscode/launch.json if it exists.

        Args:
            vscode_dir: Path to .vscode directory

        Returns:
            Launch config dict or None if file doesn't exist
        """
        launch_path = vscode_dir / "launch.json"

        if not launch_path.exists():
            return None

        try:
            with open(launch_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[yellow]Warning: Could not read existing launch.json: {e}[/yellow]")
            return None

    def _backup_existing_configs(self, vscode_dir: Path) -> None:
        """Create backups of existing VSCode config files.

        Args:
            vscode_dir: Path to .vscode directory
        """
        for filename in ["settings.json", "extensions.json", "launch.json"]:
            filepath = vscode_dir / filename
            if filepath.exists():
                try:
                    backup_path = self.backup_manager.create_backup(filepath)
                    if backup_path:
                        self.backups[str(filepath)] = backup_path
                        console.print(f"[dim]Backed up {filename}[/dim]")

                        # Cleanup old backups, keep only 3 most recent
                        self.backup_manager.cleanup_old_backups(filepath, keep_count=3)
                except OSError as e:
                    console.print(f"[yellow]Warning: Could not backup {filename}: {e}[/yellow]")

    def _merge_settings(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Merge settings with new taking precedence.

        Args:
            existing: Existing settings
            new: New settings from setup type

        Returns:
            Merged settings dictionary
        """
        from typysetup.models.vscode_config_merge import DeepMergeStrategy

        return DeepMergeStrategy.deep_merge_dicts(existing, new)

    def _merge_extensions(self, existing: List[str], new: List[str]) -> List[str]:
        """Merge extension lists with deduplication.

        Args:
            existing: Existing extension IDs
            new: New extension IDs from setup type

        Returns:
            Deduplicated extension list
        """
        from typysetup.models.vscode_config_merge import DeepMergeStrategy

        return DeepMergeStrategy.deduplicate_extensions(existing, new)

    def _merge_launch_configs(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge launch configurations.

        Args:
            existing: Existing launch config (with configurations array)
            new: New launch config (with configurations array)

        Returns:
            Merged launch config
        """
        from typysetup.models.vscode_config_merge import DeepMergeStrategy

        existing_configs = existing.get("configurations", [])
        new_configs = new.get("configurations", [])

        merged_configs = DeepMergeStrategy.merge_launch_configurations(
            existing_configs, new_configs
        )

        return {
            "version": "0.2.0",
            "configurations": merged_configs,
        }

    def _write_settings_json(self, vscode_dir: Path, settings: Dict[str, Any]) -> None:
        """Write settings.json file with proper formatting.

        Args:
            vscode_dir: Path to .vscode directory
            settings: Settings dictionary

        Raises:
            IOError: If write fails
        """
        settings_path = vscode_dir / "settings.json"

        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            raise OSError(f"Failed to write settings.json: {e}") from e

    def _write_extensions_json(self, vscode_dir: Path, extensions: List[str]) -> None:
        """Write extensions.json file with proper formatting.

        Args:
            vscode_dir: Path to .vscode directory
            extensions: List of extension IDs

        Raises:
            IOError: If write fails
        """
        extensions_path = vscode_dir / "extensions.json"
        extensions_content = {"recommendations": extensions}

        try:
            with open(extensions_path, "w", encoding="utf-8") as f:
                json.dump(extensions_content, f, indent=4, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            raise OSError(f"Failed to write extensions.json: {e}") from e

    def _write_launch_json(self, vscode_dir: Path, launch_config: Dict[str, Any]) -> None:
        """Write launch.json file with proper formatting.

        Args:
            vscode_dir: Path to .vscode directory
            launch_config: Launch configuration dictionary

        Raises:
            IOError: If write fails
        """
        launch_path = vscode_dir / "launch.json"

        try:
            with open(launch_path, "w", encoding="utf-8") as f:
                json.dump(launch_config, f, indent=4, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            raise OSError(f"Failed to write launch.json: {e}") from e

    def _restore_from_backups(self, vscode_dir: Path) -> None:
        """Restore all config files from backups on error.

        Args:
            vscode_dir: Path to .vscode directory
        """
        for filepath_str, backup_path in self.backups.items():
            try:
                filepath = Path(filepath_str)
                self.backup_manager.restore_backup(filepath, backup_path)
                console.print(f"[yellow]Restored {filepath.name} from backup[/yellow]")
            except Exception as e:
                console.print(f"[red]Failed to restore backup: {e}[/red]")
