"""SetupType data model for setup type configuration."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SetupType(BaseModel):
    """Represents a predefined configuration template for a Python project type."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "FastAPI",
                "slug": "fastapi",
                "description": "Web API with FastAPI framework",
                "python_version": "3.10+",
                "supported_managers": ["uv", "poetry", "pip"],
                "vscode_settings": {
                    "python.linting.enabled": True,
                    "python.formatting.provider": "black",
                },
                "vscode_extensions": ["ms-python.python"],
                "dependencies": {
                    "core": ["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0"],
                    "dev": ["pytest>=7.0", "black>=23.0"],
                },
                "tags": ["web", "api", "async"],
            }
        },
    )

    name: str = Field(..., min_length=1, max_length=50, description="Display name")
    slug: str = Field(
        ...,
        min_length=3,
        max_length=20,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly identifier",
    )
    description: str = Field(
        ..., min_length=10, max_length=200, description="User-friendly description"
    )
    python_version: str = Field(
        ..., description="Minimum Python version required (e.g., '3.8+', '3.10-3.12')"
    )
    supported_managers: List[str] = Field(
        ..., min_items=1, description="Package managers available for this type"
    )
    vscode_settings: Optional[Dict[str, Any]] = Field(
        default=None, description="VSCode workspace settings to apply"
    )
    vscode_extensions: Optional[List[str]] = Field(
        default=None, description="VSCode extensions to recommend"
    )
    vscode_launch_config: Optional[Dict[str, Any]] = Field(
        default=None, description="VSCode debug launch configuration"
    )
    dependencies: Dict[str, List[str]] = Field(..., description="Grouped dependencies to install")
    tags: Optional[List[str]] = Field(default=None, description="Search/filter tags")
    docs_url: Optional[str] = Field(default=None, description="Link to documentation")

    @field_validator("supported_managers", mode="before")
    @classmethod
    def validate_managers(cls, v: List[str]) -> List[str]:
        """Validate that managers are one of the supported options."""
        allowed = {"uv", "pip", "poetry"}
        for manager in v:
            if manager not in allowed:
                raise ValueError(f"Invalid package manager: {manager}. Must be one of {allowed}")
        return v

    @field_validator("dependencies", mode="before")
    @classmethod
    def validate_dependencies(cls, v: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Validate that dependencies has at least 'core' group."""
        if "core" not in v:
            raise ValueError("Dependencies must have at least a 'core' group")
        if not v.get("core"):
            raise ValueError("Core dependencies cannot be empty")
        return v

    @field_validator("vscode_extensions", mode="before")
    @classmethod
    def validate_extensions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate VSCode extension IDs format (publisher.name)."""
        if v is None:
            return v
        for ext in v:
            if not ext or "." not in ext:
                raise ValueError(f"Invalid extension ID: {ext}. Format should be 'publisher.name'")
        return v

    def get_all_dependencies(self) -> List[str]:
        """Get all dependencies (core + dev)."""
        deps = self.dependencies.get("core", []).copy()
        deps.extend(self.dependencies.get("dev", []))
        return deps

    def get_core_dependencies(self) -> List[str]:
        """Get only core dependencies."""
        return self.dependencies.get("core", []).copy()

    def get_optional_dependencies(self) -> List[str]:
        """Get only optional dependencies."""
        return self.dependencies.get("optional", []).copy()

    def get_dependency_groups(self) -> List[str]:
        """Get all dependency group names in this setup type.

        Returns:
            List of group names (e.g., ['core', 'dev', 'optional'])
        """
        return list(self.dependencies.keys())

    def get_group_by_name(self, group_name: str) -> Optional[List[str]]:
        """Get dependencies for a specific group.

        Args:
            group_name: Name of the group (core, dev, optional, etc.)

        Returns:
            List of packages in the group, or None if group doesn't exist
        """
        return self.dependencies.get(group_name)

    def get_total_dependency_count(self) -> int:
        """Get total count of all dependencies across all groups.

        Returns:
            Total number of unique packages
        """
        total = 0
        for packages in self.dependencies.values():
            total += len(packages)
        return total

    def get_group_dependency_count(self, group_name: str) -> int:
        """Get count of dependencies in a specific group.

        Args:
            group_name: Name of the group

        Returns:
            Number of packages in the group, or 0 if group doesn't exist
        """
        packages = self.get_group_by_name(group_name)
        return len(packages) if packages else 0

    def filter_dependencies_by_groups(self, group_names: List[str]) -> Dict[str, List[str]]:
        """Get dependencies filtered by group names.

        Args:
            group_names: List of group names to include

        Returns:
            Dictionary with only the requested groups
        """
        result = {}
        for group_name in group_names:
            if group_name in self.dependencies:
                result[group_name] = self.dependencies[group_name].copy()
        return result

    def get_recommended_installation_order(self) -> List[str]:
        """Get groups in recommended installation order.

        Core dependencies should be installed first, then dev, then optional.

        Returns:
            Ordered list of group names
        """
        order = ["core", "dev", "optional", "typing", "testing", "docs"]
        result = []
        for group in order:
            if group in self.dependencies:
                result.append(group)
        # Add any custom groups not in the standard order
        for group in self.dependencies:
            if group not in result:
                result.append(group)
        return result

    def get_all_dependencies_by_group(
        self, include_groups: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """Get all dependencies organized by group.

        Args:
            include_groups: If provided, only include these groups.
                          If None, include all groups.

        Returns:
            Dictionary mapping group name to list of packages
        """
        if include_groups:
            return self.filter_dependencies_by_groups(include_groups)
        return {k: v.copy() for k, v in self.dependencies.items()}

    def supports_manager(self, manager: str) -> bool:
        """Check if this setup type supports a specific package manager.

        Args:
            manager: Package manager name (uv, pip, poetry)

        Returns:
            True if manager is supported
        """
        return manager in self.supported_managers

    def requires_python_version(self, version: str) -> bool:
        """Check if a Python version meets the setup type's requirements.

        Simple check: assumes constraint like "3.10+" and compares versions.

        Args:
            version: Python version to check (e.g., "3.10.5", "3.11")

        Returns:
            True if version meets requirements (basic check)
        """
        from typysetup.models.constraint import VersionConstraint

        try:
            constraint = VersionConstraint.from_string(self.python_version)
            return constraint.is_satisfied_by(version)
        except ValueError:
            # If constraint parsing fails, do simple string comparison
            return version.startswith(self.python_version.split("+")[0])

    def has_vscode_config(self) -> bool:
        """Check if this setup type has VSCode configuration.

        Returns:
            True if VSCode settings or extensions are defined
        """
        return bool(self.vscode_settings or self.vscode_extensions or self.vscode_launch_config)

    def get_extension_count(self) -> int:
        """Get count of VSCode extensions recommended.

        Returns:
            Number of extensions
        """
        return len(self.vscode_extensions) if self.vscode_extensions else 0

    def matches_tags(self, tags: List[str], match_all: bool = False) -> bool:
        """Check if setup type has specified tags.

        Args:
            tags: List of tags to search for
            match_all: If True, must have all tags. If False, need at least one.

        Returns:
            True if matching tags are found
        """
        if not self.tags:
            return False

        if match_all:
            return all(tag in self.tags for tag in tags)
        else:
            return any(tag in self.tags for tag in tags)
