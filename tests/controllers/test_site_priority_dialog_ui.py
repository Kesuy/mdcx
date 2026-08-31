# ruff: noqa: E402

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton

from mdcx.config.enums import FixedScrapingType, Website
from mdcx.controllers.main_window.site_priority_dialog import FieldPriorityDialog, SiteListEditorDialog

APP = QApplication.instance() or QApplication([])


def _parent(dark: bool = False) -> QDialog:
    parent = QDialog()
    parent.dark_mode = dark
    return parent


def _assert_dialog_buttons_are_consistent(dialog: QDialog) -> None:
    buttons = dialog.findChildren(QPushButton)
    assert buttons
    for button in buttons:
        assert button.minimumHeight() >= 30
        assert "border-radius: 8px" in button.styleSheet()
        assert "border-radius: 7px" not in button.styleSheet()


def test_site_editor_action_buttons_use_shared_height_and_radius():
    parent = _parent()
    dialog = SiteListEditorDialog(
        "编辑网站源",
        [Website.JAVDB],
        [Website.JAVDB, Website.JAVBUS],
        parent,
    )

    _assert_dialog_buttons_are_consistent(dialog)

    dialog.close()
    parent.close()


def test_field_priority_action_buttons_use_shared_height_and_radius_in_dark_mode():
    parent = _parent(dark=True)
    dialog = FieldPriorityDialog(
        "字段优先级",
        FixedScrapingType.YOUMA,
        [Website.JAVDB, Website.JAVBUS],
        {},
        parent,
    )

    _assert_dialog_buttons_are_consistent(dialog)

    dialog.close()
    parent.close()
