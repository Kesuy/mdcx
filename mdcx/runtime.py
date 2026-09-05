from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationServices:
    """Small injectable holder for process-level services during gradual migration."""

    config_manager: Any
    executor: Any
    event_sink: Any
    task_manager: Any | None = None
    network_services: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_globals(cls, *, task_manager: Any | None = None) -> ApplicationServices:
        from .config.manager import manager
        from .signals import signal
        from .utils import executor

        return cls(
            config_manager=manager,
            executor=executor,
            event_sink=signal,
            task_manager=task_manager,
        )
