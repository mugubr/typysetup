"""Utilities for filtering, comparing, and analyzing setup types."""

from typing import Any, Dict, List

from typysetup.models import SetupType


class SetupTypeComparator:
    """Compare setup types to find similarities and differences."""

    @staticmethod
    def compare_dependencies(setup_type1: SetupType, setup_type2: SetupType) -> Dict[str, Any]:
        """Compare dependencies between two setup types.

        Args:
            setup_type1: First setup type to compare
            setup_type2: Second setup type to compare

        Returns:
            Dictionary with comparison results
        """
        # Get all dependencies from both types
        deps1 = set(setup_type1.get_all_dependencies())
        deps2 = set(setup_type2.get_all_dependencies())

        common = deps1 & deps2
        unique_to_1 = deps1 - deps2
        unique_to_2 = deps2 - deps1

        return {
            "type1": setup_type1.slug,
            "type2": setup_type2.slug,
            "common_dependencies": sorted(common),
            "unique_to_first": sorted(unique_to_1),
            "unique_to_second": sorted(unique_to_2),
            "common_count": len(common),
            "unique_to_first_count": len(unique_to_1),
            "unique_to_second_count": len(unique_to_2),
            "total_different_packages": len(unique_to_1) + len(unique_to_2),
        }

    @staticmethod
    def compare_managers(setup_type1: SetupType, setup_type2: SetupType) -> Dict[str, Any]:
        """Compare package managers supported by two setup types.

        Args:
            setup_type1: First setup type
            setup_type2: Second setup type

        Returns:
            Dictionary with manager comparison results
        """
        managers1 = set(setup_type1.supported_managers)
        managers2 = set(setup_type2.supported_managers)

        common = managers1 & managers2
        only_in_1 = managers1 - managers2
        only_in_2 = managers2 - managers1

        return {
            "type1": setup_type1.slug,
            "type2": setup_type2.slug,
            "common_managers": sorted(common),
            "only_in_first": sorted(only_in_1),
            "only_in_second": sorted(only_in_2),
            "fully_compatible": len(only_in_1) == 0 and len(only_in_2) == 0,
        }

    @staticmethod
    def compare_python_versions(setup_type1: SetupType, setup_type2: SetupType) -> str:
        """Compare Python version requirements of two setup types.

        Args:
            setup_type1: First setup type
            setup_type2: Second setup type

        Returns:
            Human-readable compatibility string
        """
        v1 = setup_type1.python_version
        v2 = setup_type2.python_version

        if v1 == v2:
            return f"Both require Python {v1}"
        else:
            return f"{setup_type1.slug} requires {v1}, {setup_type2.slug} requires {v2}"


