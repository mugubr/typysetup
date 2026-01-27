"""Rollback context manager for atomic operations with automatic cleanup on failure."""

import logging
from typing import TYPE_CHECKING, Callable, List, Tuple

from rich.console import Console

if TYPE_CHECKING:
    from typing import Literal

logger = logging.getLogger(__name__)
console = Console()


class RollbackContext:
    """Context manager for automatic cleanup on failure.

    Implements LIFO (Last In, First Out) cleanup pattern to safely
    reverse operations when an exception occurs.

    Example:
        >>> with RollbackContext() as rollback:
        ...     create_resource()
        ...     rollback.register_cleanup(cleanup_resource, "Clean up resource")
        ...     validate_operation()
        ...     # Success - no cleanup triggered
        ...
        ...     # If exception occurs, cleanup_resource() is called

    Attributes:
        cleanup_actions: List of (callable, description) tuples to execute on failure
    """

    def __init__(self) -> None:
        """Initialize rollback context with empty cleanup stack."""
        self.cleanup_actions: List[Tuple[Callable[[], None], str]] = []

    def __enter__(self) -> "RollbackContext":
        """Enter context manager.

        Returns:
            Self for use in with statement
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> "Literal[False]":
        """Exit context manager and execute cleanup if exception occurred.

        Args:
            exc_type: Exception type if exception occurred, None otherwise
            exc_val: Exception value if exception occurred, None otherwise
            exc_tb: Exception traceback if exception occurred, None otherwise

        Returns:
            False to propagate any exception that occurred
        """
        if exc_type is not None:
            self._execute_rollback()
        return False  # Don't suppress exceptions

    def register_cleanup(self, action: Callable[[], None], description: str = "") -> None:
        """Register a cleanup action to execute on failure.

        Actions are executed in LIFO (Last In, First Out) order,
        ensuring proper cleanup sequence.

        Args:
            action: Callable that performs cleanup (takes no arguments)
            description: Human-readable description of cleanup action

        Example:
            >>> rollback.register_cleanup(
            ...     lambda: shutil.rmtree(directory),
            ...     "Remove temporary directory"
            ... )
        """
        self.cleanup_actions.append((action, description))
        logger.debug(f"Registered cleanup: {description}")

    def _execute_rollback(self) -> None:
        """Execute all cleanup actions in reverse (LIFO) order.

        Continues executing remaining actions even if individual
        actions fail, logging warnings for failures.
        """
        console.print("[yellow]Rolling back changes...[/yellow]")
        logger.warning("Executing rollback sequence")

        for action, description in reversed(self.cleanup_actions):
            try:
                if description:
                    console.print(f"[dim]  Undoing: {description}[/dim]")
                    logger.debug(f"Executing: {description}")

                action()

            except Exception as e:
                # Log but don't raise - continue with remaining cleanups
                error_msg = f"Rollback action failed: {description} - {e}"
                console.print(f"[red]  Warning: {error_msg}[/red]")
                logger.error(error_msg, exc_info=True)

        console.print("[dim]Rollback complete[/dim]")
        logger.info("Rollback sequence completed")
