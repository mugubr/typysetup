"""Shared helpers for setup wizard phases."""

import sys
import traceback

from rich.console import Console

console = Console()


def print_traceback_if_verbose() -> None:
    """Print the active exception traceback when --verbose is enabled."""
    if "--verbose" in sys.argv:
        traceback.print_exc()
