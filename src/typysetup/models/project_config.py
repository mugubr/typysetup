"""ProjectConfiguration data model for setup result tracking."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class InstalledDependency(BaseModel):
    """Represents an installed package with version info."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Package name")
    version: str = Field(..., description="Installed version")
    installed_by: str = Field(..., description="Package manager that installed it")
    from_group: Optional[str] = Field(
        default=None, description="Dependency group (core, dev, optional)"
    )


class ProjectConfiguration(BaseModel):
    """Represents the result of a completed setup operation."""

    model_config = ConfigDict(extra="forbid")

    project_path: str = Field(..., description="Absolute path to project directory")
    setup_type_slug: str = Field(..., description="Reference to SetupType that was applied")
    python_version: str = Field(..., description="Actual Python version used")
    python_executable: str = Field(..., description="Path to Python interpreter in venv")
    package_manager: str = Field(..., description="Chosen package manager (uv, pip, poetry)")
    venv_path: str = Field(..., description="Path to virtual environment")
    installed_dependencies: List[InstalledDependency] = Field(
        default_factory=list, description="List of installed packages"
    )
    vscode_settings_merged: Optional[Dict[str, Any]] = Field(
        default=None, description="Final merged VSCode settings"
    )
    vscode_extensions_recommended: Optional[List[str]] = Field(
        default=None, description="Extensions recommended for this setup"
    )
    dependency_selections: Optional[Dict[str, Any]] = Field(
        default=None, description="User's dependency group selections (Phase 4)"
    )
    selected_extensions: Optional[List[str]] = Field(
        default=None, description="VSCode extensions selected by user (Phase 4)"
    )
    project_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Project metadata (name, description, author) (Phase 4)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Setup completion timestamp"
    )
    status: str = Field(
        default="pending",
        description="Setup status (pending, running, success, partial, failed)",
    )

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format with Z suffix."""
        return value.isoformat() + "Z"

    @field_validator("package_manager")
    @classmethod
    def validate_manager(cls, v: str) -> str:
        """Validate package manager is one of supported options."""
        allowed = {"uv", "pip", "poetry"}
        if v not in allowed:
            raise ValueError(f"Invalid package manager: {v}. Must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of allowed values."""
        allowed = {"pending", "running", "success", "partial", "failed"}
        if v not in allowed:
            raise ValueError(f"Invalid status: {v}. Must be one of {allowed}")
        return v

    def add_dependency(
        self, name: str, version: str, manager: str, group: Optional[str] = None
    ) -> None:
        """Add an installed dependency."""
        self.installed_dependencies.append(
            InstalledDependency(name=name, version=version, installed_by=manager, from_group=group)
        )

    def mark_success(self) -> None:
        """Mark setup as successful."""
        self.status = "success"

    def mark_failed(self) -> None:
        """Mark setup as failed."""
        self.status = "failed"

    def mark_partial(self) -> None:
        """Mark setup as partially complete."""
        self.status = "partial"

    def get_dependency_count(self) -> int:
        """Get count of installed dependencies."""
        return len(self.installed_dependencies)
