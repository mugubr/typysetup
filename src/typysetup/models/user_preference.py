"""UserPreference data model for preference persistence."""

import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from typysetup.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

MAX_HISTORY_ENTRIES = 20
MAX_PREFERRED_SETUP_TYPES = 10


class SetupHistoryEntry(BaseModel):
    """Record of a setup operation."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="When setup was run")
    setup_type_slug: str = Field(..., description="Setup type that was used")
    project_path: str = Field(..., description="Project directory path")
    project_name: str | None = Field(default=None, description="Project name")
    python_version: str | None = Field(default=None, description="Python version used")
    package_manager: str | None = Field(default=None, description="Package manager used")
    success: bool = Field(..., description="Whether setup succeeded")
    duration_seconds: float | None = Field(default=None, description="Setup duration")

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format with Z suffix."""
        return value.isoformat() + "Z"


class UserPreference(BaseModel):
    """Stores user preferences and setup history."""

    model_config = ConfigDict(extra="forbid")

    preferred_manager: str | None = Field(
        default="uv", description="Default package manager choice"
    )
    preferred_python_version: str | None = Field(
        default=None, description="Last used Python version"
    )
    preferred_setup_types: list[str] = Field(
        default_factory=list, description="Recently/favorite setup types"
    )
    setup_history: list[SetupHistoryEntry] = Field(
        default_factory=list, description="Past setup operations"
    )
    vscode_config_merge_mode: str = Field(
        default="merge", description="How to handle existing VSCode config"
    )
    first_run: bool = Field(default=True, description="Whether this is first run")
    version: str = Field(default="1.0", description="Preferences schema version")
    last_updated: datetime = Field(
        default_factory=utc_now, description="Last modification timestamp"
    )

    @field_serializer("last_updated")
    def serialize_last_updated(self, value: datetime) -> str:
        """Serialize datetime to ISO format with Z suffix."""
        return value.isoformat() + "Z"

    @field_validator("preferred_manager", mode="before")
    @classmethod
    def validate_manager(cls, v: str | None) -> str | None:
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
    def limit_history(cls, v: list[SetupHistoryEntry]) -> list[SetupHistoryEntry]:
        """Limit setup history to the most recent entries."""
        if v is not None and len(v) > MAX_HISTORY_ENTRIES:
            logger.warning(
                "Setup history exceeded %d entries; truncating to the most recent %d.",
                MAX_HISTORY_ENTRIES,
                MAX_HISTORY_ENTRIES,
            )
            return v[-MAX_HISTORY_ENTRIES:]
        return v

    def add_to_history(self, entry: SetupHistoryEntry) -> None:
        """Add an entry to setup history, maintaining the entry limit."""
        self.setup_history.append(entry)
        if len(self.setup_history) > MAX_HISTORY_ENTRIES:
            logger.warning(
                "Setup history exceeded %d entries; truncating to the most recent %d.",
                MAX_HISTORY_ENTRIES,
                MAX_HISTORY_ENTRIES,
            )
            self.setup_history = self.setup_history[-MAX_HISTORY_ENTRIES:]
        self.last_updated = utc_now()

    def add_preferred_setup_type(self, slug: str) -> None:
        """Add a setup type to preferred list, removing if already present."""
        if slug in self.preferred_setup_types:
            self.preferred_setup_types.remove(slug)
        self.preferred_setup_types.insert(0, slug)  # Add to beginning
        if len(self.preferred_setup_types) > MAX_PREFERRED_SETUP_TYPES:
            self.preferred_setup_types = self.preferred_setup_types[:MAX_PREFERRED_SETUP_TYPES]
        self.last_updated = utc_now()

    def update_preferred_manager(self, manager: str) -> None:
        """Update preferred package manager."""
        self.preferred_manager = manager
        self.last_updated = utc_now()

    def update_preferred_python_version(self, version: str) -> None:
        """Update preferred Python version."""
        self.preferred_python_version = version
        self.last_updated = utc_now()

    def mark_not_first_run(self) -> None:
        """Mark that user has completed first run."""
        self.first_run = False
        self.last_updated = utc_now()
