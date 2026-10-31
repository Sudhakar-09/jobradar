"""Run async code from sync entry points (CLI, tasks) on every platform.

psycopg's async driver cannot use Windows' default Proactor event loop, so on Windows the
selector loop is used.
"""

import asyncio
import sys
from collections.abc import Callable, Coroutine


def loop_factory(platform: str = sys.platform) -> Callable[[], asyncio.AbstractEventLoop] | None:
    """Return the event loop factory for ``platform`` (None = asyncio's default)."""
    if platform == "win32":
        return asyncio.SelectorEventLoop
    return None


def run[T](coroutine: Coroutine[object, object, T]) -> T:
    """Run a coroutine to completion with a platform-appropriate event loop."""
    return asyncio.run(coroutine, loop_factory=loop_factory())
