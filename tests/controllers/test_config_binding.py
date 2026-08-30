# ruff: noqa: E402

import os
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QLineEdit, QRadioButton, QSlider, QTextEdit

from mdcx.controllers.main_window.config_binding import ChoiceBinding, ConfigBinder, SettingBinding
from mdcx.controllers.main_window.settings_page import (
    format_duration,
    is_valid_http_url,
    parse_duration,
    validate_name_template,
)
from mdcx.models.types import CrawlersResult, FileInfo

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


def test_choice_binding_round_trips_values_and_uses_declared_default():
    ui = SimpleNamespace(emby=QRadioButton(), jellyfin=QRadioButton())
    config = SimpleNamespace(server_type="jellyfin")
    binder = ConfigBinder(
        ui,
        [],
        choices=[ChoiceBinding("server_type", (("emby", "emby"), ("jellyfin", "jellyfin")), "emby")],
    )

    binder.load(config)
    assert ui.jellyfin.isChecked()

    ui.emby.setChecked(True)
    binder.save(config)
    assert config.server_type == "emby"

    config.server_type = "unsupported"
    binder.load(config)
    assert ui.emby.isChecked()


def test_duration_binding_rejects_invalid_minutes_instead_of_silent_fallback():
    assert parse_duration("12:34:56") == timedelta(hours=12, minutes=34, seconds=56)
    assert format_duration(timedelta(hours=1, minutes=2, seconds=3)) == "01:02:03"

    with pytest.raises(ValueError, match="无效时间"):
        parse_duration("12:99:00")
    with pytest.raises(ValueError, match="无效时间"):
        parse_duration("1:02:03")


@pytest.mark.parametrize("value", ["", "https://api.example.com/v1", "http://127.0.0.1:8000/v1"])
def test_http_url_validation_accepts_supported_urls(value: str):
    assert is_valid_http_url(value)


@pytest.mark.parametrize("value", ["api.example.com", "ftp://example.com", "https://bad host/v1"])
def test_http_url_validation_rejects_ambiguous_or_unsupported_urls(value: str):
    assert not is_valid_http_url(value)


def test_name_template_validation_reports_real_jinja_syntax_errors():
    file_info = FileInfo.empty()
    file_info.number = "ABC-123"
    file_info.file_path = Path("D:/Media/ABC-123.mp4")
    file_info.file_name = "ABC-123"
    result = CrawlersResult.empty()
    result.number = "ABC-123"
    result.title = "Title"

    assert validate_name_template("{{ number }} - {{ title }}", file_info, result) == ""
    assert validate_name_template("{% if studio %}{{ studio }}", file_info, result)
