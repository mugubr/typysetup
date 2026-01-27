"""UserPreference data model for preference persistence."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class SetupHistoryEntry(BaseModel):
    """Record of a setup operation."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="When setup was run")
    setup_type_slug: str = Field(..., description="Setup type that was used")
    project_path: str = Field(..., description="Project directory path")
    project_name: Optional[str] = Field(default=None, description="Project name")
    python_version: Optional[str] = Field(default=None, description="Python version used")
    package_manager: Optional[str] = Field(default=None, description="Package manager used")
    success: bool = Field(..., description="Whether setup succeeded")
    duration_seconds: Optional[float] = Field(default=None, description="Setup duration")

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format with Z suffix."""
        return value.isoformat() + "Z"


class UserPreference(BaseModel):
    """Stores user preferences and setup history."""

    model_config = ConfigDict(extra="forbid")

    preferred_manager: Optional[str] = Field(
        default="uv", description="Default package manager choice"
    )
    preferred_python_version: Optional[str] = Field(
        default=None, description="Last used Python version"
    )
    preferred_setup_types: List[str] = Field(
        default_factory=list, description="Recently/favorite setup types"
    )
    setup_history: List[SetupHistoryEntry] = Field(
        default_factory=list, description="Past setup operations"
    )
    vscode_config_merge_mode: str = Field(
        default="merge", description="How to handle existing VSCode config"
    )
    first_run: bool = Field(default=True, description="Whether this is first run")
    version: str = Field(default="1.0", description="Preferences schema version")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last modification timestamp"
    )

    @field_serializer("last_updated")
    def serialize_last_updated(self, value: datetime) -> str:
        """Serialize datetime to ISO format with Z suffix."""
        return value.isoformat() + "Z"

    @field_validator("preferred_manager", mode="before")
    @classmethod
    def validate_manager(cls, v: Optional[str]) -> Optional[str]:
        """Validate package manager is valid."""
        if v is None:
            return "uv"
        allowed = {"uv", "pip", "poetry"}
        if v not in allowed:
            raise ValueError(f"Invalid package manager: {v}. Must be one of {allowed}")
        return v

    @field_validator("vscode_config_merge_mode", mode="before")
    @classmethod
    def validate_merge_mode(cls, v: str) -> str:
        """Validate merge mode is valid."""
        if v != "merge":
            raise ValueError(f"Invalid merge mode: {v}. Only 'merge' is currently supported")
        return v

    @field_validator("setup_history", mode="before")
    @classmethod
    def limit_history(cls, v: List[SetupHistoryEntry]) -> List[SetupHistoryEntry]:
        """Limit setup history to last 20 entries."""
        if len(v) > 20:
            return v[-20:]  # Keep last 20 entries
        return v

    def add_to_history(self, entry: SetupHistoryEntry) -> None:
        """Add an entry to setup history, maintaining the 20-entry limit."""
        self.setup_history.append(entry)
        if len(self.setup_history) > 20:
            self.setup_history = self.setup_history[-20:]
        self.last_updated = datetime.utcnow()

    def add_preferred_setup_type(self, slug: str) -> None:
        """Add a setup type to preferred list, removing if already present."""
        if slug in self.preferred_setup_types:
            self.preferred_setup_types.remove(slug)
        self.preferred_setup_types.insert(0, slug)  # Add to beginning
        if len(self.preferred_setup_types) > 10:
            self.preferred_setup_types = self.preferred_setup_types[:10]
        self.last_updated = datetime.utcnow()

    def update_preferred_manager(self, manager: str) -> None:
        """Update preferred package manager."""
        self.preferred_manager = manager
        self.last_updated = datetime.utcnow()

    def update_preferred_python_version(self, version: str) -> None:
        """Update preferred Python version."""
        self.preferred_python_version = version
        self.last_updated = datetime.utcnow()

    def mark_not_first_run(self) -> None:
        """Mark that user has completed first run."""
        self.first_run = False
        self.last_updated = datetime.utcnow()
