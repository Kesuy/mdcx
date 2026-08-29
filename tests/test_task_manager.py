from __future__ import annotations

import asyncio
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from mdcx.task_manager import QtTaskManager

APP = QApplication.instance() or QApplication([])


def _wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        APP.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Qt callback was not dispatched before timeout")


def test_task_manager_marshals_async_completion_to_qt_thread() -> None:
    manager = QtTaskManager()
    completed: list[tuple[int, int]] = []
    qt_thread = threading.get_ident()

    async def work() -> int:
        await asyncio.sleep(0)
        return 42

    manager.submit("answer", work(), on_success=lambda value: completed.append((value, threading.get_ident())))
    _wait_until(lambda: bool(completed))

    assert completed == [(42, qt_thread)]
    assert not manager.is_running("answer")
    manager.shutdown()


def test_task_manager_routes_errors_and_cleans_registry() -> None:
    manager = QtTaskManager()
    errors: list[str] = []

    async def fail() -> None:
        raise RuntimeError("expected failure")

    manager.submit("failure", fail(), on_error=errors.append)
    _wait_until(lambda: bool(errors))

    assert "expected failure" in errors[0]
    assert not manager.is_running("failure")
    manager.shutdown()


def test_task_manager_replaces_named_task_without_delivering_stale_callback() -> None:
    manager = QtTaskManager()
    completed: list[str] = []

    async def slow() -> str:
        await asyncio.sleep(1)
        return "stale"

    async def current() -> str:
        return "current"

    manager.submit("replaceable", slow(), on_success=completed.append)
    manager.submit("replaceable", current(), on_success=completed.append)
    _wait_until(lambda: completed == ["current"])

    assert completed == ["current"]
    manager.shutdown()
