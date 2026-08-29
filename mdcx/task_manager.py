from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Callable, Coroutine
from concurrent.futures import CancelledError, Future
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from .utils import executor

logger = logging.getLogger(__name__)


class QtTaskManager(QObject):
    """Submit async or blocking work and marshal completion back to Qt."""

    _completed = pyqtSignal(str, object, object)
    _failed = pyqtSignal(str, object, str)
    task_failed = pyqtSignal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._callbacks: dict[str, tuple[Callable[[Any], None] | None, Callable[[str], None] | None]] = {}
        self._futures: dict[str, Future] = {}
        self._shutting_down = False
        self._completed.connect(self._dispatch_success)
        self._failed.connect(self._dispatch_error)

    def submit(
        self,
        name: str,
        coroutine: Coroutine[Any, Any, Any],
        *,
        group: object | None = None,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> Future:
        self.cancel(name)
        self._callbacks[name] = (on_success, on_error)
        future = executor.submit(coroutine, group=group)
        self._futures[name] = future

        def done(completed: Future) -> None:
            if self._shutting_down:
                return
            try:
                self._completed.emit(name, completed, completed.result())
            except CancelledError:
                return
            except Exception:
                self._failed.emit(name, completed, traceback.format_exc())

        future.add_done_callback(done)
        return future

    def submit_sync(
        self,
        name: str,
        function: Callable[..., Any],
        *args,
        group: object | None = None,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        **kwargs,
    ) -> Future:
        return self.submit(
            name,
            asyncio.to_thread(function, *args, **kwargs),
            group=group,
            on_success=on_success,
            on_error=on_error,
        )

    def cancel(self, name: str) -> None:
        self._callbacks.pop(name, None)
        future = self._futures.pop(name, None)
        if future is not None and not future.done():
            future.cancel()

    def cancel_all(self) -> None:
        for name in list(self._futures):
            self.cancel(name)

    def is_running(self, name: str) -> bool:
        future = self._futures.get(name)
        return future is not None and not future.done()

    def _dispatch_success(self, name: str, completed: Future, result: object) -> None:
        if self._futures.get(name) is not completed:
            return
        self._futures.pop(name, None)
        success, _ = self._callbacks.pop(name, (None, None))
        if success is not None:
            success(result)

    def _dispatch_error(self, name: str, completed: Future, error: str) -> None:
        if self._futures.get(name) is not completed:
            return
        self._futures.pop(name, None)
        _, failed = self._callbacks.pop(name, (None, None))
        if failed is not None:
            failed(error)
        else:
            logger.error("Background task %s failed:\n%s", name, error)
        self.task_failed.emit(name, error)

    def shutdown(self) -> None:
        self._shutting_down = True
        self.cancel_all()
        self._callbacks.clear()
