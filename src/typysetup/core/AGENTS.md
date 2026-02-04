# AGENTS.md - Core Module

Business logic layer for TyPySetup. All orchestration happens here.

## Module Map

| File | Class | Responsibility |
|------|-------|----------------|
| `config_loader.py` | `ConfigLoader` | Load YAML configs → Pydantic models |
| `venv_manager.py` | `VirtualEnvironmentManager` | Create/manage Python venvs |
| `dependency_installer.py` | `DependencyInstaller` | Install packages via uv/pip/poetry |
| `vscode_config_generator.py` | `VSCodeConfigGenerator` | Generate .vscode/ settings |
| `preference_manager.py` | `PreferenceManager` | User prefs in `~/.typysetup/` |
| `project_config_manager.py` | `ProjectConfigManager` | Project state in `.typysetup.json` |
| `setup_type_registry.py` | `SetupTypeRegistry` | Registry of available setup types |
| `setup_type_utils.py` | `SetupTypeComparator/Filter/Validator` | Setup type utilities |
| `pyproject_generator.py` | `PyprojectGenerator` | Generate pyproject.toml |
| `gitignore_generator.py` | `GitignoreGenerator` | Generate .gitignore |
| `file_backup_manager.py` | `FileBackupManager` | Backup/restore files during setup |

## Conventions

### Error Handling
Each module defines its own exceptions:
```python
class ConfigLoadError(Exception): ...
class PreferenceLoadError(Exception): ...
class PreferenceSaveError(Exception): ...
```
Always raise specific exceptions, never generic `Exception`.

### File Operations
- Use `Path` objects exclusively
- Check existence before operations
- Use context managers for file I/O
- Backup before overwrite via `FileBackupManager`

### Package Manager Support
`DependencyInstaller` supports:
- `uv` (preferred) - fast Rust-based installer
- `pip` (universal) - standard fallback
- `poetry` (lock files) - for poetry users

Detection order: check if available in PATH, fall back gracefully.

## Key Classes

### ConfigLoader
```python
loader = ConfigLoader(configs_dir=Path("configs/"))
setup_type = loader.load_setup_type("fastapi")  # Returns SetupType model
all_types = loader.load_all_setup_types()       # Returns dict[str, SetupType]
```

### VirtualEnvironmentManager
```python
venv_mgr = VirtualEnvironmentManager(project_path)
venv_mgr.create_venv()           # Creates ./venv/
venv_mgr.get_python_executable() # Returns Path to venv python
venv_mgr.is_venv_active()        # Check if venv exists
```

### DependencyInstaller
```python
installer = DependencyInstaller(venv_path, manager="uv")
installer.install(["fastapi", "uvicorn"])  # Install packages
installer.install_from_requirements(Path("requirements.txt"))
```

### VSCodeConfigGenerator
```python
generator = VSCodeConfigGenerator(project_path)
generator.generate(setup_type)  # Creates .vscode/settings.json, launch.json, extensions.json
```
**Note**: Merges with existing settings, doesn't overwrite.

## Anti-Patterns

1. **Don't bypass ConfigLoader** - all YAML → model conversion goes through it
2. **Don't hardcode paths** - use `Path` and relative paths
3. **Check venv exists before operations** - `VirtualEnvironmentManager.is_venv_active()`
4. **Never store secrets in PreferenceManager** - it's plain JSON in home dir
