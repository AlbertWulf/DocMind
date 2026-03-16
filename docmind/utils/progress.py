"""
Progress display utilities.
"""

from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.status import Status


@dataclass
class TaskInfo:
    """Information about a progress task."""

    name: str
    total: Optional[int] = None
    current: int = 0


class ProgressDisplay:
    """
    Display progress information during document generation.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize progress display.

        Args:
            verbose: Whether to show verbose output.
        """
        self.console = Console()
        self.verbose = verbose
        self.progress: Optional[Progress] = None
        self.status: Optional[Status] = None
        self.tasks: dict[str, TaskID] = {}

    def start(self, message: str = "Starting...") -> None:
        """Start progress display with a status message."""
        self.status = self.console.status(message, spinner="dots")
        self.status.start()

    def stop(self) -> None:
        """Stop the current status display."""
        if self.status:
            self.status.stop()
            self.status = None

    def update_status(self, message: str) -> None:
        """Update the status message."""
        if self.status:
            self.status.update(message)

    def print(self, message: str) -> None:
        """Print a message."""
        self.console.print(message)

    def print_success(self, message: str) -> None:
        """Print a success message."""
        self.console.print(f"[green]✓[/green] {message}")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"[red]✗[/red] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message."""
        self.console.print(f"[yellow]![/yellow] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        if self.verbose:
            self.console.print(f"[blue]ℹ[/blue] {message}")

    def start_progress(self, description: str, total: Optional[int] = None) -> None:
        """
        Start a progress bar.

        Args:
            description: Description of the task.
            total: Total number of steps (None for indeterminate).
        """
        if self.progress is None:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console,
            )
            self.progress.start()

        task_id = self.progress.add_task(description, total=total)
        self.tasks[description] = task_id

    def update_progress(self, description: str, advance: int = 1) -> None:
        """Update progress for a task."""
        if self.progress and description in self.tasks:
            self.progress.update(self.tasks[description], advance=advance)

    def complete_progress(self, description: str) -> None:
        """Mark a progress task as complete."""
        if self.progress and description in self.tasks:
            self.progress.update(self.tasks[description], completed=True)

    def stop_progress(self) -> None:
        """Stop all progress displays."""
        if self.progress:
            self.progress.stop()
            self.progress = None
            self.tasks.clear()

    def section(self, title: str) -> None:
        """Print a section header."""
        self.console.print()
        self.console.print(f"[bold cyan]▸ {title}[/bold cyan]")

    def summary(self, items: list[tuple[str, str]]) -> None:
        """Print a summary of key-value pairs."""
        self.console.print()
        self.console.print("[bold]Summary:[/bold]")
        for key, value in items:
            self.console.print(f"  {key}: {value}")