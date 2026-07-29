from PyQt6.QtWidgets import QApplication, QMainWindow

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.views.MDCx import Ui_MDCx

APP = QApplication.instance() or QApplication([])


def _setup_fc2cmadb_ui():
    window = QMainWindow()
    window.Ui = Ui_MDCx()
    window.Ui.setupUi(window)
    MyMAinWindow._setup_fc2ppvdb_cookie_ui(window)
    return window


def test_fc2cmadb_ui_only_exposes_manual_cookie_controls():
    window = _setup_fc2cmadb_ui()

    assert window.Ui.plainTextEdit_cookie_fc2ppvdb.placeholderText().startswith("登录 fc2cmadb 后")
    assert window.Ui.pushButton_check_fc2ppvdb_cookie.text() == "检查cookie"
    for removed_control in (
        "radioButton_fc2cmadb_manual",
        "radioButton_fc2cmadb_auto",
        "lineEdit_fc2cmadb_username",
        "lineEdit_fc2cmadb_password",
        "pushButton_fc2cmadb_login",
    ):
        assert not hasattr(window.Ui, removed_control)


def test_cookie_settings_visually_separate_each_website():
    window = _setup_fc2cmadb_ui()

    section_titles = [
        window.Ui.label_javdb_cookie_section,
        window.Ui.label_javbus_cookie_section,
        window.Ui.label_fc2cmadb_cookie_section,
    ]

    assert [label.text() for label in section_titles] == ["JavDB", "JavBus", "FC2CMADB"]
    assert all(label.styleSheet() for label in section_titles)
    assert [
        window.Ui.gridLayout_10.getItemPosition(window.Ui.gridLayout_10.indexOf(label))[0] for label in section_titles
    ] == [0, 4, 8]
    assert window.Ui.gridLayoutWidget_10.geometry().bottom() < window.Ui.label_75.geometry().top()
    assert window.Ui.label_get_cookie_url.geometry().bottom() < window.Ui.groupBox_10.height()
