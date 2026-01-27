"""SetupTypeRegistry for managing and querying setup types."""

import logging
from typing import Any, Dict, List, Optional

from typysetup.core.config_loader import ConfigLoader
from typysetup.models import SetupType

logger = logging.getLogger(__name__)


class SetupTypeRegistry:
    """Central registry for managing setup types with filtering and querying.

    Provides methods to:
    - Register and retrieve setup types
    - Filter by tags, Python version, capabilities
    - Search across all types
    - Get statistics and validation info
    - Cache loaded setup types for performance
    """

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """Initialize registry with optional config loader.

        Args:
            config_loader: ConfigLoader instance. If None, creates one.
        """
        self.config_loader = config_loader or ConfigLoader()
        self._setup_types: Dict[str, SetupType] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy load setup types on first access."""
        if not self._loaded:
            self._load_from_config()

    def _load_from_config(self) -> None:
        """Load all setup types from config loader."""
        try:
            types = self.config_loader.load_all_setup_types()
            for setup_type in types:
                self.register(setup_type)
            logger.info(f"Registry loaded {len(self._setup_types)} setup types")
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load setup types: {e}")
            raise

    def register(self, setup_type: SetupType) -> None:
        """Register a setup type in the registry.

        Args:
            setup_type: SetupType instance to register
        """
        self._setup_types[setup_type.slug] = setup_type
        logger.debug(f"Registered setup type: {setup_type.slug}")

    def unregister(self, slug: str) -> bool:
        """Unregister a setup type from the registry.

        Args:
            slug: Setup type slug

        Returns:
            True if removed, False if not found
        """
        if slug in self._setup_types:
            del self._setup_types[slug]
            logger.debug(f"Unregistered setup type: {slug}")
            return True
        return False

    def get(self, slug: str) -> Optional[SetupType]:
        """Get a setup type by slug.

        Args:
            slug: Setup type slug

        Returns:
            SetupType instance or None if not found
        """
        self._ensure_loaded()
        return self._setup_types.get(slug)

    def get_all(self) -> List[SetupType]:
        """Get all registered setup types.

        Returns:
            List of all SetupType instances
        """
        self._ensure_loaded()
        return list(self._setup_types.values())

    def get_slugs(self) -> List[str]:
        """Get all setup type slugs.

        Returns:
            List of slug strings
        """
        self._ensure_loaded()
        return list(self._setup_types.keys())

    def find_by_tag(self, tag: str) -> List[SetupType]:
        """Find setup types by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of SetupType instances with the tag
        """
        self._ensure_loaded()
        return [st for st in self._setup_types.values() if st.tags and tag in st.tags]

    def find_by_tags(self, tags: List[str], match_all: bool = False) -> List[SetupType]:
        """Find setup types by multiple tags.

        Args:
            tags: List of tags to search for
            match_all: If True, must have all tags. If False, at least one.

        Returns:
            List of SetupType instances matching tags
        """
        self._ensure_loaded()
        result = []
        for st in self._setup_types.values():
            if st.matches_tags(tags, match_all=match_all):
                result.append(st)
        return result

    def find_by_python_version(self, version: str) -> List[SetupType]:
        """Find setup types compatible with a Python version.

        Args:
            version: Python version to check (e.g., "3.10.5")

        Returns:
            List of SetupType instances supporting the version
        """
        self._ensure_loaded()
        return [st for st in self._setup_types.values() if st.requires_python_version(version)]

    def find_by_manager(self, manager: str) -> List[SetupType]:
        """Find setup types supporting a package manager.

        Args:
            manager: Package manager name (uv, pip, poetry)

        Returns:
            List of SetupType instances supporting the manager
        """
        self._ensure_loaded()
        return [st for st in self._setup_types.values() if st.supports_manager(manager)]

    def find_by_capability(self, capability: str) -> List[SetupType]:
        """Find setup types with a specific capability.

        Capabilities are determined by tags. This is an alias for find_by_tag.

        Args:
            capability: Capability tag (e.g., "async", "web", "ml")

        Returns:
            List of SetupType instances with the capability
        """
        return self.find_by_tag(capability)

    def search(self, query: str) -> List[SetupType]:
        """Search setup types by name, description, or slug.

        Args:
            query: Search query string

        Returns:
            List of matching SetupType instances
        """
        self._ensure_loaded()
        query_lower = query.lower()
        results = []

        for st in self._setup_types.values():
            # Check if query matches name, slug, or description
            if (
                query_lower in st.name.lower()
                or query_lower in st.slug.lower()
                or query_lower in st.description.lower()
            ):
                results.append(st)

        return results

    def validate_all(self) -> List[str]:
        """Validate all registered setup types.

        Returns:
            List of validation errors (empty if all valid)
        """
        self._ensure_loaded()
        errors = []

        for slug, setup_type in self._setup_types.items():
            try:
                # Basic validation by trying to access properties
                if not setup_type.name:
                    errors.append(f"{slug}: Missing name")
                if not setup_type.dependencies.get("core"):
                    errors.append(f"{slug}: Missing core dependencies")
                if not setup_type.supported_managers:
                    errors.append(f"{slug}: No supported managers")
            except Exception as e:
                errors.append(f"{slug}: {str(e)}")

        return errors

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about registered setup types.

        Returns:
            Dictionary with stats (total types, total packages, etc.)
        """
        self._ensure_loaded()

        total_types = len(self._setup_types)
        total_packages = 0
        all_tags = set()
        manager_count: Dict[str, int] = {}

        for st in self._setup_types.values():
            total_packages += st.get_total_dependency_count()

            if st.tags:
                all_tags.update(st.tags)

            for manager in st.supported_managers:
                manager_count[manager] = manager_count.get(manager, 0) + 1

        avg_dependencies = total_packages / total_types if total_types > 0 else 0

        return {
            "total_types": total_types,
            "total_packages": total_packages,
            "average_dependencies_per_type": round(avg_dependencies, 2),
            "unique_tags": len(all_tags),
            "tags": sorted(all_tags),
            "manager_support": manager_count,
        }

    def clear_cache(self) -> None:
        """Clear the registry cache and reload from config."""
        self._setup_types.clear()
        self._loaded = False
        logger.debug("Registry cache cleared")

    def __len__(self) -> int:
        """Get count of registered setup types."""
        self._ensure_loaded()
        return len(self._setup_types)

    def __contains__(self, slug: str) -> bool:
        """Check if a setup type is registered."""
        self._ensure_loaded()
        return slug in self._setup_types

    def __getitem__(self, slug: str) -> SetupType:
        """Get setup type by slug using bracket notation."""
        st = self.get(slug)
        if st is None:
            raise KeyError(f"Setup type not found: {slug}")
        return st

    def __iter__(self):
        """Iterate over all setup types."""
        self._ensure_loaded()
        return iter(self._setup_types.values())
