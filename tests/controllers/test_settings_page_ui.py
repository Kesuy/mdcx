from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMainWindow

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.settings_page import SettingsPageController
from mdcx.views.MDCx import Ui_MDCx

APP = QApplication.instance() or QApplication([])


def _controller() -> tuple[QMainWindow, SettingsPageController]:
    window = QMainWindow()
    window.Ui = Ui_MDCx()
    window.Ui.setupUi(window)
    window.dark_mode = False
    window._build_name_preview_sample = MyMAinWindow._build_name_preview_sample.__get__(window, QMainWindow)
    MyMAinWindow._setup_fc2ppvdb_cookie_ui(window)
    MyMAinWindow._setup_baidu_translate_ui(window)
    controller = SettingsPageController(window)
    return window, controller


def test_api_keys_have_explicit_eye_toggle_buttons():
    window, controller = _controller()

    for field in (
        window.Ui.lineEdit_baidu_key,
        window.Ui.lineEdit_deepl_key,
        window.Ui.lineEdit_llm_key,
        window.Ui.lineEdit_api_token_theporndb,
        window.Ui.lineEdit_api_key,
    ):
        action = controller._secret_actions[field]
        assert not action.isChecked()
        action.trigger()
        assert field.echoMode() == field.EchoMode.Normal
        assert action.toolTip() == "隐藏密钥"
        action.trigger()
        assert field.echoMode() == field.EchoMode.Password


def test_ca_certificate_is_selected_with_file_picker(monkeypatch, tmp_path):
    window, controller = _controller()
    certificate = tmp_path / "proxy-ca.pem"
    certificate.write_text("certificate", encoding="utf-8")
    monkeypatch.setattr(
        "mdcx.controllers.main_window.settings_page.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (str(certificate), "CA 证书 (*.pem)"),
    )

    window.Ui.toolButton_select_ca_bundle.click()

    assert window.Ui.lineEdit_ca_bundle.isReadOnly()
    assert window.Ui.lineEdit_ca_bundle.text() == str(certificate)
    assert controller.validate().count("lineEdit_ca_bundle") == 0


def test_validation_reveals_the_exact_field_and_message():
    window, controller = _controller()
    network_tab = next(
        index
        for index in range(window.Ui.tabWidget.count())
        if window.Ui.tabWidget.widget(index).isAncestorOf(window.Ui.lineEdit_ca_bundle)
    )
    window.Ui.tabWidget.setCurrentIndex(0)
    controller._set_validation_error(window.Ui.lineEdit_ca_bundle, "找不到指定的 CA 证书文件")

    message = controller.reveal_validation_error("lineEdit_ca_bundle")

    assert message == "找不到指定的 CA 证书文件"
    assert window.Ui.tabWidget.currentIndex() == network_tab
    assert window.Ui.lineEdit_ca_bundle.property("validationError") is True


def test_website_help_button_and_network_controls_are_layout_managed():
    window, _controller_instance = _controller()

    assert window.Ui.widget_scrape_help_row.layout().indexOf(window.Ui.pushButton_scrape_note) >= 0
    assert window.Ui.groupBox_28.layout().indexOf(window.Ui.gridLayoutWidget_9) >= 0
    assert window.Ui.toolButton_select_ca_bundle.accessibleName() == "选择 CA 证书文件"


def test_nfo_help_button_is_part_of_the_first_field_row():
    window, _controller_instance = _controller()

    assert window.Ui.pushButton_field_tips_nfo.parentWidget() is window.Ui.layoutWidget_10
    assert window.Ui.horizontalLayout_135.indexOf(window.Ui.pushButton_field_tips_nfo) >= 0
