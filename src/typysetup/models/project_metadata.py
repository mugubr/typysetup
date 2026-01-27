"""ProjectMetadata model for capturing user's project information."""

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectMetadata(BaseModel):
    """Captures project metadata collected from user during setup.

    Stores project name, description, author, and email for later use
    in pyproject.toml generation and configuration.
    """

    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Project name (must be valid Python package name)",
    )
    project_description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Project description (optional)",
    )
    author_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Author name (optional)",
    )
    author_email: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Author email (optional, must be valid format)",
    )

    @field_validator("project_name", mode="before")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        """Validate that project name is a valid Python package name.

        Valid names:
        - Start with letter or underscore
        - Contain only lowercase letters, numbers, and underscores
        - 3-50 characters
        - Not a Python keyword
        """
        if not v:
            raise ValueError("Project name is required")

        # Normalize to lowercase
        v = v.lower().replace("-", "_")

        # Check pattern: start with letter/underscore, contain alphanumeric/underscore
        if not re.match(r"^[a-z_][a-z0-9_]*$", v):
            raise ValueError(
                "Project name must start with a letter or underscore, "
                "and contain only lowercase letters, numbers, and underscores"
            )

        # Check Python keywords
        import keyword

        if keyword.iskeyword(v):
            raise ValueError(f"'{v}' is a Python keyword and cannot be used as a project name")

        # Check length
        if len(v) < 3:
            raise ValueError("Project name must be at least 3 characters")

        return v

    @field_validator("project_description", mode="before")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize description."""
        if v is None:
            return v
        if not v.strip():
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Description must be 500 characters or less")
        return v

    @field_validator("author_name", mode="before")
    @classmethod
    def validate_author_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize author name."""
        if v is None:
            return v
        if not v.strip():
            return None
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Author name must be 100 characters or less")
        return v

    @field_validator("author_email", mode="before")
    @classmethod
    def validate_author_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is None:
            return v
        if not v.strip():
            return None

        v = v.strip()

        # Simplified RFC 5322 pattern
        # Allows: user@domain.extension
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, v):
            raise ValueError(
                f"'{v}' is not a valid email address. " "Expected format: user@example.com"
            )

        return v

    @staticmethod
    def is_valid_package_name(name: str) -> bool:
        """Check if a name is a valid Python package name.

        Args:
            name: Name to validate

        Returns:
            True if valid, False otherwise
        """
        import keyword
        import re

        if not name or len(name) < 3:
            return False

        # Convert to lowercase for checking
        normalized = name.lower()

        # Check for hyphens (should use underscores)
        if "-" in normalized:
            return False

        # Check pattern
        if not re.match(r"^[a-z_][a-z0-9_]*$", normalized):
            return False

        # Check Python keywords
        if keyword.iskeyword(normalized):
            return False

        return True

    def sanitize_for_file_usage(self) -> dict:
        """Prepare metadata for use in file generation (e.g., pyproject.toml).

        Returns:
            Dictionary with sanitized values ready for template substitution
        """
        return {
            "project_name": self.project_name,
            "project_description": self.project_description or "",
            "author_name": self.author_name or "",
            "author_email": self.author_email or "",
        }

    def get_author_string(self) -> str:
        """Get formatted author string for pyproject.toml.

        Format: "Name <email>" or just "Name" or empty string

        Returns:
            Formatted author string
        """
        if not self.author_name:
            return ""

        if self.author_email:
            return f"{self.author_name} <{self.author_email}>"
        return self.author_name

    def __repr__(self) -> str:
        """String representation."""
        return f"ProjectMetadata(name={self.project_name}, author={self.get_author_string()})"