class SetupTypeFilter:
    """Filter setup types based on various criteria."""

    @staticmethod
    def filter_by_tags(
        setup_types: List[SetupType],
        tags: List[str],
        match_all: bool = False,
    ) -> List[SetupType]:
        """Filter setup types by tags.

        Args:
            setup_types: List of setup types to filter
            tags: Tags to search for
            match_all: If True, must have all tags. If False, at least one.

        Returns:
            Filtered list of setup types
        """
        result = []
        for st in setup_types:
            if st.matches_tags(tags, match_all=match_all):
                result.append(st)
        return result

    @staticmethod
    def filter_by_manager(
        setup_types: List[SetupType],
        manager: str,
    ) -> List[SetupType]:
        """Filter setup types by supported package manager.

        Args:
            setup_types: List of setup types to filter
            manager: Package manager name (uv, pip, poetry)

        Returns:
            Filtered list supporting the manager
        """
        return [st for st in setup_types if st.supports_manager(manager)]

    @staticmethod
    def filter_by_python_version(
        setup_types: List[SetupType],
        version: str,
    ) -> List[SetupType]:
        """Filter setup types by Python version compatibility.

        Args:
            setup_types: List of setup types to filter
            version: Python version to check (e.g., "3.10.5")

        Returns:
            Filtered list compatible with the version
        """
        return [st for st in setup_types if st.requires_python_version(version)]

    @staticmethod
    def filter_by_min_dependencies(
        setup_types: List[SetupType],
        min_count: int,
    ) -> List[SetupType]:
        """Filter setup types by minimum dependency count.

        Args:
            setup_types: List of setup types to filter
            min_count: Minimum number of dependencies

        Returns:
            Filtered list with at least min_count dependencies
        """
        return [st for st in setup_types if st.get_total_dependency_count() >= min_count]

    @staticmethod
    def filter_by_vscode_support(
        setup_types: List[SetupType],
    ) -> List[SetupType]:
        """Filter setup types that have VSCode configuration.

        Args:
            setup_types: List of setup types to filter

        Returns:
            Filtered list with VSCode support
        """
        return [st for st in setup_types if st.has_vscode_config()]

    @staticmethod
    def rank_by_relevance(
        setup_types: List[SetupType],
        query: str,
    ) -> List[SetupType]:
        """Rank setup types by relevance to a search query.

        Exact matches score higher than partial matches.

        Args:
            setup_types: List of setup types to rank
            query: Search query

        Returns:
            Sorted list (most relevant first)
        """
        query_lower = query.lower()
        scored = []

        for st in setup_types:
            score = 0

            # Exact match on name (highest)
            if st.name.lower() == query_lower:
                score += 100

            # Partial match on name
            elif query_lower in st.name.lower():
                score += 50

            # Exact match on slug
            elif st.slug == query_lower:
                score += 80

            # Partial match on slug
            elif query_lower in st.slug:
                score += 40

            # Partial match on description
            elif query_lower in st.description.lower():
                score += 20

            # Match on tags
            if st.tags and any(query_lower in tag.lower() for tag in st.tags):
                score += 15

            if score > 0:
                scored.append((score, st))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [st for _, st in scored]

    @staticmethod
    def apply_multiple_filters(
        setup_types: List[SetupType],
        filters: Dict[str, any],
    ) -> List[SetupType]:
        """Apply multiple filters to setup types.

        Supported filter keys:
        - tags: List[str] - filter by tags
        - manager: str - filter by package manager
        - python_version: str - filter by Python version
        - min_dependencies: int - filter by minimum dependency count
        - has_vscode: bool - filter by VSCode support

        Args:
            setup_types: List of setup types to filter
            filters: Dictionary of filters to apply

        Returns:
            Filtered list
        """
        result = setup_types

        if "tags" in filters:
            result = SetupTypeFilter.filter_by_tags(result, filters["tags"])

        if "manager" in filters:
            result = SetupTypeFilter.filter_by_manager(result, filters["manager"])

        if "python_version" in filters:
            result = SetupTypeFilter.filter_by_python_version(result, filters["python_version"])

        if "min_dependencies" in filters:
            result = SetupTypeFilter.filter_by_min_dependencies(result, filters["min_dependencies"])

        if filters.get("has_vscode"):
            result = SetupTypeFilter.filter_by_vscode_support(result)

        return result


class SetupTypeValidator:
    """Validate setup types for correctness and compatibility."""

    @staticmethod
    def validate_setup_type(setup_type: SetupType) -> Dict[str, any]:
        """Validate a setup type for correctness.

        Args:
            setup_type: Setup type to validate

        Returns:
            Dictionary with is_valid bool and lists of errors/warnings
        """
        errors = []
        warnings = []

        # Check required fields
        if not setup_type.name:
            errors.append("Setup type must have a name")

        if not setup_type.slug:
            errors.append("Setup type must have a slug")

        if not setup_type.description:
            errors.append("Setup type must have a description")

        if not setup_type.python_version:
            errors.append("Setup type must specify Python version")

        if not setup_type.supported_managers:
            errors.append("Setup type must support at least one package manager")

        if not setup_type.dependencies or "core" not in setup_type.dependencies:
            errors.append("Setup type must have core dependencies")

        if setup_type.dependencies.get("core") is not None:
            if len(setup_type.dependencies.get("core", [])) == 0:
                errors.append("Core dependencies cannot be empty")

        # Validate package managers
        valid_managers = {"uv", "pip", "poetry"}
        for manager in setup_type.supported_managers:
            if manager not in valid_managers:
                errors.append(f"Invalid package manager: {manager}")

        # Validate VSCode extensions
        if setup_type.vscode_extensions:
            for ext in setup_type.vscode_extensions:
                if "." not in ext:
                    errors.append(f"Invalid extension ID format: {ext}")

        # Warnings
        if not setup_type.tags:
            warnings.append("Setup type should have tags for filtering")

        if not setup_type.vscode_extensions:
            warnings.append("Setup type should recommend VSCode extensions")

        if not setup_type.docs_url:
            warnings.append("Setup type should link to documentation")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "slug": setup_type.slug,
        }

    @staticmethod
    def validate_python_compatibility(
        setup_type: SetupType,
        python_version: str,
    ) -> bool:
        """Check if a Python version is compatible with a setup type.

        Args:
            setup_type: Setup type to check
            python_version: Python version to validate

        Returns:
            True if version is compatible
        """
        return setup_type.requires_python_version(python_version)

    @staticmethod
    def validate_manager_compatibility(
        setup_type: SetupType,
        manager: str,
    ) -> bool:
        """Check if a package manager is supported by a setup type.

        Args:
            setup_type: Setup type to check
            manager: Package manager name

        Returns:
            True if manager is supported
        """
        return setup_type.supports_manager(manager)
