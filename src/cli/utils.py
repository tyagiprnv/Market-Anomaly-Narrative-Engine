"""Utility functions for CLI commands."""

import asyncio
import functools
import logging
import signal
import sys
from typing import Any, Callable

from rich.console import Console

logger = logging.getLogger(__name__)

# Global Rich console instance
console = Console()


def async_command(f: Callable) -> Callable:
    """Decorator to run async Click commands.

    Click doesn't natively support async functions, so this decorator
    wraps them with asyncio.run().

    Args:
        f: Async function to wrap

    Returns:
        Synchronous wrapper function
    """

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def run_with_shutdown(scheduler: Any, console: Console) -> None:
    """Run scheduler with graceful shutdown on SIGINT/SIGTERM.

    Sets up signal handlers to gracefully stop the scheduler when
    receiving interrupt signals.

    Args:
        scheduler: AnomalyDetectionScheduler instance
        console: Rich console for output

    Note:
        On Windows, signal handling works differently. This implementation
        uses asyncio event loop signal handlers which work on Unix-like systems.
        On Windows, Ctrl+C will still work but may not be as clean.
    """
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler() -> None:
        """Handle shutdown signal."""
        stop_event.set()

    # Setup signal handlers (Unix-like systems)
    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    else:
        # On Windows, we rely on KeyboardInterrupt
        pass

    try:
        # Start scheduler
        await scheduler.start()

        console.print(
            "[green]Scheduler started successfully[/green]\n"
            "[yellow]Press Ctrl+C to stop gracefully[/yellow]"
        )

        # Keep running until signal received
        if sys.platform != "win32":
            await stop_event.wait()
        else:
            # On Windows, just keep the scheduler running
            # KeyboardInterrupt will be caught by outer try/except
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Received interrupt signal (Ctrl+C)[/yellow]")
    finally:
        console.print("[yellow]Stopping scheduler gracefully...[/yellow]")
        await scheduler.stop()
        console.print("[green]Shutdown complete[/green]")
