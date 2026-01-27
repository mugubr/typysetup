"""Configuration loader for setup type YAML files."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import yaml
from pydantic import ValidationError

from typysetup.models import SetupType

if TYPE_CHECKING:
    from typysetup.core.setup_type_registry import SetupTypeRegistry

logger = logging.getLogger(__name__)


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""

    pass


class ConfigLoader:
    """Load and validate setup type YAML configurations."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize ConfigLoader.

        Args:
            config_dir: Path to directory containing YAML config files.
                       If None, uses package configs directory.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "configs"

        if not config_dir.exists():
            raise ConfigLoadError(f"Config directory does not exist: {config_dir}")

        self.config_dir = config_dir
        self._cache: Dict[str, SetupType] = {}
        self._registry: Optional[SetupTypeRegistry] = None

    def load_setup_type(self, slug: str) -> SetupType:
        """
        Load a single setup type configuration.

        Args:
            slug: Setup type slug (e.g., 'fastapi')

        Returns:
            SetupType instance

        Raises:
            ConfigLoadError: If file not found or validation fails
        """
        # Return from cache if already loaded
        if slug in self._cache:
            return self._cache[slug]

        yaml_path = self.config_dir / f"{slug}.yaml"

        if not yaml_path.exists():
            raise ConfigLoadError(f"Setup type not found: {slug}")

        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                raise ConfigLoadError(f"Empty YAML file: {yaml_path}")

            setup_type = SetupType(**data)
            self._cache[slug] = setup_type
            logger.info(f"Loaded setup type: {slug}")
            return setup_type

        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Invalid YAML in {slug}.yaml: {e}") from e
        except ValidationError as e:
            raise ConfigLoadError(f"Invalid setup type configuration {slug}: {e}") from e
        except Exception as e:
            raise ConfigLoadError(f"Error loading setup type {slug}: {e}") from e

    def load_all_setup_types(self) -> List[SetupType]:
        """
        Load all available setup type configurations.

        Returns:
            List of SetupType instances

        Raises:
            ConfigLoadError: If any configuration is invalid
        """
        setup_types = []
        yaml_files = sorted(self.config_dir.glob("*.yaml"))

        if not yaml_files:
            raise ConfigLoadError(f"No YAML files found in {self.config_dir}")

        for yaml_file in yaml_files:
            slug = yaml_file.stem
            try:
                setup_type = self.load_setup_type(slug)
                setup_types.append(setup_type)
            except ConfigLoadError as e:
                logger.error(f"Failed to load {slug}: {e}")
                # Continue loading other types, but track failure
                pass

        if not setup_types:
            raise ConfigLoadError("No valid setup types found")

        logger.info(f"Loaded {len(setup_types)} setup types")
        return setup_types

    def get_setup_type_by_slug(self, slug: str) -> Optional[SetupType]:
        """
        Get setup type by slug, returning None if not found.

        Args:
            slug: Setup type slug

        Returns:
            SetupType instance or None if not found
        """
        try:
            return self.load_setup_type(slug)
        except ConfigLoadError:
            return None

    def list_setup_type_slugs(self) -> List[str]:
        """
        Get list of all available setup type slugs.

        Returns:
            List of slug strings
        """
        yaml_files = sorted(self.config_dir.glob("*.yaml"))
        return [f.stem for f in yaml_files]

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._cache.clear()
        self._registry = None
        logger.debug("Cleared configuration cache")

    def get_registry(self) -> "SetupTypeRegistry":
        """Get or create the SetupTypeRegistry.

        Returns:
            SetupTypeRegistry instance populated with all setup types

        Raises:
            ConfigLoadError: If registry cannot be created
        """
        if self._registry is None:
            from typysetup.core.setup_type_registry import SetupTypeRegistry

            self._registry = SetupTypeRegistry(config_loader=self)

        return self._registry

    def validate_all_configs(self) -> List[str]:
        """Validate all loaded configuration files.

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        setup_types = self.load_all_setup_types()

        for setup_type in setup_types:
            from typysetup.core.setup_type_utils import SetupTypeValidator

            result = SetupTypeValidator.validate_setup_type(setup_type)
            if not result["is_valid"]:
                for error in result["errors"]:
                    errors.append(f"{setup_type.slug}: {error}")

        return errors

    def get_setup_type_stats(self) -> Dict[str, any]:
        """Get statistics about all setup types.

        Returns:
            Dictionary with stats across all setup types
        """
        registry = self.get_registry()
        return registry.get_stats()

    def search_setup_types(self, query: str) -> List[SetupType]:
        """Search setup types by name, slug, or description.

        Args:
            query: Search query string

        Returns:
            List of matching setup types
        """
        registry = self.get_registry()
        return registry.search(query)
