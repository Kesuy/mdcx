from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtWidgets import QAbstractButton, QAbstractSlider, QLineEdit, QPlainTextEdit, QSpinBox


def _resolve(root: object, path: str) -> tuple[object, str]:
    parts = path.split(".")
    current = root
    for part in parts[:-1]:
        current = getattr(current, part)
    return current, parts[-1]


@dataclass(frozen=True)
class SettingBinding:
    widget: str
    path: str
    parser: Callable[[Any], Any] = lambda value: value
    formatter: Callable[[Any], Any] = lambda value: value


class ConfigBinder:
    """Declarative two-way binding between generated Qt widgets and Config."""

    def __init__(self, ui: object, bindings: list[SettingBinding]):
        self.ui = ui
        self.bindings = bindings

    @staticmethod
    def _read_widget(widget: object) -> Any:
        if isinstance(widget, QAbstractButton):
            return widget.isChecked()
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        if isinstance(widget, QSpinBox | QAbstractSlider):
            return widget.value()
        raise TypeError(f"不支持的设置控件: {type(widget).__name__}")

    @staticmethod
    def _write_widget(widget: object, value: Any) -> None:
        if isinstance(widget, QAbstractButton):
            widget.setChecked(bool(value))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value or ""))
        elif isinstance(widget, QPlainTextEdit):
            widget.setPlainText(str(value or ""))
        elif isinstance(widget, QSpinBox | QAbstractSlider):
            widget.setValue(int(value))
        else:
            raise TypeError(f"不支持的设置控件: {type(widget).__name__}")

    def load(self, config: object) -> None:
        for binding in self.bindings:
            owner, name = _resolve(config, binding.path)
            self._write_widget(getattr(self.ui, binding.widget), binding.formatter(getattr(owner, name)))

    def save(self, config: object) -> None:
        for binding in self.bindings:
            owner, name = _resolve(config, binding.path)
            raw = self._read_widget(getattr(self.ui, binding.widget))
            setattr(owner, name, binding.parser(raw))
