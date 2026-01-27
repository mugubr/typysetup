"""Data models for TyPySetup."""

from .builder import SetupTypeBuilder
from .constraint import ConstraintType, VersionConstraint
from .dependency_group import DependencyGroup
from .dependency_selection import DependencySelection
from .project_config import InstalledDependency, ProjectConfiguration
from .project_metadata import ProjectMetadata
from .setup_type import SetupType
from .user_preference import SetupHistoryEntry, UserPreference
from .vscode_config import (
    VSCodeConfiguration,
    VSCodeExtension,
    VSCodeLaunchConfiguration,
    VSCodeSettings,
)

__all__ = [
    "SetupType",
    "ProjectConfiguration",
    "InstalledDependency",
    "UserPreference",
    "SetupHistoryEntry",
    "DependencyGroup",
    "VersionConstraint",
    "ConstraintType",
    "SetupTypeBuilder",
    "DependencySelection",
    "ProjectMetadata",
    "VSCodeSettings",
    "VSCodeExtension",
    "VSCodeLaunchConfiguration",
    "VSCodeConfiguration",
]
