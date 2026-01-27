# TyPySetup Architecture Documentation

**Version**: 0.1.0
**Date**: 2026-01-25
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [System Architecture](#system-architecture)
4. [Module Organization](#module-organization)
5. [Data Flow](#data-flow)
6. [Design Patterns](#design-patterns)
7. [Key Components](#key-components)
8. [Configuration System](#configuration-system)
9. [Error Handling & Rollback](#error-handling--rollback)
10. [Testing Strategy](#testing-strategy)
11. [Performance Considerations](#performance-considerations)
12. [Security Considerations](#security-considerations)

---

## Overview

TyPySetup is a CLI tool built with Typer that automates Python environment setup for VSCode projects. The architecture follows a modular, layered design with clear separation of concerns.

### Core Goals

- **Simplicity**: Easy to use, minimal configuration required
- **Reliability**: Atomic operations with automatic rollback
- **Extensibility**: Easy to add new setup types and features
- **Testability**: High test coverage with isolated components
- **Performance**: Fast setup times (<5 minutes target)

---

## Design Principles

### 1. Separation of Concerns

```
┌─────────────────┐
│  CLI Commands   │  ← User interaction (Typer)
├─────────────────┤
│  Core Logic     │  ← Business logic (pure Python)
├─────────────────┤
│  Data Models    │  ← Data validation (Pydantic)
├─────────────────┤
│  Utilities      │  ← Cross-cutting concerns
└─────────────────┘
```

### 2. Configuration-Driven

- Setup types defined in YAML files
- No hardcoded project templates in code
- Easy to add new setup types without code changes

### 3. Atomic Operations

- All-or-nothing setup process
- Automatic rollback on failure
- No partial/broken configurations left behind

### 4. Minimal Dependencies

- Core: Typer, Pydantic, PyYAML, Rich, Questionary
- No heavy frameworks (Django, FastAPI, etc.)
- Built-in Python modules where possible (venv, pathlib)

---

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        User Interface                         │
│  (Typer CLI + Rich/Questionary for interactive prompts)      │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│                      Command Layer                             │
│  ┌──────────┐  ┌─────────────┐  ┌────────────┐               │
│  │  setup   │  │ preferences │  │   config   │  ...          │
│  └──────────┘  └─────────────┘  └────────────┘               │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                           │
│            SetupOrchestrator (coordinates phases)              │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│                      Core Services                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │ConfigLoader │  │ VenvManager  │  │DependencyInstaller│     │
│  └─────────────┘  └──────────────┘  └──────────────────┘     │
│  ┌─────────────────────┐  ┌──────────────────┐               │
│  │VSCodeConfigGenerator│  │PreferenceManager │               │
│  └─────────────────────┘  └──────────────────┘               │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│                       Data Layer                               │
│  ┌────────────┐  ┌──────────────────┐  ┌──────────────┐      │
│  │ SetupType  │  │ProjectConfiguration│ │UserPreference│      │
│  │  (YAML)    │  │      (JSON)        │  │   (JSON)    │      │
│  └────────────┘  └──────────────────┘  └──────────────┘      │
└────────────────────────────────────────────────────────────────┘
```

---

## Module Organization

### Directory Structure

```
src/typysetup/
├── main.py                    # Entry point, Typer app
├── models/                    # Pydantic data models
│   ├── setup_type.py          # SetupType entity
│   ├── project_config.py      # ProjectConfiguration entity
│   ├── user_preference.py     # UserPreference entity
│   ├── dependency_group.py    # Dependency grouping
│   └── ...
├── commands/                  # CLI command implementations
│   └── setup_orchestrator.py # Main setup flow orchestration
├── core/                      # Business logic (framework-agnostic)
│   ├── config_loader.py       # Load & validate YAML configs
│   ├── venv_manager.py        # Virtual environment creation
│   ├── dependency_installer.py # Package installation (uv/pip/poetry)
│   ├── vscode_config_generator.py # VSCode config generation
│   ├── preference_manager.py  # User preference persistence
│   └── project_config_manager.py # Project config management
├── utils/                     # Utilities and helpers
│   ├── ui.py                  # Rich/Questionary UI components
│   ├── paths.py               # Cross-platform path handling
│   └── validators.py          # Custom validators
└── configs/                   # Setup type YAML templates
    ├── fastapi.yaml
    ├── django.yaml
    ├── data-science.yaml
    ├── cli-tool.yaml
    ├── async-realtime.yaml
    └── ml-ai.yaml
```

### Module Responsibilities

| Module | Responsibility | Dependencies |
|--------|----------------|--------------|
| `main.py` | CLI app definition, command routing | Typer, commands/* |
| `models/` | Data validation, serialization | Pydantic |
| `commands/` | User interaction, command logic | Typer, core/*, utils/ui |
| `core/` | Business logic, pure functions | models/*, minimal external |
| `utils/` | Cross-cutting concerns | Rich, Questionary |
| `configs/` | YAML configuration files | None (data) |

---

## Data Flow

### Setup Command Flow

```
1. User Input
   ├─> typysetup setup /path/to/project
   │
2. Load Available Setup Types
   ├─> ConfigLoader.load_all_setup_types()
   ├─> Parse YAML files
   └─> Validate with Pydantic
   │
3. Interactive Prompts
   ├─> Select setup type (Questionary)
   ├─> Select package manager
   └─> Confirm choices
   │
4. Create RollbackContext
   ├─> Register cleanup actions for each phase
   │
5. Phase 1: Virtual Environment
   ├─> VenvManager.create_venv()
   ├─> Register rollback: delete venv
   │
6. Phase 2: Install Dependencies
   ├─> DependencyInstaller.install()
   ├─> Execute via subprocess (uv/pip/poetry)
   ├─> Register rollback: remove packages
   │
7. Phase 3: VSCode Configuration
   ├─> VSCodeConfigGenerator.generate()
   ├─> Merge with existing settings
   ├─> Register rollback: restore previous config
   │
8. Phase 4: Persist Configuration
   ├─> ProjectConfigManager.save_config()
   ├─> PreferenceManager.update_history()
   │
9. Display Summary
   └─> Show success message with next steps
```

### Error Flow

```
Exception at any phase
   │
   ├─> RollbackContext.__exit__() triggered
   │   ├─> Execute cleanup actions in LIFO order
   │   ├─> Log rollback progress
   │   └─> Restore previous state
   │
   └─> Display error message with troubleshooting hints
```

---

## Design Patterns

### 1. Repository Pattern (ConfigLoader)

**Purpose**: Centralize YAML configuration loading and validation.

```python
class ConfigLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir

    def load_setup_type(self, slug: str) -> SetupType:
        """Load single setup type by slug"""
        yaml_path = self.config_dir / f"{slug}.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        return SetupType(**data)  # Pydantic validation

    def load_all_setup_types(self) -> list[SetupType]:
        """Load all available setup types"""
        # Implementation
```

**Benefits**:
- Single source of truth for configuration loading
- Easy to add caching layer later
- Testable with mock filesystem

### 2. Context Manager Pattern (RollbackContext)

**Purpose**: Automatic cleanup on failure (RAII pattern).

```python
class RollbackContext:
    def __init__(self):
        self.undo_stack = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Execute cleanup in LIFO order
            for undo in reversed(self.undo_stack):
                try:
                    undo()
                except Exception as e:
                    logger.error(f"Rollback failed: {e}")
        return False  # Don't suppress exceptions
```

**Usage**:
```python
with RollbackContext() as ctx:
    venv = create_venv(path)
    ctx.register_cleanup(lambda: shutil.rmtree(venv.path))

    install_deps(venv)
    # If exception, venv is automatically deleted
```

### 3. Strategy Pattern (DependencyInstaller)

**Purpose**: Support multiple package managers with common interface.

```python
class DependencyInstaller:
    def install(self, venv, deps, manager='uv'):
        if manager == 'uv':
            return self._install_uv(venv, deps)
        elif manager == 'poetry':
            return self._install_poetry(venv, deps)
        else:
            return self._install_pip(venv, deps)

    def _install_uv(self, venv, deps):
        # UV-specific implementation

    def _install_pip(self, venv, deps):
        # Pip-specific implementation
```

### 4. Builder Pattern (Pydantic Models)

**Purpose**: Flexible object construction with validation.

```python
from pydantic import BaseModel, validator

class SetupType(BaseModel):
    name: str
    slug: str
    python_version: str
    dependencies: Dict[str, List[str]]

    @validator('slug')
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Invalid slug format')
        return v
```

### 5. Facade Pattern (SetupOrchestrator)

**Purpose**: Simplify complex multi-step setup process.

```python
class SetupOrchestrator:
    def run_setup_wizard(self, project_path):
        # Coordinates all setup phases
        setup_type = self.prompt_setup_type()
        manager = self.prompt_package_manager()

        with RollbackContext() as ctx:
            venv = self.create_venv(project_path)
            ctx.register_cleanup(...)

            self.install_deps(venv, setup_type, manager)
            self.generate_vscode_config(project_path, setup_type)
            self.save_preferences()

        return project_config
```

---

## Key Components

### ConfigLoader

**Responsibility**: Load and validate setup type configurations.

**Key Methods**:
- `load_setup_type(slug: str) -> SetupType`
- `load_all_setup_types() -> List[SetupType]`
- `get_config_dir() -> Path`

**Error Handling**:
- Invalid YAML → `YAMLError` with line number
- Validation failure → `ValidationError` with field details
- Missing file → `FileNotFoundError` with helpful message

### VenvManager

**Responsibility**: Create and manage Python virtual environments.

**Key Methods**:
- `create_venv(path: Path, python_version: str) -> VirtualEnvironment`
- `get_python_executable(venv_path: Path) -> Path`
- `detect_python_version() -> str`

**Cross-Platform Support**:
```python
def get_python_executable(self, venv_path: Path) -> Path:
    if sys.platform == 'win32':
        return venv_path / 'Scripts' / 'python.exe'
    return venv_path / 'bin' / 'python'
```

### DependencyInstaller

**Responsibility**: Install packages using uv/pip/poetry.

**Key Methods**:
- `install(venv, dependencies, manager) -> InstallResult`
- `_install_uv(venv, deps) -> subprocess.CompletedProcess`
- `_install_pip(venv, deps) -> subprocess.CompletedProcess`
- `_install_poetry(venv, deps) -> subprocess.CompletedProcess`

**Implementation Details**:
- Uses `subprocess.run()` for all managers
- Captures stdout/stderr for error reporting
- Parses output to detect success/failure
- Retries on network errors (configurable)

### VSCodeConfigGenerator

**Responsibility**: Generate and merge VSCode configuration files.

**Key Methods**:
- `generate_settings(setup_type) -> Dict`
- `generate_extensions(setup_type) -> List[str]`
- `merge_settings(existing, new) -> Dict`

**Merge Strategy**:
- Objects: Deep merge, new values take precedence
- Arrays: Concatenate and deduplicate
- Primitives: New value overwrites

---

## Configuration System

### Setup Type YAML Schema

```yaml
name: FastAPI                    # Display name
slug: fastapi                    # Unique identifier
description: "FastAPI web framework"
python_version: "3.10+"          # Minimum version

supported_managers:              # Available package managers
  - uv
  - poetry
  - pip

vscode_settings:                 # VSCode workspace settings
  python.linting.enabled: true
  python.formatting.provider: "black"

vscode_extensions:               # VSCode extension recommendations
  - ms-python.python
  - charliermarsh.ruff

dependencies:                    # Grouped dependencies
  core:                          # Always installed
    - fastapi>=0.104.0
    - uvicorn[standard]>=0.24.0
  dev:                           # Development (optional)
    - pytest>=7.0
    - black>=23.0
  optional:                      # User chooses
    - sqlalchemy>=2.0
    - redis>=5.0

tags:                            # Search/filter tags
  - web
  - api
  - async

docs_url: "https://fastapi.tiangolo.com"
```

### User Preferences Schema

```json
{
  "preferred_manager": "uv",
  "preferred_python_version": "3.11",
  "preferred_setup_types": ["fastapi", "data-science"],
  "setup_history": [
    {
      "timestamp": "2026-01-25T10:30:00Z",
      "setup_type_slug": "fastapi",
      "project_path": "/home/user/my-api",
      "success": true,
      "duration_seconds": 42
    }
  ],
  "vscode_config_merge_mode": "merge",
  "first_run": false,
  "version": "1.0",
  "last_updated": "2026-01-25T10:30:00Z"
}
```

---

## Error Handling & Rollback

### Error Hierarchy

```
TyPySetupError (base)
├── ConfigurationError
│   ├── InvalidYAMLError
│   └── ValidationError
├── VenvCreationError
│   ├── PythonNotFoundError
│   └── PermissionError
├── DependencyInstallationError
│   ├── PackageNotFoundError
│   ├── NetworkError
│   └── ManagerNotFoundError
└── VSCodeConfigError
    ├── InvalidJSONError
    └── MergeConflictError
```

### Rollback Mechanism

**Phases and Cleanup Actions**:

| Phase | Action | Rollback |
|-------|--------|----------|
| Venv Creation | Create venv directory | `shutil.rmtree(venv_path)` |
| Dependency Install | Install packages | Delete venv (contains packages) |
| VSCode Config | Write settings.json | Restore backup |
| Preferences | Update history | Remove last entry |

**LIFO Execution**:
- Cleanup actions execute in reverse order
- Idempotent (safe to call multiple times)
- Logged for debugging

---

## Testing Strategy

### Test Pyramid

```
        ┌─────────────┐
        │   E2E (5%)  │  ← Manual testing, full workflow
        ├─────────────┤
        │ Integration │  ← Multiple components, mocked I/O
        │    (25%)    │
        ├─────────────┤
        │    Unit     │  ← Single component, full coverage
        │    (70%)    │
        └─────────────┘
```

### Unit Tests

- **Coverage Target**: 80%+
- **Mocking**: subprocess, filesystem operations
- **Focus**: Business logic, edge cases

**Example**:
```python
def test_venv_creation(tmp_path, monkeypatch):
    """Test virtual environment creation"""
    manager = VenvManager()
    venv = manager.create_venv(tmp_path / "venv")

    assert venv.path.exists()
    assert venv.python.exists()
```

### Integration Tests

- **Scope**: Multi-component flows
- **Mocking**: External services only (PyPI, subprocess)
- **Focus**: Component interaction

**Example**:
```python
def test_setup_flow(cli_runner, tmp_path, mock_subprocess):
    """Test complete setup flow"""
    result = cli_runner.invoke(app, ['setup', str(tmp_path)])

    assert result.exit_code == 0
    assert "Setup complete" in result.stdout
```

---

## Performance Considerations

### Optimization Strategies

1. **Package Manager Selection**:
   - uv: 10-100x faster than pip
   - Default to uv, fallback to pip

2. **Parallel Operations**:
   - YAML loading can be parallelized
   - Dependency installation is sequential (package manager limitation)

3. **Caching**:
   - ConfigLoader caches loaded setup types
   - Package managers use local caches (~/.cache/pip, ~/.cache/uv)

4. **Lazy Loading**:
   - Load setup types only when needed
   - Don't load all YAMLs for simple commands

### Performance Targets

| Operation | Target | Actual |
|-----------|--------|--------|
| List setup types | <100ms | ~50ms |
| Venv creation | <10s | ~5s |
| Dependency install (uv) | <2min | ~30s |
| VSCode config generation | <1s | ~200ms |
| **Total setup time** | **<5min** | **~1-2min** |

---

## Security Considerations

### Input Validation

- All user inputs validated via Pydantic
- Path traversal prevention (`Path.resolve()`)
- YAML safe loading (`yaml.safe_load()`)

### Subprocess Execution

- No shell=True (prevents injection)
- Whitelist of allowed executables (uv, pip, poetry)
- Argument sanitization

### File Operations

- Atomic writes (write to temp, then rename)
- Permission checks before file operations
- No following symlinks in sensitive operations

### Secrets Management

- Never commit `.env` files
- Warn if user tries to commit secrets
- `.gitignore` includes common secret files

---

## Future Enhancements

### Planned Features

1. **Custom Setup Types**:
   - User-defined YAML in `~/.typysetup/custom/`
   - Validation against JSON schema

2. **CI/CD Integration**:
   - GitHub Actions workflow generation
   - GitLab CI configuration

3. **Docker Support**:
   - Generate Dockerfile for setup type
   - Docker Compose for multi-service setups

4. **Plugin System**:
   - Third-party setup type plugins
   - Custom post-setup hooks

### Architecture Improvements

1. **Async Operations**:
   - Use `asyncio` for parallel dependency installation
   - Non-blocking UI updates

2. **Incremental Updates**:
   - Update existing setups with new dependencies
   - Migrate to newer Python versions

3. **Telemetry**:
   - Anonymous usage statistics (opt-in)
   - Error reporting for debugging

---

## References

- **Typer Documentation**: https://typer.tiangolo.com
- **Pydantic Documentation**: https://docs.pydantic.dev
- **Python venv Module**: https://docs.python.org/3/library/venv.html
- **Rich Documentation**: https://rich.readthedocs.io
- **uv Documentation**: https://docs.astral.sh/uv

---

**Document Version**: 1.0
**Last Updated**: 2026-01-25
**Maintainer**: TyPySetup Development Team
