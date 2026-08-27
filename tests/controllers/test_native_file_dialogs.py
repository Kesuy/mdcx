# ruff: noqa: E402, I001

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QCheckBox, QFileDialog

from mdcx.config.enums import Switch
from mdcx.controllers.main_window.load_config import configure_native_file_dialogs


APP = QApplication.instance() or QApplication([])


def test_native_file_dialogs_ignore_legacy_qt_dialog_switch_without_losing_it():
    checkbox = QCheckBox()
    window = SimpleNamespace(Ui=SimpleNamespace(checkBox_dialog_qt=checkbox), options=None)

    configure_native_file_dialogs(window, [Switch.QT_DIALOG])

    assert checkbox.isChecked() is True
    assert checkbox.isHidden() is True
    assert window.options == QFileDialog.Option(0)
    assert not window.options & QFileDialog.Option.DontUseNativeDialog
