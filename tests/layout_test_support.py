import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMainWindow

from mdcx.controllers.main_window.init import setup_local_nfo_button, setup_result_sort_ui
from mdcx.views.MDCx import Ui_MDCx

APP = QApplication.instance() or QApplication([])


def generated_ui_window() -> QMainWindow:
    window = QMainWindow()
    window.Ui = Ui_MDCx()
    window.Ui.setupUi(window)
    window._sort_success_results = lambda: None
    window._toggle_result_sort_order = lambda: None
    window.main_load_nfo_click = lambda: None
    setup_result_sort_ui(window)
    setup_local_nfo_button(window)
    return window
