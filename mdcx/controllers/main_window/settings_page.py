from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from PyQt6.QtCore import QLocale, QRegularExpression
from PyQt6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mdcx.config.enums import CleanAction, HDPicSource, NoEscape
from mdcx.config.models import str_to_list
from mdcx.core.naming import NameRenderOptions, NamingTarget, render_name

from .config_binding import ChoiceBinding, ConfigBinder, MultiChoiceBinding, SettingBinding


def parse_duration(value: str) -> timedelta:
    if re.fullmatch(r"\d{2}:[0-5]\d:[0-5]\d", value) is None:
        raise ValueError(f"无效时间: {value}")
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def format_duration(value: timedelta) -> str:
    total_seconds = max(0, int(value.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{min(hours, 99):02d}:{minutes:02d}:{seconds:02d}"


def is_valid_http_url(value: str) -> bool:
    if not value.strip():
        return True
    parsed = urlsplit(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and " " not in parsed.netloc


def validate_name_template(template: str, file_info, result) -> str:
    if not template.strip():
        return ""
    try:
        render_name(
            template,
            file_info,
            result,
            NameRenderOptions(
                target=NamingTarget.FILE,
                show_definition_suffix=False,
                show_cnword_suffix=False,
                show_moword_suffix=False,
                max_length=120,
            ),
        )
    except Exception as error:
        return str(error)
    return ""


class SettingsPageController:
    """Own settings-only behavior kept out of the main window controller."""

    def __init__(self, window):
        self.window = window
        self.ui = window.Ui
        self._advanced_widgets: list[QWidget] = []
        self._validation_messages: dict[QLineEdit, QLabel] = {}
        self._setup_network_security()
        self._setup_secret_fields()
        self._setup_numeric_validation()
        self.binder = ConfigBinder(
            self.ui,
            [
                SettingBinding(
                    "lineEdit_movie_type",
                    "media_type",
                    parser=lambda value: str_to_list(value.lower(), "|"),
                    formatter="|".join,
                ),
                SettingBinding(
                    "lineEdit_sub_type",
                    "sub_type",
                    parser=lambda value: str_to_list(value, "|"),
                    formatter=lambda value: "|".join(value).replace(".txt|", ""),
                ),
                SettingBinding(
                    "lineEdit_escape_dir", "folders", parser=lambda value: str_to_list(value, ","), formatter=",".join
                ),
                SettingBinding(
                    "lineEdit_escape_string", "string", parser=lambda value: str_to_list(value, ","), formatter=",".join
                ),
                SettingBinding("lineEdit_escape_size", "file_size", parser=float),
                SettingBinding(
                    "lineEdit_clean_file_ext",
                    "clean_ext",
                    parser=lambda value: str_to_list(value, "|"),
                    formatter="|".join,
                ),
                SettingBinding(
                    "lineEdit_clean_file_name",
                    "clean_name",
                    parser=lambda value: str_to_list(value, "|"),
                    formatter="|".join,
                ),
                SettingBinding(
                    "lineEdit_clean_file_contains",
                    "clean_contains",
                    parser=lambda value: str_to_list(value, "|"),
                    formatter="|".join,
                ),
                SettingBinding("lineEdit_clean_file_size", "clean_size", parser=float),
                SettingBinding(
                    "lineEdit_clean_excluded_file_ext",
                    "clean_ignore_ext",
                    parser=lambda value: str_to_list(value, "|"),
                    formatter="|".join,
                ),
                SettingBinding(
                    "lineEdit_clean_excluded_file_contains",
                    "clean_ignore_contains",
                    parser=lambda value: str_to_list(value, "|"),
                    formatter="|".join,
                ),
                SettingBinding("lineEdit_movie_path", "media_path"),
                SettingBinding("lineEdit_movie_softlink_path", "softlink_path"),
                SettingBinding("lineEdit_success", "success_output_folder"),
                SettingBinding("lineEdit_fail", "failed_output_folder"),
                SettingBinding("lineEdit_extrafanart_dir", "extrafanart_folder", parser=lambda value: value.strip()),
                SettingBinding("checkBox_scrape_softlink_path", "scrape_softlink_path"),
                SettingBinding("lineEdit_nfo_tagline", "nfo_tagline"),
                SettingBinding("lineEdit_nfo_tag_series", "nfo_tag_series"),
                SettingBinding("lineEdit_nfo_tag_studio", "nfo_tag_studio"),
                SettingBinding("lineEdit_nfo_tag_publisher", "nfo_tag_publisher"),
                SettingBinding("lineEdit_nfo_tag_actor", "nfo_tag_actor"),
                SettingBinding(
                    "lineEdit_nfo_tag_actor_contains",
                    "nfo_tag_actor_contains",
                    parser=lambda value: str_to_list(value, "|"),
                    formatter="|".join,
                ),
                SettingBinding("lineEdit_baidu_appid", "translate_config.baidu_appid"),
                SettingBinding("lineEdit_baidu_key", "translate_config.baidu_key"),
                SettingBinding("lineEdit_deepl_key", "translate_config.deepl_key", parser=lambda value: value.strip()),
                SettingBinding(
                    "lineEdit_deeplx_url", "translate_config.deeplx_url", parser=lambda value: value.strip()
                ),
                SettingBinding("lineEdit_llm_model", "translate_config.llm_model"),
                SettingBinding("lineEdit_llm_key", "translate_config.llm_key"),
                SettingBinding("textEdit_llm_prompt_title", "translate_config.llm_prompt_title"),
                SettingBinding("textEdit_llm_prompt_outline", "translate_config.llm_prompt_outline"),
                SettingBinding("doubleSpinBox_llm_max_req_sec", "translate_config.llm_max_req_sec", parser=float),
                SettingBinding("spinBox_llm_max_try", "translate_config.llm_max_try", parser=int),
                SettingBinding("doubleSpinBox_llm_temperature", "translate_config.llm_temperature", parser=float),
                SettingBinding("horizontalSlider_thread", "thread_number", parser=int),
                SettingBinding("horizontalSlider_thread_time", "thread_time", parser=int),
                SettingBinding("horizontalSlider_javdb_time", "javdb_time", parser=int),
                SettingBinding("lineEdit_update_a_folder", "update_a_folder"),
                SettingBinding("lineEdit_update_b_folder", "update_b_folder"),
                SettingBinding("lineEdit_update_c_filetemplate", "update_c_filetemplate"),
                SettingBinding("lineEdit_update_d_folder", "update_d_folder"),
                SettingBinding("lineEdit_update_titletemplate", "update_titletemplate"),
                SettingBinding("checkBox_cover", "show_poster"),
                SettingBinding("checkBox_use_local_number_images", "use_local_number_images"),
                SettingBinding("lineEdit_dir_name", "folder_name"),
                SettingBinding("lineEdit_local_name", "naming_file"),
                SettingBinding("lineEdit_media_name", "naming_media"),
                SettingBinding("lineEdit_prevent_char", "prevent_char"),
                SettingBinding("lineEdit_actor_no_name", "actor_no_name"),
                SettingBinding("lineEdit_actor_name_more", "actor_name_more"),
                SettingBinding("lineEdit_release_rule", "release_rule"),
                SettingBinding(
                    "lineEdit_folder_name_max",
                    "folder_name_max",
                    parser=int,
                    formatter=lambda value: value if 0 < value <= 255 else 60,
                ),
                SettingBinding(
                    "lineEdit_file_name_max",
                    "file_name_max",
                    parser=int,
                    formatter=lambda value: value if 0 < value <= 255 else 60,
                ),
                SettingBinding("lineEdit_actor_name_max", "actor_name_max", parser=int),
                SettingBinding("lineEdit_umr_style", "umr_style"),
                SettingBinding("lineEdit_leak_style", "leak_style"),
                SettingBinding("lineEdit_wuma_style", "wuma_style"),
                SettingBinding("lineEdit_youma_style", "youma_style"),
                SettingBinding("checkBox_foldername_mosaic", "folder_moword"),
                SettingBinding("checkBox_filename_mosaic", "file_moword"),
                SettingBinding("checkBox_foldername_4k", "folder_hd"),
                SettingBinding("checkBox_filename_4k", "file_hd"),
                SettingBinding("checkBox_actor_realname", "actor_realname"),
                SettingBinding("checkBox_amazon_skip_poster_size_precheck", "amazon_skip_poster_size_precheck"),
                SettingBinding("checkBox_amazon_strict_pic_verify", "amazon_strict_pic_verify"),
                SettingBinding("lineEdit_sub_folder", "subtitle_folder"),
                SettingBinding("checkBox_sub_add_chs", "subtitle_add_chs"),
                SettingBinding("checkBox_sub_rescrape", "subtitle_add_rescrape"),
                SettingBinding("lineEdit_api_key", "api_key"),
                SettingBinding("lineEdit_user_id", "user_id"),
                SettingBinding("lineEdit_actor_photo_folder", "actor_photo_folder"),
                SettingBinding("lineEdit_actor_db_path", "info_database_path"),
                SettingBinding("checkBox_actor_db", "use_database"),
                SettingBinding("checkBox_actor_photo_kodi", "actor_photo_kodi_auto"),
                SettingBinding("plainTextEdit_cookie_javdb", "javdb"),
                SettingBinding("plainTextEdit_cookie_fc2ppvdb", "fc2ppvdb"),
                SettingBinding("plainTextEdit_cookie_javbus", "javbus"),
                SettingBinding("lineEdit_api_token_theporndb", "theporndb_api_token"),
                SettingBinding("lineEdit_rest_count", "rest_count", parser=int, formatter=lambda value: value or 1),
                SettingBinding("lineEdit_rest_time", "rest_time", parser=parse_duration, formatter=format_duration),
                SettingBinding(
                    "lineEdit_timed_interval", "timed_interval", parser=parse_duration, formatter=format_duration
                ),
                SettingBinding("checkBox_show_web_log", "show_web_log"),
                SettingBinding("checkBox_show_from_log", "show_from_log"),
                SettingBinding("checkBox_show_data_log", "show_data_log"),
                SettingBinding(
                    "lineEdit_local_library_path",
                    "local_library",
                    parser=lambda value: str_to_list(value),
                    formatter=",".join,
                ),
                SettingBinding("lineEdit_actors_name", "actors_name", parser=lambda value: value.replace("\n", "")),
                SettingBinding("lineEdit_netdisk_path", "netdisk_path"),
                SettingBinding("lineEdit_localdisk_path", "localdisk_path"),
                SettingBinding(
                    "checkBox_hide_window_title",
                    "window_title",
                    parser=lambda checked: "hide" if checked else "show",
                    formatter=lambda value: value == "hide",
                ),
                SettingBinding("checkBox_create_link", "auto_link"),
                SettingBinding("checkBox_use_proxy", "use_proxy"),
                SettingBinding("lineEdit_proxy", "proxy", parser=lambda value: value.strip()),
                SettingBinding("checkBox_verify_tls", "verify_tls"),
                SettingBinding("lineEdit_ca_bundle", "ca_bundle", parser=lambda value: value.strip()),
                SettingBinding("lineEdit_cf_bypass_url", "cf_bypass_url", parser=lambda value: value.strip()),
                SettingBinding("lineEdit_cf_bypass_proxy", "cf_bypass_proxy", parser=lambda value: value.strip()),
                SettingBinding("horizontalSlider_timeout", "timeout", parser=int),
                SettingBinding("horizontalSlider_retry", "retry", parser=int),
            ],
            choices=[
                ChoiceBinding(
                    "success_file_move",
                    (("radioButton_succ_move_on", True), ("radioButton_succ_move_off", False)),
                    False,
                ),
                ChoiceBinding(
                    "failed_file_move",
                    (("radioButton_fail_move_on", True), ("radioButton_fail_move_off", False)),
                    False,
                ),
                ChoiceBinding(
                    "success_file_rename",
                    (("radioButton_succ_rename_on", True), ("radioButton_succ_rename_off", False)),
                    False,
                ),
                ChoiceBinding(
                    "del_empty_folder",
                    (("radioButton_del_empty_folder_on", True), ("radioButton_del_empty_folder_off", False)),
                    False,
                ),
                ChoiceBinding(
                    "server_type",
                    (("radioButton_server_emby", "emby"), ("radioButton_server_jellyfin", "jellyfin")),
                    "emby",
                ),
                ChoiceBinding(
                    "save_log",
                    (("radioButton_log_on", True), ("radioButton_log_off", False)),
                    True,
                ),
                ChoiceBinding(
                    "update_check",
                    (("radioButton_update_on", True), ("radioButton_update_off", False)),
                    True,
                ),
            ],
            multi_choices=[
                MultiChoiceBinding(
                    "no_escape",
                    (
                        ("checkBox_no_escape_file", NoEscape.NO_SKIP_SMALL_FILE),
                        ("checkBox_no_escape_dir", NoEscape.FOLDER),
                        ("checkBox_skip_success_file", NoEscape.SKIP_SUCCESS_FILE),
                        ("checkBox_record_success_file", NoEscape.RECORD_SUCCESS_FILE),
                        ("checkBox_check_symlink", NoEscape.CHECK_SYMLINK),
                        ("checkBox_check_symlink_definition", NoEscape.SYMLINK_DEFINITION),
                    ),
                ),
                MultiChoiceBinding(
                    "clean_enable",
                    (
                        ("checkBox_clean_file_ext", CleanAction.CLEAN_EXT),
                        ("checkBox_clean_file_name", CleanAction.CLEAN_NAME),
                        ("checkBox_clean_file_contains", CleanAction.CLEAN_CONTAINS),
                        ("checkBox_clean_file_size", CleanAction.CLEAN_SIZE),
                        ("checkBox_clean_excluded_file_ext", CleanAction.CLEAN_IGNORE_EXT),
                        ("checkBox_clean_excluded_file_contains", CleanAction.CLEAN_IGNORE_CONTAINS),
                        ("checkBox_i_understand_clean", CleanAction.I_KNOW),
                        ("checkBox_i_agree_clean", CleanAction.I_AGREE),
                        ("checkBox_auto_clean", CleanAction.AUTO_CLEAN),
                    ),
                ),
                MultiChoiceBinding(
                    "download_hd_pics",
                    (("checkBox_amazon_big_pic", HDPicSource.AMAZON),),
                ),
            ],
        )

    def _setup_network_security(self) -> None:
        parent = self.ui.gridLayoutWidget_9
        self.ui.checkBox_verify_tls = QCheckBox("验证 HTTPS（推荐）", parent)
        self.ui.checkBox_verify_tls.setToolTip("仅在特殊代理环境中关闭；关闭后 API Key 和 Cookie 可能被窃取")
        self.ui.label_ca_bundle = QLabel("CA:", parent)
        self.ui.lineEdit_ca_bundle = QLineEdit(parent)
        self.ui.lineEdit_ca_bundle.setPlaceholderText("可选：PEM 格式 CA 文件路径")
        self.ui.lineEdit_ca_bundle.setMinimumWidth(140)
        self.ui.horizontalLayout_17.addWidget(self.ui.checkBox_verify_tls)
        self.ui.horizontalLayout_17.addWidget(self.ui.label_ca_bundle)
        self.ui.horizontalLayout_17.addWidget(self.ui.lineEdit_ca_bundle, 1)
        self._advanced_widgets.extend(
            [
                self.ui.label_ca_bundle,
                self.ui.lineEdit_ca_bundle,
                self.ui.label_cf_bypass,
                self.ui.lineEdit_cf_bypass_url,
                self.ui.label_cf_bypass_proxy,
                self.ui.lineEdit_cf_bypass_proxy,
                self.ui.label_73,
                self.ui.horizontalSlider_timeout,
                self.ui.lcdNumber_timeout,
                self.ui.label_65,
                self.ui.horizontalSlider_retry,
                self.ui.lcdNumber_retry,
                self.ui.groupBox_44,
            ]
        )

    def _setup_secret_fields(self) -> None:
        for name in (
            "lineEdit_baidu_key",
            "lineEdit_deepl_key",
            "lineEdit_llm_key",
            "lineEdit_api_token_theporndb",
            "lineEdit_api_key",
        ):
            widget = getattr(self.ui, name, None)
            if isinstance(widget, QLineEdit):
                widget.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
                widget.setToolTip("凭据优先保存到系统密钥库，配置导出不会包含明文")

    def _setup_numeric_validation(self) -> None:
        self._numeric_widgets: list[QLineEdit] = []
        self._format_widgets: dict[QLineEdit, str] = {}
        self._url_widgets: dict[QLineEdit, str] = {}
        self._template_widgets: list[QLineEdit] = []
        locale = QLocale.c()
        for name in ("lineEdit_escape_size", "lineEdit_clean_file_size"):
            widget = getattr(self.ui, name)
            validator = QDoubleValidator(0, 1_000_000_000, 3, widget)
            validator.setLocale(locale)
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            widget.setValidator(validator)
            self._numeric_widgets.append(widget)
        for name, maximum in (
            ("lineEdit_folder_name_max", 10_000),
            ("lineEdit_file_name_max", 10_000),
            ("lineEdit_actor_name_max", 1_000),
            ("lineEdit_rest_count", 1_000_000),
        ):
            widget = getattr(self.ui, name)
            widget.setValidator(QIntValidator(0, maximum, widget))
            self._numeric_widgets.append(widget)
        duration_expression = QRegularExpression(r"\d{2}:[0-5]\d:[0-5]\d")
        for name in ("lineEdit_rest_time", "lineEdit_timed_interval"):
            widget = getattr(self.ui, name)
            widget.setValidator(QRegularExpressionValidator(duration_expression, widget))
            self._format_widgets[widget] = "请按 HH:MM:SS 输入，分钟和秒必须小于 60"
        for name in ("lineEdit_llm_url", "lineEdit_deeplx_url", "lineEdit_cf_bypass_url"):
            widget = getattr(self.ui, name)
            self._url_widgets[widget] = "请输入完整的 http:// 或 https:// 地址"
        for name in (
            "lineEdit_dir_name",
            "lineEdit_local_name",
            "lineEdit_media_name",
            "lineEdit_update_c_filetemplate",
            "lineEdit_update_titletemplate",
        ):
            self._template_widgets.append(getattr(self.ui, name))
        for widget in (
            *self._numeric_widgets,
            *self._format_widgets,
            *self._url_widgets,
            *self._template_widgets,
            self.ui.lineEdit_ca_bundle,
        ):
            self._install_inline_error(widget)

    def _install_inline_error(self, widget: QLineEdit) -> None:
        parent = widget.parentWidget()
        parent_layout = parent.layout() if parent is not None else None
        if parent_layout is None:
            return

        container = QWidget(parent)
        container.setObjectName(f"{widget.objectName()}_validation_container")
        stack = QVBoxLayout(container)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(2)
        replaced = parent_layout.replaceWidget(widget, container)
        if replaced is None:
            container.deleteLater()
            return
        widget.setParent(container)
        stack.addWidget(widget)
        message = QLabel(container)
        message.setProperty("validationMessage", True)
        message.setWordWrap(True)
        message.hide()
        stack.addWidget(message)
        self._validation_messages[widget] = message

    def _set_validation_error(self, widget: QLineEdit, message: str = "") -> None:
        has_error = bool(message)
        widget.setProperty("validationError", has_error)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        label = self._validation_messages.get(widget)
        if label is not None:
            label.setText(message)
            label.setVisible(has_error)

    def validate(self) -> list[str]:
        errors = []
        for widget in self._numeric_widgets:
            acceptable = widget.hasAcceptableInput() and bool(widget.text().strip())
            if not acceptable:
                self._set_validation_error(widget, "请输入有效的非负数字")
                errors.append(widget.objectName())
            else:
                self._set_validation_error(widget)
        for widget, message in self._format_widgets.items():
            if not widget.hasAcceptableInput():
                self._set_validation_error(widget, message)
                errors.append(widget.objectName())
            else:
                self._set_validation_error(widget)
        for widget, message in self._url_widgets.items():
            if not is_valid_http_url(widget.text()):
                self._set_validation_error(widget, message)
                errors.append(widget.objectName())
            else:
                self._set_validation_error(widget)
        file_info, result = self.window._build_name_preview_sample()
        for widget in self._template_widgets:
            message = validate_name_template(widget.text(), file_info, result)
            if message:
                self._set_validation_error(widget, f"命名模板语法错误：{message}")
                errors.append(widget.objectName())
            else:
                self._set_validation_error(widget)
        ca_path = self.ui.lineEdit_ca_bundle.text().strip()
        if ca_path and not Path(ca_path).expanduser().is_file():
            self._set_validation_error(self.ui.lineEdit_ca_bundle, "找不到指定的 CA 证书文件")
            errors.append("lineEdit_ca_bundle")
        else:
            self._set_validation_error(self.ui.lineEdit_ca_bundle)
        return errors

    def install_search_bar(self, layout) -> None:
        if hasattr(self.ui, "lineEdit_settings_search"):
            return
        bar = QWidget(self.ui.page_setting)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        self.ui.lineEdit_settings_search = QLineEdit(bar)
        self.ui.lineEdit_settings_search.setPlaceholderText("搜索设置，例如：代理、命名、NFO")
        self.ui.toolButton_advanced_settings = QToolButton(bar)
        self.ui.toolButton_advanced_settings.setText("显示高级设置")
        self.ui.toolButton_advanced_settings.setCheckable(True)
        row.addWidget(self.ui.lineEdit_settings_search, 1)
        row.addWidget(self.ui.toolButton_advanced_settings)
        layout.insertWidget(0, bar)
        self.ui.lineEdit_settings_search.textChanged.connect(self._search)
        self.ui.toolButton_advanced_settings.toggled.connect(self._toggle_advanced)
        self._toggle_advanced(False)

    def _toggle_advanced(self, visible: bool) -> None:
        self.ui.toolButton_advanced_settings.setText("隐藏高级设置" if visible else "显示高级设置")
        for widget in self._advanced_widgets:
            widget.setVisible(visible)

    def _search(self, query: str) -> None:
        query = query.strip().casefold()
        if not query:
            self._toggle_advanced(self.ui.toolButton_advanced_settings.isChecked())
            return

        for tab_index in range(self.ui.tabWidget.count()):
            tab = self.ui.tabWidget.widget(tab_index)
            text_parts = [self.ui.tabWidget.tabText(tab_index)]
            for label in tab.findChildren(QLabel):
                text_parts.append(label.text())
            for group in tab.findChildren(QGroupBox):
                text_parts.append(group.title())
            if query in " ".join(text_parts).casefold():
                self.ui.tabWidget.setCurrentIndex(tab_index)
                break
        for widget in self._advanced_widgets:
            widget.setVisible(True)
