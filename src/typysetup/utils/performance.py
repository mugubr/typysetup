"""
Performance monitoring and optimization utilities.

Provides timing measurements, progress tracking, and performance optimization helpers.
"""

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

logger = logging.getLogger(__name__)
console = Console()


class PerformanceTimer:
    """Track performance metrics for operations."""

    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}

    def record(self, operation: str, duration: float, success: bool = True):
        """
        Record performance metric for an operation.

        Args:
            operation: Name of the operation
            duration: Duration in seconds
            success: Whether operation succeeded
        """
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "success_count": 0,
                "failure_count": 0,
            }

        metric = self.metrics[operation]
        metric["count"] += 1
        metric["total_duration"] += duration
        metric["avg_duration"] = metric["total_duration"] / metric["count"]
        metric["min_duration"] = min(metric["min_duration"], duration)
        metric["max_duration"] = max(metric["max_duration"], duration)

        if success:
            metric["success_count"] += 1
        else:
            metric["failure_count"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all performance metrics."""
        return self.metrics.copy()

    def log_summary(self):
        """Log performance summary."""
        if not self.metrics:
            logger.debug("No performance metrics recorded")
            return

        logger.info("Performance Summary:")
        for operation, metric in self.metrics.items():
            logger.info(
                f"  {operation}: "
                f"{metric['avg_duration']:.2f}s avg "
                f"(min: {metric['min_duration']:.2f}s, "
                f"max: {metric['max_duration']:.2f}s, "
                f"count: {metric['count']}, "
                f"success: {metric['success_count']}/{metric['count']})"
            )

    def display_summary(self):
        """Display performance summary to console."""
        if not self.metrics:
            return

        console.print("\n[bold cyan]Performance Summary:[/bold cyan]")
        for operation, metric in self.metrics.items():
            success_rate = (
                metric["success_count"] / metric["count"] * 100 if metric["count"] > 0 else 0
            )

            console.print(
                f"  [cyan]{operation}[/cyan]: "
                f"{metric['avg_duration']:.2f}s avg "
                f"({metric['min_duration']:.2f}s - {metric['max_duration']:.2f}s) "
                f"| Success: [green]{success_rate:.0f}%[/green]"
            )


# Global performance timer instance
_global_timer = PerformanceTimer()


def get_global_timer() -> PerformanceTimer:
    """Get global performance timer instance."""
    return _global_timer


@contextmanager
def measure_time(operation: str, verbose: bool = False):
    """
    Context manager to measure execution time of an operation.

    Args:
        operation: Name of the operation being measured
        verbose: Whether to log timing information

    Yields:
        dict: Contains 'duration' key after operation completes

    Example:
        >>> with measure_time("venv_creation") as timing:
        ...     create_venv()
        >>> print(f"Duration: {timing['duration']:.2f}s")
    """
    timing = {"duration": 0.0, "success": True}
    start_time = time.time()

    try:
        yield timing
    except Exception:
        timing["success"] = False
        raise
    finally:
        end_time = time.time()
        duration = end_time - start_time
        timing["duration"] = duration

        # Record in global timer
        _global_timer.record(operation, duration, timing["success"])

        # Log if verbose
        if verbose:
            status = "✓" if timing["success"] else "✗"
            logger.info(f"{status} {operation}: {duration:.2f}s")


def timed(operation_name: Optional[str] = None):
    """
    Decorator to measure function execution time.

    Args:
        operation_name: Custom operation name (defaults to function name)

    Example:
        >>> @timed("dependency_installation")
        ... def install_deps():
        ...     ...
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with measure_time(op_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class ProgressManager:
    """Manage progress bars for long-running operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.progress: Optional[Progress] = None

    def create_progress(self) -> Progress:
        """Create a Rich Progress instance."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        )

    @contextmanager
    def task(self, description: str, total: Optional[int] = None):
        """
        Context manager for a single progress task.

        Args:
            description: Task description
            total: Total number of steps (if known)

        Yields:
            TaskID: Progress task ID for updating

        Example:
            >>> pm = ProgressManager()
            >>> with pm.task("Installing dependencies", total=10) as task_id:
            ...     for i in range(10):
            ...         install_package(i)
            ...         pm.progress.update(task_id, advance=1)
        """
        if not self.progress:
            self.progress = self.create_progress()

        with self.progress:
            task_id = self.progress.add_task(description, total=total)
            yield task_id

    @contextmanager
    def indeterminate_task(self, description: str):
        """
        Context manager for indeterminate progress (spinner only).

        Args:
            description: Task description

        Example:
            >>> pm = ProgressManager()
            >>> with pm.indeterminate_task("Creating virtual environment"):
            ...     create_venv()
        """
        if not self.progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            )

        with self.progress:
            task_id = self.progress.add_task(description, total=None)
            yield task_id

    def update(self, task_id: TaskID, **kwargs):
        """Update progress task."""
        if self.progress:
            self.progress.update(task_id, **kwargs)


def estimate_time(operation: str, count: int, avg_time_per_item: float) -> float:
    """
    Estimate total time for an operation.

    Args:
        operation: Operation name
        count: Number of items
        avg_time_per_item: Average time per item in seconds

    Returns:
        Estimated total time in seconds
    """
    # Check if we have historical data
    metrics = _global_timer.metrics.get(operation)
    if metrics and metrics["count"] > 0:
        # Use historical average if available
        return metrics["avg_duration"] * count

    # Use provided estimate
    return count * avg_time_per_item


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(125.5)
        '2m 5s'
        >>> format_duration(65.3)
        '1m 5s'
        >>> format_duration(5.2)
        '5.2s'
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


# Performance optimization helpers


def batch_operations(items: list, batch_size: int = 10, operation: Optional[Callable] = None):
    """
    Batch operations for better performance.

    Args:
        items: List of items to process
        batch_size: Number of items per batch
        operation: Optional operation to apply to each batch

    Yields:
        Batches of items

    Example:
        >>> items = list(range(100))
        >>> for batch in batch_operations(items, batch_size=20):
        ...     process_batch(batch)
    """
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        if operation:
            operation(batch)
        else:
            yield batch


@contextmanager
def suppress_output(suppress: bool = True):
    """
    Context manager to suppress stdout/stderr.

    Args:
        suppress: Whether to suppress output

    Example:
        >>> with suppress_output(True):
        ...     print("This won't be shown")
    """
    if not suppress:
        yield
        return

    import sys
    from io import StringIO

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
