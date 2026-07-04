"""Setup wizard phases.

Each phase groups one cohesive slice of the wizard flow so it can be
tested against its explicit inputs instead of orchestrator internals:

- SelectionPhase: interactive prompts (type, version, manager, deps, ...)
- ScaffoldPhase: .gitignore, VSCode config and pyproject.toml generation
- EnvironmentPhase: venv creation and dependency installation
- SummaryPhase: final report and next steps
"""

from typysetup.commands.phases.environment_phase import EnvironmentPhase
from typysetup.commands.phases.scaffold_phase import ScaffoldPhase
from typysetup.commands.phases.selection_phase import SelectionPhase
from typysetup.commands.phases.summary_phase import SummaryPhase

__all__ = [
    "EnvironmentPhase",
    "ScaffoldPhase",
    "SelectionPhase",
    "SummaryPhase",
]
