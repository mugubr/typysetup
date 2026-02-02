"""Generate .gitignore files for new projects."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GitignoreGenerator:
    """Generate .gitignore files with Python best practices."""

    GITIGNORE_TEMPLATE = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual Environments
venv/
.venv/
env/
ENV/
*.egg-info/

# Distribution/Build
dist/
build/
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project Config
.typysetup/

# Backup files
*.backup.*
"""

    @staticmethod
    def generate_gitignore(project_path: Path) -> Path:
        """Generate .gitignore file if it doesn't exist.

        Args:
            project_path: Path to project root

        Returns:
            Path to created/existing .gitignore file

        Raises:
            OSError: If file creation fails
        """
        gitignore_path = project_path / ".gitignore"

        if gitignore_path.exists():
            logger.info(f".gitignore already exists at {gitignore_path}")
            return gitignore_path

        try:
            gitignore_path.write_text(GitignoreGenerator.GITIGNORE_TEMPLATE)
            logger.info(f"Created .gitignore at {gitignore_path}")
            return gitignore_path
        except OSError as e:
            logger.error(f"Failed to create .gitignore: {e}")
            raise
