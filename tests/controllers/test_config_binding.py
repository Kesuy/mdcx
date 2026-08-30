# ruff: noqa: E402

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QLineEdit, QSlider, QTextEdit

from mdcx.controllers.main_window.config_binding import ConfigBinder, SettingBinding

APP = QApplication.instance() or QApplication([])


def test_config_binder_round_trips_nested_text_bool_float_and_slider_values():
    ui = SimpleNamespace(
        path=QLineEdit(),
        enabled=QCheckBox(),
        temperature=QDoubleSpinBox(),
        retries=QSlider(Qt.Orientation.Horizontal),
    )
    config = SimpleNamespace(
        path="D:/Media",
        enabled=True,
        nested=SimpleNamespace(temperature=0.25),
        retries=3,
    )
    binder = ConfigBinder(
        ui,
        [
            SettingBinding("path", "path", parser=lambda value: value.strip()),
            SettingBinding("enabled", "enabled"),
            SettingBinding("temperature", "nested.temperature", parser=float),
            SettingBinding("retries", "retries", parser=int),
        ],
    )

    binder.load(config)

    assert ui.path.text() == "D:/Media"
    assert ui.enabled.isChecked() is True
    assert ui.temperature.value() == 0.25
    assert ui.retries.value() == 3

    ui.path.setText("  E:/Library  ")
    ui.enabled.setChecked(False)
    ui.temperature.setValue(0.75)
    ui.retries.setValue(5)
    binder.save(config)

    assert config.path == "E:/Library"
    assert config.enabled is False
    assert config.nested.temperature == 0.75
    assert config.retries == 5
    assert APP is not None


def test_config_binder_supports_multiline_text_and_collection_formatters():
    ui = SimpleNamespace(prompt=QTextEdit(), extensions=QLineEdit())
    config = SimpleNamespace(prompt="第一行\n第二行", extensions=[".mp4", ".mkv"])
    binder = ConfigBinder(
        ui,
        [
            SettingBinding("prompt", "prompt"),
            SettingBinding(
                "extensions",
                "extensions",
                parser=lambda value: [part for part in value.split("|") if part],
                formatter="|".join,
            ),
        ],
    )

    binder.load(config)
    assert ui.prompt.toPlainText() == "第一行\n第二行"
    assert ui.extensions.text() == ".mp4|.mkv"

    ui.prompt.setPlainText("更新后的提示词")
    ui.extensions.setText(".avi|.wmv")
    binder.save(config)
    assert config.prompt == "更新后的提示词"
    assert config.extensions == [".avi", ".wmv"]
