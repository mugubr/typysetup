# AGENTS.md - TyPySetup

Interactive Python environment setup CLI for VSCode. Configures virtual environments, dependencies, and VSCode settings via Typer-based wizard.

## Quick Reference

| Item | Value |
|------|-------|
| Entry point | `typysetup.main:app` (Typer CLI) |
| Python | 3.8+ (targets 3.8-3.12) |
| Package manager | setuptools, src layout |
| Main deps | typer, pydantic 2.0, pyyaml, rich, questionary |

## Architecture

```
src/typysetup/
├── main.py              # CLI commands (setup, list, preferences, config, history, help)
├── commands/            # setup_orchestrator.py - main workflow (823 lines, HOTSPOT)
├── core/                # Business logic - see core/AGENTS.md
├── models/              # Pydantic models - see models/AGENTS.md
├── utils/               # UI prompts, paths, rollback, performance
└── configs/             # YAML templates for setup types (fastapi.yaml, django.yaml, etc.)
```

## Conventions

### Code Style
- Black: 100 char line length
- Ruff: E, W, F, I, B, C4, UP rules
- MyPy: lenient (`disallow_untyped_defs=false`, `ignore_missing_imports=true`)
- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`

### Patterns
- All data models: Pydantic BaseModel with `model_config = ConfigDict(...)`
- Config loading: YAML files in `configs/` → Pydantic models via ConfigLoader
- Error classes: Custom exceptions per module (e.g., `ConfigLoadError`, `PreferenceSaveError`)
- File operations: Always use `pathlib.Path`, never string concatenation

### Testing
- pytest with markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Coverage: `--cov=src/typysetup --cov-report=html`
- Fixtures: `tests/conftest.py` - temp directories, mock configs, sample data

## Anti-Patterns (NEVER do these)

1. **Core dependencies are ALWAYS selected** - cannot be deselected in UI
2. **Never commit `.env` files** - user preferences go to `~/.typysetup/`
3. **Use `datetime.now(UTC)`** not deprecated `datetime.utcnow()`
4. **No `as any` or type suppression** - fix the types properly
5. **Don't hardcode version** - import from `__version__` in `__init__.py`

## Complexity Hotspots

| File | Lines | Issue |
|------|-------|-------|
| `commands/setup_orchestrator.py` | 823 | God class, cyclomatic complexity 158 |
| `main.py` | 487 | All commands inline, should extract to commands/ |
| `core/vscode_config_generator.py` | 400+ | Complex merge logic |

## Build & CI

```bash
# Development
pip install -e ".[dev]"
pytest                    # All tests
pytest tests/unit/        # Unit only
pytest tests/integration/ # Integration only

# Quality
black src/ tests/
ruff check src/ tests/
mypy src/typysetup

# Build & publish (GitHub Actions)
# Trigger: push tag v*.*.*
# Workflow: .github/workflows/publish.yml → PyPI
```

## Key Flows

### Setup Command Flow
1. `main.py:setup` → `SetupOrchestrator.run()`
2. Load configs via `ConfigLoader` → prompt user via `questionary`
3. Create venv → install deps → generate VSCode config
4. Save to `~/.typysetup/preferences.json` and project `.typysetup.json`

### Config Loading
1. YAML in `configs/{setup_type}.yaml`
2. `ConfigLoader.load_setup_type()` → validates via Pydantic
3. Returns `SetupType` model with dependencies, vscode settings, metadata

## Files You'll Touch Often

| Task | Files |
|------|-------|
| Add CLI command | `main.py`, possibly new file in `commands/` |
| Add setup type | `configs/{name}.yaml`, update `SetupTypeRegistry` |
| Change model | `models/*.py`, check all usages |
| Fix venv/deps | `core/venv_manager.py`, `core/dependency_installer.py` |
| VSCode settings | `core/vscode_config_generator.py`, `models/vscode_config.py` |

## Related Docs

- `README.md` - User-facing documentation
- `src/typysetup/core/AGENTS.md` - Core business logic details
- `src/typysetup/models/AGENTS.md` - Pydantic model details
