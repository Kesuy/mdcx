from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .enums import FileMode
from .failure import FailureRecord
from .types import ScrapeResult


@dataclass
class ScrapeSessionState:
    file_mode: FileMode = FileMode.Default
    started_at: float = field(default_factory=time.time)
    total_count: int = 0
    started_count: int = 0
    completed_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    remain_queue: list[Path] = field(default_factory=list)
    failures: list[FailureRecord] = field(default_factory=list)
    success_paths: set[Path] = field(default_factory=set)
    per_run_caches: dict[str, Any] = field(default_factory=dict)
    retry_context: dict[Path, tuple[str, str, str]] = field(default_factory=dict)
    appointment_url: str = ""
    specified_site: str = ""


class ScrapeSession:
    """State owned by one scrape run; Flags mirrors it during migration."""

    def __init__(self, state: ScrapeSessionState | None = None) -> None:
        self.state = state or ScrapeSessionState()
        self._cancelled = threading.Event()
        self._lock = threading.RLock()
        self._remain_version = 0
        self._remain_dirty = False

    @property
    def cancellation_requested(self) -> bool:
        return self._cancelled.is_set()

    def request_cancel(self) -> None:
        self._cancelled.set()

    def reset(self, file_mode: FileMode) -> None:
        with self._lock:
            self.state = ScrapeSessionState(file_mode=file_mode)
            self._cancelled.clear()
            self._remain_version = 0
            self._remain_dirty = False

    def replace_remain_queue(self, paths: list[Path], *, mark_dirty: bool = True) -> None:
        with self._lock:
            self.state.remain_queue[:] = paths
            self._remain_version += 1
            self._remain_dirty = mark_dirty

    def remove_remain_path(self, path: Path) -> bool:
        with self._lock:
            try:
                self.state.remain_queue.remove(path)
            except ValueError:
                return False
            self._remain_version += 1
            self._remain_dirty = True
            return True

    def remain_snapshot(self) -> tuple[list[Path], int, bool]:
        with self._lock:
            return list(self.state.remain_queue), self._remain_version, self._remain_dirty

    def mark_remain_saved(self, version: int) -> None:
        with self._lock:
            if self._remain_version == version:
                self._remain_dirty = False

    def record_failure(self, record: FailureRecord) -> None:
        with self._lock:
            self.state.failures.append(record)
            self.state.failure_count = max(self.state.failure_count, len(self.state.failures))

    def record_success(self, path: Path) -> None:
        with self._lock:
            self.state.success_paths.add(path)

    def increment_progress(self, field_name: str) -> int:
        if field_name not in {"started_count", "completed_count", "success_count", "failure_count"}:
            raise ValueError(f"unsupported progress field: {field_name}")
        with self._lock:
            value = getattr(self.state, field_name) + 1
            setattr(self.state, field_name, value)
            return value

    def cache(self, name: str, factory: type = dict) -> Any:
        with self._lock:
            return self.state.per_run_caches.setdefault(name, factory())

    def sync_progress(
        self,
        *,
        total: int | None = None,
        started: int | None = None,
        completed: int | None = None,
        succeeded: int | None = None,
        failed: int | None = None,
    ) -> None:
        with self._lock:
            if total is not None:
                self.state.total_count = total
            if started is not None:
                self.state.started_count = started
            if completed is not None:
                self.state.completed_count = completed
            if succeeded is not None:
                self.state.success_count = succeeded
            if failed is not None:
                self.state.failure_count = failed

    @property
    def scrape_results(self) -> dict[str, ScrapeResult]:
        return self.cache("scrape_results")
