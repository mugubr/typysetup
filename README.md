# TyPySetup - Python Environment Setup CLI

Interactive Python environment setup CLI for VSCode. Automatically configure Python projects with proper virtual environments, dependencies, and VSCode settings.

## Features

- 🎯 **Interactive Menu** - Select from 6 project type templates (FastAPI, Django, Data Science, CLI Tools, Async/Real-time, ML/AI)
- 🔧 **Automatic Setup** - Create virtual environment, install dependencies, generate VSCode configs
- 📦 **Multiple Package Managers** - Support for uv (fast), pip (universal), and poetry (lock files)
- ⚙️ **Smart Configuration** - VSCode settings optimized per project type, non-destructive merging
- 💾 **Preference Persistence** - Remember your choices for faster future setups
- 🔄 **Graceful Cancellation** - Cancel between phases with automatic rollback

## Quick Start

### Installation

```bash
# Install from source (development)
git clone <repository>
cd typysetup
pip install -e .
```

### Basic Usage

```bash
# Interactive setup wizard
typysetup setup /path/to/project

# List available setup types
typysetup list

# Manage preferences
typysetup preferences --show
```

### Example: FastAPI Project

```bash
$ typysetup setup ~/my-api
? Choose a setup type: FastAPI
? Package manager (uv recommended): uv
? Proceed with setup? [Y/n]: y

Creating virtual environment...
Installing dependencies (14 packages)...
Generating VSCode configuration...

✓ Setup complete! Next steps:
  - Activate: source ~/my-api/venv/bin/activate
  - Open VSCode: code ~/my-api
  - Start coding: fastapi dev main.py
```

## Project Structure

```bash
typysetup/
├── src/typysetup/
│   ├── main.py                # Typer CLI application
│   ├── models/                # Pydantic data models
│   ├── commands/              # CLI commands (setup, list, preferences)
│   ├── core/                  # Business logic (config loading, venv, deps, vscode)
│   ├── utils/                 # Utilities (UI, paths, validators)
│   └── configs/               # Setup type YAML templates
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── conftest.py           # Pytest fixtures
└── pyproject.toml            # Project metadata and dependencies
```

## Setup Types

### FastAPI

Web API with FastAPI framework - async, modern, fast

- Python: 3.10+
- Core: fastapi, uvicorn, pydantic
- Dev: pytest, black, ruff

### Django

Full-stack web framework with batteries included

- Python: 3.8+
- Core: django, djangorestframework
- Dev: pytest, black, ruff

### Data Science

Jupyter-based data analysis and ML workflows

- Python: 3.9+
- Core: pandas, numpy, jupyter, scikit-learn
- Dev: pytest, black, ruff

### CLI Tool

Command-line applications using Typer/Click

- Python: 3.8+
- Core: typer, click, rich
- Dev: pytest, black, ruff

### Async/Real-time

High-performance async and real-time applications

- Python: 3.10+
- Core: asyncio, aiohttp, websockets, starlette
- Dev: pytest, black, ruff

### ML/AI

Machine learning and AI model development

- Python: 3.9+
- Core: tensorflow, torch, transformers, scikit-learn
- Dev: pytest, black, ruff

## Technology Stack

- **Language**: Python 3.8+
- **CLI Framework**: Typer (type-safe, beautiful)
- **Data Validation**: Pydantic (runtime validation)
- **Configuration**: YAML + PyYAML (human-friendly)
- **Terminal UI**: Rich + Questionary (interactive prompts)
- **Virtual Environment**: Built-in venv module
- **Package Managers**: uv (primary), pip, poetry
- **Testing**: pytest + pytest-cov
- **Code Quality**: black, ruff, mypy

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/typysetup
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/typysetup
```

## Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage report
pytest --cov=src/typysetup --cov-report=html
```

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Configuration

User preferences are stored in `~/.typysetup/preferences.json`:

```json
{
  "preferred_manager": "uv",
  "preferred_python_version": "3.11",
  "preferred_setup_types": ["fastapi"],
  "setup_history": []
}
```

## Commands

### `typysetup setup`

Interactive setup wizard - guides you through project configuration.

```bash
typysetup setup /path/to/project [--verbose]
```

**Options**:

- `--verbose, -v`: Enable detailed logging output

**Example**:

```bash
typysetup setup ~/my-fastapi-app --verbose
```

### `typysetup list`

List all available setup type templates.

```bash
typysetup list
```

### `typysetup preferences`

Manage user preferences and view setup history.

```bash
typysetup preferences --show   # View current preferences
typysetup preferences --reset  # Reset to defaults
```

### `typysetup config`

Display project configuration.

```bash
typysetup config /path/to/project
```

### `typysetup history`

View recent setup history.

```bash
typysetup history [--limit 10] [--verbose]
```

### `typysetup help`

Show detailed help and usage examples.

```bash
typysetup help [topic]  # Topics: setup, workflows, preferences
```

## Common Workflows

### Creating a New FastAPI Project

```bash
mkdir my-api
cd my-api
typysetup setup .
# Select "FastAPI" from menu
# Choose "uv" as package manager
source venv/bin/activate
code .
```

### Data Science Project with Jupyter

```bash
typysetup setup ml-analysis
# Select "Data Science"
cd ml-analysis
source venv/bin/activate
jupyter notebook
```

### Converting Existing Project

```bash
cd existing-project
typysetup setup .
# TyPySetup will detect and preserve existing files
# Select appropriate setup type
```

## Troubleshooting

For detailed troubleshooting guide, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Quick Fixes

**Python not found**:

```bash
python --version  # Ensure 3.8+
```

**Command not found**:

```bash
pip install typysetup
# or
pip install --user typysetup
```

**Permission denied**:

```bash
chmod u+w /path/to/project
```

**VSCode not recognizing venv**:

- Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"
- Select interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter"

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see LICENSE file for details
