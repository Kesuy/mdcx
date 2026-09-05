from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractSlider,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTextEdit,
)


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


@dataclass(frozen=True)
class ChoiceBinding:
    path: str
    choices: tuple[tuple[str, Any], ...]
    default: Any


@dataclass(frozen=True)
class MultiChoiceBinding:
    path: str
    choices: tuple[tuple[str, Any], ...]
    preserve_unknown: bool = True


@dataclass(frozen=True)
class FieldOptionBinding:
    field: Any
    language_choices: tuple[tuple[str, Any], ...]
    default_language: Any
    translate_widget: str
    mirror_fields: tuple[Any, ...] = ()


@dataclass(frozen=True)
class CompositeBinding:
    """Typed load/save contract for settings represented by several widgets."""

    name: str
    load: Callable[[object, object], None]
    save: Callable[[object, object], None]


class ConfigBinder:
    """Declarative two-way binding between generated Qt widgets and Config."""

    def __init__(
        self,
        ui: object,
        bindings: list[SettingBinding],
        choices: list[ChoiceBinding] | None = None,
        multi_choices: list[MultiChoiceBinding] | None = None,
        field_options: list[FieldOptionBinding] | None = None,
        composites: list[CompositeBinding] | None = None,
    ):
        self.ui = ui
        self.bindings = bindings
        self.choices = choices or []
        self.multi_choices = multi_choices or []
        self.field_options = field_options or []
        self.composites = composites or []

    @staticmethod
    def _read_widget(widget: object) -> Any:
        if isinstance(widget, QAbstractButton):
            return widget.isChecked()
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QPlainTextEdit | QTextEdit):
            return widget.toPlainText()
        if isinstance(widget, QSpinBox | QDoubleSpinBox | QAbstractSlider):
            return widget.value()
        raise TypeError(f"不支持的设置控件: {type(widget).__name__}")

    @staticmethod
    def _write_widget(widget: object, value: Any) -> None:
        if isinstance(widget, QAbstractButton):
            widget.setChecked(bool(value))
        elif isinstance(widget, QLineEdit):
            widget.setText("" if value is None else str(value))
        elif isinstance(widget, QPlainTextEdit | QTextEdit):
            widget.setPlainText("" if value is None else str(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QSpinBox | QAbstractSlider):
            widget.setValue(int(value))
        else:
            raise TypeError(f"不支持的设置控件: {type(widget).__name__}")

    def load(self, config: object) -> None:
        for binding in self.bindings:
            owner, name = _resolve(config, binding.path)
            self._write_widget(getattr(self.ui, binding.widget), binding.formatter(getattr(owner, name)))
        for binding in self.choices:
            owner, name = _resolve(config, binding.path)
            value = getattr(owner, name)
            selected = next((widget for widget, choice in binding.choices if choice == value), None)
            if selected is None:
                selected = next(widget for widget, choice in binding.choices if choice == binding.default)
            getattr(self.ui, selected).setChecked(True)
        for binding in self.multi_choices:
            owner, name = _resolve(config, binding.path)
            selected_values = getattr(owner, name)
            for widget, choice in binding.choices:
                getattr(self.ui, widget).setChecked(choice in selected_values)
        for binding in self.field_options:
            field_config = config.get_field_config(binding.field)
            selected = next(
                (widget for widget, language in binding.language_choices if language == field_config.language),
                next(widget for widget, language in binding.language_choices if language == binding.default_language),
            )
            getattr(self.ui, selected).setChecked(True)
            getattr(self.ui, binding.translate_widget).setChecked(field_config.translate)
        for binding in self.composites:
            binding.load(self.ui, config)

    def save(self, config: object) -> None:
        for binding in self.bindings:
            owner, name = _resolve(config, binding.path)
            raw = self._read_widget(getattr(self.ui, binding.widget))
            setattr(owner, name, binding.parser(raw))
        for binding in self.choices:
            owner, name = _resolve(config, binding.path)
            value = next(
                (choice for widget, choice in binding.choices if getattr(self.ui, widget).isChecked()),
                binding.default,
            )
            setattr(owner, name, value)
        for binding in self.multi_choices:
            owner, name = _resolve(config, binding.path)
            known_values = {choice for _widget, choice in binding.choices}
            values = [choice for widget, choice in binding.choices if getattr(self.ui, widget).isChecked()]
            if binding.preserve_unknown:
                values.extend(value for value in getattr(owner, name) if value not in known_values)
            setattr(owner, name, values)
        for binding in self.field_options:
            language = next(
                (choice for widget, choice in binding.language_choices if getattr(self.ui, widget).isChecked()),
                binding.default_language,
            )
            translate = getattr(self.ui, binding.translate_widget).isChecked()
            for field in (binding.field, *binding.mirror_fields):
                config.set_field_language(field, language)
                config.set_field_translate(field, translate)
        for binding in self.composites:
            binding.save(self.ui, config)
