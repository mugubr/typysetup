# AGENTS.md - Models Module

Pydantic 2.0 data models for TyPySetup. All data validation happens here.

## Model Map

| File | Models | Purpose |
|------|--------|---------|
| `setup_type.py` | `SetupType` | Setup template definition (from YAML) |
| `dependency_group.py` | `DependencyGroup` | Group of related dependencies |
| `dependency_selection.py` | `DependencySelection` | User's selected dependencies |
| `constraint.py` | `VersionConstraint`, `ConstraintType` | Version constraint parsing |
| `project_config.py` | `ProjectConfiguration`, `InstalledDependency` | Project state persistence |
| `project_metadata.py` | `ProjectMetadata` | Project name, path, python version |
| `user_preference.py` | `UserPreference`, `SetupHistoryEntry` | User preferences persistence |
| `vscode_config.py` | `VSCodeConfiguration`, `VSCodeSettings`, `VSCodeExtension`, `VSCodeLaunchConfiguration` | VSCode settings models |
| `vscode_config_merge.py` | (utilities) | Merge logic for VSCode configs |
| `builder.py` | `SetupTypeBuilder` | Fluent builder for SetupType |

## Conventions

### Pydantic 2.0 Style
```python
from pydantic import BaseModel, ConfigDict, Field

class MyModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,           # Immutable by default
        extra="forbid",        # No unknown fields
        str_strip_whitespace=True,
    )
    
    name: str = Field(..., min_length=1)
    optional_field: str | None = None
```

### Validators
Use `@field_validator` for field-level, `@model_validator` for cross-field:
```python
@field_validator("python_version")
@classmethod
def validate_python_version(cls, v: str) -> str:
    if not v.startswith("3."):
        raise ValueError("Python 3.x required")
    return v
```

### Serialization
Models support both JSON and YAML via:
- `model.model_dump()` → dict
- `model.model_dump_json()` → JSON string
- `Model.model_validate(data)` → from dict

## Key Models

### SetupType
Primary model loaded from YAML configs:
```python
class SetupType(BaseModel):
    name: str
    display_name: str
    description: str
    python_version: str
    core_dependencies: list[DependencyGroup]  # ALWAYS installed
    optional_dependencies: list[DependencyGroup]  # User selects
    vscode_settings: VSCodeSettings
    vscode_extensions: list[VSCodeExtension]
```

### DependencyGroup
```python
class DependencyGroup(BaseModel):
    name: str
    description: str
    packages: list[str]  # e.g., ["fastapi>=0.100", "uvicorn[standard]"]
    is_core: bool = False  # Core = always selected, can't deselect
```

### ProjectConfiguration
Persisted to `.typysetup.json` in project root:
```python
class ProjectConfiguration(BaseModel):
    setup_type: str
    created_at: datetime
    python_version: str
    package_manager: str
    installed_dependencies: list[InstalledDependency]
    vscode_configured: bool
```

### UserPreference
Persisted to `~/.typysetup/preferences.json`:
```python
class UserPreference(BaseModel):
    preferred_manager: str = "uv"
    preferred_python_version: str = "3.11"
    preferred_setup_types: list[str] = []
    setup_history: list[SetupHistoryEntry] = []
```

## Anti-Patterns

1. **Never mutate frozen models** - create new instances with `model.model_copy(update={...})`
2. **Don't add fields without defaults** - breaks existing serialized data
3. **Use `Field(...)` for required fields** - explicit is better than implicit
4. **Validate at model level** - not in business logic
