"""Version constraint model for validating Python and package versions."""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConstraintType(str, Enum):
    """Types of version constraints."""

    MINIMUM = "minimum"  # >= X.Y (e.g., "3.10+")
    MAXIMUM = "maximum"  # <= X.Y
    EXACT = "exact"  # == X.Y
    RANGE = "range"  # X.Y to Z.W (e.g., "3.8-3.11")
    GREATER_THAN = "greater_than"  # > X.Y
    LESS_THAN = "less_than"  # < X.Y


class VersionConstraint(BaseModel):
    """Represents a version constraint for Python or packages.

    Parses and validates version specifications like:
    - "3.10+" (minimum version)
    - "3.8-3.11" (version range)
    - ">=3.9" (greater than or equal)
    - "3.11" (exact version)
    """

    model_config = ConfigDict(extra="forbid")

    constraint_str: str = Field(..., description="Original constraint string")
    constraint_type: ConstraintType = Field(..., description="Type of constraint")
    min_version: Optional[str] = Field(default=None, description="Minimum version if applicable")
    max_version: Optional[str] = Field(default=None, description="Maximum version if applicable")

    @staticmethod
    def parse_version_string(version_str: str) -> tuple[int, ...]:
        """Parse a version string into tuple of integers.

        Args:
            version_str: Version like "3.10", "3.10.5", etc.

        Returns:
            Tuple of version parts as integers

        Raises:
            ValueError: If version format is invalid
        """
        try:
            parts = version_str.split(".")
            if not parts or not all(p.isdigit() for p in parts):
                raise ValueError(f"Invalid version format: {version_str}")
            return tuple(int(p) for p in parts)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid version format: {version_str}") from e

    @classmethod
    def from_string(cls, constraint_str: str) -> "VersionConstraint":
        """Parse a constraint string and create VersionConstraint instance.

        Supported formats:
        - "3.10+" → minimum version
        - "3.8-3.11" → range
        - ">=3.9" → greater than or equal
        - "<=3.11" → less than or equal
        - ">3.8" → greater than
        - "<3.12" → less than
        - "==3.10" → exact
        - "3.10" → exact

        Args:
            constraint_str: Constraint string

        Returns:
            VersionConstraint instance

        Raises:
            ValueError: If constraint format is unrecognized
        """
        constraint_str = constraint_str.strip()

        # Check for "X.Y+" format (minimum)
        if match := re.match(r"^(\d+\.\d+)\+$", constraint_str):
            min_version = match.group(1)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.MINIMUM,
                min_version=min_version,
            )

        # Check for "X.Y-A.B" format (range)
        if match := re.match(r"^(\d+\.\d+)-(\d+\.\d+)$", constraint_str):
            min_version = match.group(1)
            max_version = match.group(2)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.RANGE,
                min_version=min_version,
                max_version=max_version,
            )

        # Check for ">=" format
        if match := re.match(r"^>=(\d+\.\d+)$", constraint_str):
            min_version = match.group(1)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.MINIMUM,
                min_version=min_version,
            )

        # Check for "<=" format
        if match := re.match(r"^<=(\d+\.\d+)$", constraint_str):
            max_version = match.group(1)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.MAXIMUM,
                max_version=max_version,
            )

        # Check for ">" format
        if match := re.match(r"^>(\d+\.\d+)$", constraint_str):
            min_version = match.group(1)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.GREATER_THAN,
                min_version=min_version,
            )

        # Check for "<" format
        if match := re.match(r"^<(\d+\.\d+)$", constraint_str):
            max_version = match.group(1)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.LESS_THAN,
                max_version=max_version,
            )

        # Check for "==" format
        if match := re.match(r"^==(\d+\.\d+)$", constraint_str):
            min_version = match.group(1)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.EXACT,
                min_version=min_version,
            )

        # Check for plain version (e.g., "3.10")
        if match := re.match(r"^(\d+\.\d+)$", constraint_str):
            min_version = match.group(1)
            return cls(
                constraint_str=constraint_str,
                constraint_type=ConstraintType.EXACT,
                min_version=min_version,
            )

        raise ValueError(
            f"Unrecognized constraint format: {constraint_str}. "
            "Try: '3.10+', '3.8-3.11', '>=3.9', '<=3.11', '3.10'"
        )

    @field_validator("constraint_str")
    @classmethod
    def validate_constraint_str(cls, v: str) -> str:
        """Validate that constraint string is non-empty."""
        if not v.strip():
            raise ValueError("Constraint string cannot be empty")
        return v.strip()

    def is_satisfied_by(self, version: str) -> bool:
        """Check if a version satisfies this constraint.

        Args:
            version: Version to check (e.g., "3.10.5")

        Returns:
            True if version satisfies constraint, False otherwise
        """
        try:
            version_parts = self.parse_version_string(version)
        except ValueError:
            return False

        if self.constraint_type == ConstraintType.EXACT:
            if self.min_version:
                constraint_parts = self.parse_version_string(self.min_version)
                return version_parts == constraint_parts[: len(version_parts)]
            return False

        if self.constraint_type == ConstraintType.MINIMUM:
            if self.min_version:
                min_parts = self.parse_version_string(self.min_version)
                return version_parts >= min_parts
            return False

        if self.constraint_type == ConstraintType.GREATER_THAN:
            if self.min_version:
                min_parts = self.parse_version_string(self.min_version)
                return version_parts > min_parts
            return False

        if self.constraint_type == ConstraintType.MAXIMUM:
            if self.max_version:
                max_parts = self.parse_version_string(self.max_version)
                return version_parts <= max_parts
            return False

        if self.constraint_type == ConstraintType.LESS_THAN:
            if self.max_version:
                max_parts = self.parse_version_string(self.max_version)
                return version_parts < max_parts
            return False

        if self.constraint_type == ConstraintType.RANGE:
            if self.min_version and self.max_version:
                min_parts = self.parse_version_string(self.min_version)
                max_parts = self.parse_version_string(self.max_version)
                return min_parts <= version_parts <= max_parts
            return False

        return False

    def get_readable_format(self) -> str:
        """Get human-readable format of the constraint.

        Returns:
            Formatted constraint string (e.g., "Python 3.10 or later")
        """
        if self.constraint_type == ConstraintType.EXACT:
            return f"Python {self.min_version}"
        elif self.constraint_type == ConstraintType.MINIMUM:
            return f"Python {self.min_version} or later"
        elif self.constraint_type == ConstraintType.GREATER_THAN:
            return f"Python later than {self.min_version}"
        elif self.constraint_type == ConstraintType.MAXIMUM:
            return f"Python {self.max_version} or earlier"
        elif self.constraint_type == ConstraintType.LESS_THAN:
            return f"Python earlier than {self.max_version}"
        elif self.constraint_type == ConstraintType.RANGE:
            return f"Python {self.min_version} to {self.max_version}"
        return self.constraint_str

    def __str__(self) -> str:
        """String representation."""
        return self.get_readable_format()
