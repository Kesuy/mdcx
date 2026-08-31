from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QGroupBox, QMainWindow, QVBoxLayout

from mdcx.config.enums import EmbyAction, FieldRule, MarkType, NfoInclude, Switch, TagInclude
from mdcx.config.manager import manager
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


def test_every_settings_group_uses_a_qt_layout():
    window, _controller_instance = _controller()

    groups = window.Ui.page_setting.findChildren(QGroupBox)
    assert len(groups) >= 50
    assert all(group.layout() is not None for group in groups)


def test_nfo_help_button_is_part_of_the_first_field_row():
    window, _controller_instance = _controller()

    assert window.Ui.pushButton_field_tips_nfo.parentWidget() is window.Ui.layoutWidget_10
    assert window.Ui.horizontalLayout_135.indexOf(window.Ui.pushButton_field_tips_nfo) >= 0


def test_disabled_clean_size_rule_does_not_require_a_value():
    window, controller = _controller()
    window.Ui.checkBox_clean_file_size.setChecked(False)
    window.Ui.lineEdit_clean_file_size.clear()

    errors = controller.validate()

    assert "lineEdit_clean_file_size" not in errors
    assert not window.Ui.lineEdit_clean_file_size.isEnabled()


def test_enabled_clean_size_rule_requires_a_valid_non_negative_number():
    window, controller = _controller()
    window.Ui.checkBox_clean_file_size.setChecked(True)
    window.Ui.lineEdit_clean_file_size.clear()

    errors = controller.validate()

    assert "lineEdit_clean_file_size" in errors
    assert window.Ui.lineEdit_clean_file_size.property("validationError") is True


def test_advanced_settings_visibility_is_saved_and_restored(monkeypatch):
    monkeypatch.setattr(manager.config, "show_advanced_settings", False)
    save_calls = []
    monkeypatch.setattr(manager, "save", lambda: save_calls.append(manager.config.show_advanced_settings))
    window, controller = _controller()
    controller.install_search_bar(QVBoxLayout())
    controller.binder.load(manager.config)

    assert not window.Ui.toolButton_advanced_settings.isChecked()
    assert all(widget.isHidden() for widget in controller._advanced_widgets)

    window.Ui.toolButton_advanced_settings.click()

    assert manager.config.show_advanced_settings is True
    assert save_calls == [True]

    restored_window, restored_controller = _controller()
    restored_controller.install_search_bar(QVBoxLayout())
    restored_controller.binder.load(manager.config)
    assert restored_window.Ui.toolButton_advanced_settings.isChecked()

    restored_window.close()
    window.close()


def test_composite_settings_schema_round_trips_nfo_emby_watermark_and_switches():
    window, controller = _controller()
    controller.install_search_bar(QVBoxLayout())
    config = manager.config.model_copy(deep=True)
    config.nfo_include_new = [NfoInclude.TITLE_CD]
    config.nfo_tag_include = [TagInclude.ACTOR, TagInclude.DEFINITION]
    config.fields_rule = [FieldRule.DEL_NUM]
    config.emby_on = [
        EmbyAction.ACTOR_INFO_ZH_TW,
        EmbyAction.ACTOR_INFO_ALL,
        EmbyAction.ACTOR_PHOTO_NET,
        EmbyAction.ACTOR_PHOTO_MISS,
        EmbyAction.ACTOR_REPLACE,
    ]
    config.mark_type = [MarkType.SUB, MarkType.HD]
    config.mark_fixed = "corner"
    config.mark_pos_hd = "top_right"
    config.switch_on = [Switch.DARK_MODE, Switch.HIDE_MINI, Switch.SHOW_LOGS]

    controller.binder.load(config)

    assert window.Ui.checkBox_nfo_title_cd.isChecked()
    assert not window.Ui.checkBox_nfo_actor.isChecked()
    assert window.Ui.radioButton_actor_info_zh_tw.isChecked()
    assert window.Ui.radioButton_actor_info_all.isChecked()
    assert window.Ui.radioButton_actor_photo_net.isChecked()
    assert window.Ui.checkBox_actor_pic_replace.isChecked()
    assert window.Ui.radioButton_fixed_corner.isChecked()
    assert window.Ui.radioButton_top_right_hd.isChecked()
    assert window.Ui.radioButton_hide_mini.isChecked()

    window.Ui.checkBox_nfo_title_cd.setChecked(False)
    window.Ui.checkBox_nfo_actor.setChecked(True)
    window.Ui.radioButton_actor_info_ja.setChecked(True)
    window.Ui.radioButton_actor_info_miss.setChecked(True)
    window.Ui.radioButton_actor_photo_local.setChecked(True)
    window.Ui.radioButton_actor_photo_all.setChecked(True)
    window.Ui.radioButton_fixed_position.setChecked(True)
    window.Ui.radioButton_bottom_left_hd.setChecked(True)
    window.Ui.radioButton_hide_none.setChecked(True)
    window.Ui.textBrowser_log_main_2.hide()
    controller.binder.save(config)

    assert config.nfo_include_new == [NfoInclude.ACTOR]
    assert EmbyAction.ACTOR_INFO_JA in config.emby_on
    assert EmbyAction.ACTOR_INFO_MISS in config.emby_on
    assert EmbyAction.ACTOR_PHOTO_LOCAL in config.emby_on
    assert EmbyAction.ACTOR_PHOTO_ALL in config.emby_on
    assert config.mark_fixed == "fixed"
    assert config.mark_pos_hd == "bottom_left"
    assert Switch.HIDE_NONE in config.switch_on
    assert Switch.SHOW_LOGS not in config.switch_on
