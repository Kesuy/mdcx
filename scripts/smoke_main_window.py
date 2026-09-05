"""Construct the real main window without entering the Qt event loop."""

import os

os.environ.setdefault("MDCX_OFFLINE", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from mdcx.controllers.main_window.main_window import MyMAinWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    # Keep CI deterministic: this smoke covers construction and controller/UI
    # wiring, while configuration migration has its own round-trip tests.
    MyMAinWindow.load_config = lambda self: None
    MyMAinWindow._finish_startup = lambda self: None
    window = MyMAinWindow()
    assert window.Ui.centralwidget is not None
    assert window.Ui.stackedWidget.count() >= 6
    print("MDCx main window construction smoke test passed")
    window.deleteLater()
    del app


if __name__ == "__main__":
    main()
