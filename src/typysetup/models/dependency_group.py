"""DependencyGroup model for organizing dependencies by category."""

import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DependencyGroup(BaseModel):
    """Represents a group of related dependencies within a setup type.

    Groups can be: core (mandatory), dev (development), optional (nice-to-have),
    or custom groups like testing, typing, documentation, etc.
    """

    model_config = ConfigDict(extra="forbid")

    group_name: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern=r"^[a-z0-9-]+$",
        description="Group identifier (core, dev, optional, testing, etc.)",
    )
    packages: List[str] = Field(
        default=..., min_length=1, description="Package specifications (e.g., fastapi>=0.104.0)"
    )
    description: Optional[str] = Field(
        default=None, max_length=200, description="Human-readable description of the group"
    )
    required: bool = Field(
        default=False, description="Whether this group is mandatory for the setup"
    )
    hidden: bool = Field(
        default=False,
        description="Whether to show in interactive selection prompts",
    )

    @field_validator("packages", mode="before")
    @classmethod
    def validate_packages(cls, v: List[str]) -> List[str]:
        """Validate that all packages have valid pip format."""
        if not v:
            raise ValueError("Package list cannot be empty")

        for pkg in v:
            # Check basic pip format: name or name[extras] or name>=version
            # Pattern: alphanumeric/underscore/hyphen, optional extras, optional version spec
            if not re.match(r"^[a-zA-Z0-9_\-\.]+(\[[a-zA-Z0-9_,\-]+\])?([><=!~\*\+]+.+)?$", pkg):
                raise ValueError(
                    f"Invalid package format: {pkg}. "
                    "Expected pip format like 'package', 'package[extra]', or 'package>=1.0'"
                )
        return v

    def get_package_names(self) -> List[str]:
        """Get package names without version specifications.

        Returns:
            List of package names only (no versions or extras)
        """
        names = []
        for pkg in self.packages:
            # Extract name part before [, >, <, =, !, ~, or space
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)", pkg)
            if match:
                names.append(match.group(1))
        return names

    def get_package_count(self) -> int:
        """Get total number of packages in this group.

        Returns:
            Number of packages
        """
        return len(self.packages)

    def filter_by_version_spec(self, spec: str) -> List[str]:
        """Filter packages by version specification operator.

        Args:
            spec: Version spec operator (e.g., ">=", "==", "<")

        Returns:
            List of packages matching the spec
        """
        return [pkg for pkg in self.packages if spec in pkg]

    def get_readable_description(self) -> str:
        """Get human-readable description of the group.

        Returns:
            Description or generated default if not provided
        """
        if self.description:
            return self.description

        # Generate default description based on group name
        defaults = {
            "core": "Core dependencies required for basic functionality",
            "dev": "Development and testing dependencies",
            "optional": "Optional dependencies for enhanced functionality",
            "testing": "Testing and quality assurance tools",
            "typing": "Type checking and validation tools",
            "docs": "Documentation generation tools",
        }
        return defaults.get(self.group_name, f"{self.group_name.title()} dependencies")

    def to_installable_format(self) -> str:
        """Get packages in a format suitable for passing to package managers.

        Returns:
            Space-separated packages string
        """
        return " ".join(self.packages)
