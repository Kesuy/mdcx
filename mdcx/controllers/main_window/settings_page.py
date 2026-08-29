from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QWidget,
)

from .config_binding import ConfigBinder, SettingBinding


class SettingsPageController:
    """Own settings-only behavior kept out of the main window controller."""

    def __init__(self, window):
        self.window = window
        self.ui = window.Ui
        self._advanced_widgets: list[QWidget] = []
        self._setup_network_security()
        self._setup_secret_fields()
        self._setup_numeric_validation()
        self.binder = ConfigBinder(
            self.ui,
            [
                SettingBinding("checkBox_use_proxy", "use_proxy"),
                SettingBinding("lineEdit_proxy", "proxy", parser=lambda value: value.strip()),
                SettingBinding("checkBox_verify_tls", "verify_tls"),
                SettingBinding("lineEdit_ca_bundle", "ca_bundle", parser=lambda value: value.strip()),
                SettingBinding("lineEdit_cf_bypass_url", "cf_bypass_url", parser=lambda value: value.strip()),
                SettingBinding("lineEdit_cf_bypass_proxy", "cf_bypass_proxy", parser=lambda value: value.strip()),
                SettingBinding("horizontalSlider_timeout", "timeout", parser=int),
                SettingBinding("horizontalSlider_retry", "retry", parser=int),
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

    def validate(self) -> list[str]:
        errors = []
        for widget in self._numeric_widgets:
            acceptable = widget.hasAcceptableInput() and bool(widget.text().strip())
            widget.setProperty("validationError", not acceptable)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            if not acceptable:
                widget.setToolTip("请输入有效的非负数字")
                errors.append(widget.objectName())
        ca_path = self.ui.lineEdit_ca_bundle.text().strip()
        if ca_path and not Path(ca_path).expanduser().is_file():
            self.ui.lineEdit_ca_bundle.setToolTip("找不到指定的 CA 证书文件")
            errors.append("lineEdit_ca_bundle")
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
