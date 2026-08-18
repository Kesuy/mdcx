# ruff: noqa: E402, I001

import os
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel

from mdcx.controllers.main_window.ui_text import set_elided_label_text


_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_set_elided_label_text_keeps_long_number_when_width_is_sufficient():
    _app()
    label = QLabel()
    label.resize(260, 40)
    number = "FC2-PPV-1234567890"

    set_elided_label_text(label, number)

    assert label.text() == number
    assert label.toolTip() == number
    assert label.property("mdcxFullText") == number


def test_set_elided_label_text_preserves_both_ends_when_space_is_tight():
    _app()
    label = QLabel()
    label.resize(95, 40)
    number = "FC2-PPV-1234567890"

    set_elided_label_text(label, number)

    assert "…" in label.text()
    prefix, suffix = label.text().split("…", 1)
    assert number.startswith(prefix)
    assert number.endswith(suffix)
    assert label.toolTip() == number


def test_main_ui_allocates_more_space_for_number_without_overlapping_actor_label():
    ui_path = Path(__file__).parents[2] / "mdcx" / "views" / "MDCx.ui"
    root = ET.parse(ui_path).getroot()

    def geometry(name: str) -> dict[str, int]:
        widget = root.find(f".//widget[@name='{name}']")
        assert widget is not None
        rect = widget.find("./property[@name='geometry']/rect")
        assert rect is not None
        return {child.tag: int(child.text or 0) for child in rect}

    number = geometry("label_number")
    actor_label = geometry("label_actor1")

    assert number["width"] >= 211
    assert number["x"] + number["width"] <= actor_label["x"]
