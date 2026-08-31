from typing import TYPE_CHECKING

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)

from mdcx.config.resources import resources


def _qss_resources(style: str) -> str:
    """将 QSS 中的相对资源路径替换为 Qt 可识别的绝对路径。"""
    return (
        style.replace("url(resources/Img/check_indicator.svg)", f"url({resources.qtr('Img/check_indicator.svg')})")
        .replace("url(resources/Img/radio_indicator.svg)", f"url({resources.qtr('Img/radio_indicator.svg')})")
        .replace("url(resources/Img/chevron_down_light.svg)", f"url({resources.qtr('Img/chevron_down_light.svg')})")
        .replace("url(resources/Img/chevron_down_dark.svg)", f"url({resources.qtr('Img/chevron_down_dark.svg')})")
    )


if TYPE_CHECKING:
    from .main_window import MyMAinWindow


LIGHT_TOKENS = {
    "window": "#FFFFFF",
    "surface": "#F8FAFC",
    "surface_muted": "#F5F7FF",
    "text": "#111827",
    "text_muted": "#4B5563",
    "text_disabled": "#9AA3AF",
    "placeholder": "#6B7280",
    "border": "#D8DEE9",
    "accent": "#4C6EFF",
    "accent_hover": "#6684FF",
    "accent_pressed": "#3F5FE6",
    "link": "#0B63CE",
    "link_hover": "#084A9C",
    "selection_bg": "rgba(76, 110, 255, 42)",
    "selection_bg_inactive": "rgba(76, 110, 255, 34)",
    "selection_text": "#111827",
    "tree_hover": "rgba(76, 110, 255, 18)",
    "tree_border": "rgba(76, 110, 255, 170)",
    "on_accent": "#FFFFFF",
    "input_bg": "#FFFFFF",
    "navigation": "#F5F7FF",
    "danger": "#C62828",
    "warning": "#B26A00",
    "success": "#12805C",
    "radius_sm": "4px",
    "radius_md": "8px",
    "radius_lg": "10px",
}

DARK_TOKENS = {
    "window": "#121A24",
    "surface": "#18222D",
    "surface_muted": "#1D2834",
    "text": "#E5E7EB",
    "text_muted": "#B6C2D0",
    "text_disabled": "#6B7280",
    "placeholder": "#94A3B8",
    "border": "#2F3A46",
    "accent": "#6684FF",
    "accent_hover": "#8EA3FF",
    "accent_pressed": "#4C6EE0",
    "link": "#9DB7FF",
    "link_hover": "#C3D2FF",
    "selection_bg": "rgba(102, 132, 255, 80)",
    "selection_bg_inactive": "rgba(102, 132, 255, 58)",
    "selection_text": "#FFFFFF",
    "tree_hover": "rgba(102, 132, 255, 34)",
    "tree_border": "rgba(142, 163, 255, 190)",
    "on_accent": "#FFFFFF",
    "input_bg": "#18222D",
    "navigation": "#1F272F",
    "danger": "#FF7B7B",
    "warning": "#F2B35D",
    "success": "#58C69A",
    "radius_sm": "4px",
    "radius_md": "8px",
    "radius_lg": "10px",
}


def _tokens(dark: bool) -> dict[str, str]:
    return DARK_TOKENS if dark else LIGHT_TOKENS


def get_theme_tokens(dark: bool) -> dict[str, str]:
    return _tokens(dark)


def _theme_qss(style: str, dark: bool) -> str:
    """Resolve legacy color literals through the semantic theme palette."""
    t = _tokens(dark)
    replacements = {
        "#4C6EFF": t["accent"],
        "#6684FF": t["accent"] if dark else t["accent_hover"],
        "#8EA3FF": t["accent_hover"],
        "#4C6EE0": t["accent_pressed"],
        "#3F5FE6": t["accent_pressed"],
        "#D8DEE9": t["border"],
        "#2F3A46": t["border"],
        "#111827": t["text"],
        "#E5E7EB": t["text"],
        "#FFFFFF": t["on_accent"],
        "#18222D": t["surface"],
        "#1D2834": t["surface_muted"],
        "#1F272F": t["navigation"],
    }
    for literal, value in replacements.items():
        style = style.replace(literal, value)
    return style


def apply_application_palette(dark: bool) -> None:
    app = QApplication.instance()
    if app is None:
        return

    t = _tokens(dark)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(t["window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(t["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(t["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(t["surface_muted"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(t["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(t["surface_muted"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(t["text"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(t["surface"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(t["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(t["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(t["on_accent"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(t["link"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["placeholder"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(t["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, QColor(t["surface"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, QColor(t["surface_muted"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(t["surface_muted"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(t["text_disabled"]))
    try:
        palette.setColor(QPalette.ColorRole.Accent, QColor(t["accent"]))
    except AttributeError:
        pass
    app.setPalette(palette)


def build_tree_widget_style(dark: bool) -> str:
    t = _tokens(dark)
    return f"""
        QTreeWidget, QTreeView {{
            outline: 0;
            border: 0;
            color: {t["text"]};
            background: transparent;
            alternate-background-color: transparent;
            selection-background-color: transparent;
            selection-color: {t["selection_text"]};
        }}
        QTreeWidget::item, QTreeView::item {{
            color: {t["text"]};
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 2px 4px;
        }}
        QTreeWidget::item:hover, QTreeView::item:hover {{
            color: {t["text"]};
            background: {t["tree_hover"]};
            border: 1px solid {t["tree_border"]};
        }}
        QTreeWidget::item:selected, QTreeView::item:selected,
        QTreeWidget::item:selected:active, QTreeView::item:selected:active {{
            color: {t["selection_text"]};
            background: {t["selection_bg"]};
            border: 1px solid {t["tree_border"]};
        }}
        QTreeWidget::item:selected:!active, QTreeView::item:selected:!active {{
            color: {t["selection_text"]};
            background: {t["selection_bg_inactive"]};
            border: 1px solid {t["tree_border"]};
        }}
        QTreeWidget::branch, QTreeView::branch {{
            background: transparent;
            border: 0;
            image: none;
        }}
        QTreeWidget::branch:selected, QTreeView::branch:selected {{
            background: transparent;
            image: none;
        }}
    """


def build_menu_style(dark: bool) -> str:
    t = _tokens(dark)
    return f"""
        QMenu {{
            color: {t["text"]};
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            padding: 4px;
        }}
        QMenu::item {{
            color: {t["text"]};
            padding: 5px 28px 5px 24px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            color: #FFFFFF;
            background: {t["accent"]};
        }}
        QMenu::item:disabled {{
            color: {t["text_disabled"]};
        }}
        QMenu::separator {{
            height: 1px;
            background: {t["border"]};
            margin: 4px 8px;
        }}
    """


def build_scrollbar_style(dark: bool) -> str:
    handle = "#4B5563" if dark else "#CBD5E1"
    handle_hover = "#64748B" if dark else "#94A3B8"
    return f"""
        QScrollBar:vertical{{
            width: 10px;
            margin: 0;
            background: transparent;
        }}
        QScrollBar::handle:vertical{{
            min-height: 32px;
            border-radius: 5px;
            background: {handle};
        }}
        QScrollBar::handle:vertical:hover{{
            background: {handle_hover};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical{{
            height: 0;
            background: transparent;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{{
            background: transparent;
        }}
        QScrollBar:horizontal{{
            height: 10px;
            margin: 0;
            background: transparent;
        }}
        QScrollBar::handle:horizontal{{
            min-width: 32px;
            border-radius: 5px;
            background: {handle};
        }}
        QScrollBar::handle:horizontal:hover{{
            background: {handle_hover};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal{{
            width: 0;
            background: transparent;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal{{
            background: transparent;
        }}
    """


def build_validation_style(dark: bool) -> str:
    t = _tokens(dark)
    return f"""
        QLineEdit[validationError="true"] {{
            border: 1px solid {t["danger"]};
        }}
        QLabel[validationMessage="true"] {{
            color: {t["danger"]};
            font-size: 11px;
            padding: 0 2px;
        }}
    """


def build_sidebar_background_style(dark: bool, radius: int) -> str:
    t = _tokens(dark)
    return (
        f"background: {t['navigation']};"
        f"border-right: 1px solid {t['border']};"
        f"border-top-left-radius: {radius}px;"
        f"border-bottom-left-radius: {radius}px;"
    )


def build_sidebar_button_style(object_name: str, dark: bool, *, active: bool = False) -> str:
    t = _tokens(dark)
    background = t["selection_bg"] if active else "transparent"
    weight = "600" if active else "400"
    return f"""
        QPushButton#{object_name} {{
            color: {t["text"]};
            background: {background};
            font-weight: {weight};
        }}
        QPushButton#{object_name}:hover {{
            color: {t["text"]};
            background: {t["tree_hover"]};
        }}
    """


def build_action_button_style(object_name: str, dark: bool, *, danger: bool = False) -> str:
    t = _tokens(dark)
    normal = t["danger"] if danger else t["accent"]
    hover = t["warning"] if danger else t["accent_hover"]
    pressed = t["danger"] if danger else t["accent_pressed"]
    return f"""
        QPushButton#{object_name} {{ color: {t["on_accent"]}; background: {normal}; }}
        QPushButton#{object_name}:hover {{ color: {t["on_accent"]}; background: {hover}; }}
        QPushButton#{object_name}:pressed {{ color: {t["on_accent"]}; background: {pressed}; }}
    """


def build_status_text_style(dark: bool, state: str = "neutral") -> str:
    t = _tokens(dark)
    color = t.get(state, t["text_muted"])
    return f"color: {color};"


def build_section_title_style(dark: bool, *, separated: bool = False) -> str:
    t = _tokens(dark)
    border = f"border-top: 1px solid {t['border']};" if separated else ""
    return f"font-weight: 600; color: {t['success']}; padding: 6px 2px 2px; {border}"


def build_code_editor_style(dark: bool) -> str:
    t = _tokens(dark)
    return (
        f"color: {t['text']}; background: {t['input_bg']}; "
        f"border: 1px solid {t['border']}; border-radius: {t['radius_sm']}; font-family: Courier;"
    )


def set_semantic_property(widget: QWidget, name: str, value: object) -> None:
    """Update a semantic style property and refresh only the affected widget."""
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def build_sidebar_style(dark: bool, radius: int) -> str:
    t = _tokens(dark)
    return f"""
        QWidget#widget_setting {{
            background: {t["navigation"]};
            border-right: 1px solid {t["border"]};
            border-top-left-radius: {radius}px;
            border-bottom-left-radius: {radius}px;
            border-top-right-radius: 0;
            border-bottom-right-radius: 0;
        }}
        QPushButton#pushButton_main, QPushButton#pushButton_log,
        QPushButton#pushButton_tool, QPushButton#pushButton_setting,
        QPushButton#pushButton_net, QPushButton#pushButton_about {{
            font-size: 14px;
            color: {t["text"]};
            border: 0;
            border-radius: {t["radius_lg"]};
            text-align: left;
            qproperty-iconSize: 20px 20px;
            padding-left: 20px;
        }}
        QLabel#label_show_version {{
            font-size: 13px;
            color: {t["text_muted"]};
            border: 0;
        }}
    """


def build_shell_splitter_style(dark: bool) -> str:
    """Paint the internal seam with opaque theme colors at every pixel."""
    t = _tokens(dark)
    return f"""
        QSplitter#window_shell_splitter {{
            background: {t["input_bg"]};
            border: 0;
        }}
        QSplitter#window_shell_splitter::handle:horizontal {{
            background: {t["border"]};
        }}
    """


def build_window_chrome_style(dark: bool) -> str:
    t = _tokens(dark)
    return f"""
        QPushButton#pushButton_close {{
            color: {t["danger"]}; background: {t["danger"]};
            border: 0; border-radius: {t["radius_md"]}; margin: 2px;
            font: 900 14pt Tahoma;
        }}
        QPushButton#pushButton_close:hover {{ color: {t["text"]}; background: {t["danger"]}; }}
        QPushButton#pushButton_min {{
            color: {t["warning"]}; background: {t["warning"]};
            border: 0; border-radius: {t["radius_md"]}; margin: 2px;
            font: 900 14pt Tahoma;
        }}
        QPushButton#pushButton_min:hover {{ color: {t["text"]}; background: {t["warning"]}; }}
        QProgressBar#progressBar_scrape {{
            border: 0; border-radius: 0; text-align: center; background: transparent;
        }}
        QProgressBar#progressBar_scrape::chunk {{ background: {t["accent"]}; width: 3px; }}
    """


def build_main_page_style(dark: bool) -> str:
    t = _tokens(dark)
    return f"""
        QLabel#label_number1, QLabel#label_actor1, QLabel#label_title1,
        QLabel#label_poster1, QLabel#label_number, QLabel#label_actor,
        QLabel#label_title {{
            color: {t["text"]};
            font-size: 16px;
            font-weight: 600;
            background: transparent;
            border: 0;
        }}
        QLabel#label_18, QLabel#label_33, QLabel#label_13, QLabel#label_22,
        QLabel#label_23, QLabel#label_31, QLabel#label_30, QLabel#label_24 {{
            color: {t["text"]};
            font-size: 14px;
            font-weight: 500;
        }}
        QLabel#label_outline, QLabel#label_tag, QLabel#label_release,
        QLabel#label_runtime, QLabel#label_director, QLabel#label_series,
        QLabel#label_studio, QLabel#label_publish {{
            color: {t["text"]};
            font-size: 14px;
            font-weight: 400;
        }}
        QLabel#label_file_path {{
            color: {t["text"]};
            font-size: 14px;
            font-weight: 500;
            background: transparent;
            border: 0;
        }}
        QLabel#label_poster_size, QLabel#label_thumb_size {{ color: {t["text_muted"]}; }}
        QLabel#label_poster, QLabel#label_thumb {{ border: 1px solid {t["border"]}; }}
        QGroupBox {{ background: transparent; }}
    """


def build_tool_page_style(dark: bool) -> str:
    t = _tokens(dark)
    card_background = "rgba(180, 180, 180, 20)" if dark else "#F5F5F6"
    return f"""
        * {{ color: {t["text"]}; font-size: 13px; }}
        QWidget#page_tool, QScrollArea#scrollArea_10,
        QScrollArea#scrollArea_10 QWidget#qt_scrollarea_viewport,
        QWidget#scrollAreaWidgetContents_gongju {{
            background: {t["input_bg"]};
            border: 0;
        }}
        QLabel {{ border: 0; }}
        QLabel[toolRole="help"] {{ color: {t["success"]}; background: transparent; }}
        QLineEdit {{
            color: {t["text"]};
            background: {t["input_bg"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius_md"]};
            padding: 0 10px;
        }}
        QComboBox {{ color: {t["text"]}; combobox-popup: 0; }}
        QGroupBox {{
            color: {t["text"]};
            background: {card_background};
            border: 0;
            border-radius: {t["radius_lg"]};
            margin-top: 0;
            padding-top: 8px;
            font-weight: 500;
        }}
        QGroupBox::title {{
            subcontrol-origin: border;
            subcontrol-position: top left;
            left: 14px;
            top: 8px;
            padding: 0 4px;
            background: transparent;
        }}
        QPushButton[toolRole="secondary"] {{
            color: {t["text"]};
            background: {t["input_bg"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius_md"]};
            padding: 0 12px;
        }}
        QPushButton[toolRole="secondary"]:hover {{
            color: {t["accent"]};
            border-color: {t["accent"]};
        }}
        QPushButton[toolRole="primary"] {{
            color: {t["on_accent"]};
            background: {t["accent"]};
            border: 1px solid {t["accent"]};
            border-radius: {t["radius_md"]};
            font-weight: 500;
        }}
        QPushButton[toolRole="primary"]:hover {{
            background: {t["accent_hover"]};
            border-color: {t["accent_hover"]};
        }}
        QPushButton[toolRole="primary"]:pressed {{
            background: {t["accent_pressed"]};
            border-color: {t["accent_pressed"]};
        }}
    """


def build_about_page_style(dark: bool) -> str:
    t = _tokens(dark)
    return f"""
        * {{ color: {t["text"]}; font-size: 13px; }}
        QTextBrowser {{
            color: {t["text"]};
            background: transparent;
            border: 0;
            padding: 2px;
            font-family: 'Microsoft YaHei UI', 'Segoe UI Variable', 'PingFang SC',
                         'Noto Sans CJK SC', 'Segoe UI';
        }}
    """


def _normalize_form_control_radius(self: "MyMAinWindow") -> None:
    """Expose the shared radius as metadata without creating inline QSS."""
    selector_types = (
        (QLineEdit, "QLineEdit"),
        (QComboBox, "QComboBox"),
        (QAbstractSpinBox, "QAbstractSpinBox"),
        (QPlainTextEdit, "QPlainTextEdit"),
        (QTextEdit, "QTextEdit"),
    )
    for widget_type, _selector in selector_types:
        for widget in self.findChildren(widget_type):
            widget.setProperty("mdcxControlRadius", 8)


def _adopt_settings_semantic_styles(self: "MyMAinWindow") -> None:
    """Convert Designer-era color QSS into stable semantic widget roles."""
    if self.Ui.page_setting.property("mdcxSemanticStylesAdopted"):
        return
    for widget in self.Ui.page_setting.findChildren(QWidget):
        legacy_style = widget.styleSheet().strip()
        if not legacy_style:
            continue
        compact = legacy_style.replace(" ", "").lower()
        role = None
        if isinstance(widget, QLabel):
            if "255,38,0" in compact:
                role = "danger"
            elif "10,52,255" in compact:
                role = "link"
            elif "8,128,128" in compact:
                role = "help"
        elif isinstance(widget, QPushButton) and "background-color:rgba(255,255,255,0)" in compact:
            role = "ghost"
        elif isinstance(widget, (QLineEdit, QPlainTextEdit, QTextEdit)):
            role = "code" if "courier" in compact else "input"
        if role is not None:
            widget.setProperty("semanticRole", role)
        widget.setProperty("mdcxLegacyInlineStyle", legacy_style)
        widget.setStyleSheet("")
    self.Ui.page_setting.setProperty("mdcxSemanticStylesAdopted", True)


def _settings_semantic_style(dark: bool) -> str:
    t = _tokens(dark)
    return f"""
        QLabel[semanticRole="help"] {{ color: {t["success"]}; }}
        QLabel[semanticRole="danger"] {{ color: {t["danger"]}; font-weight: 600; }}
        QLabel[semanticRole="link"] {{ color: {t["link"]}; }}
        QLabel[semanticRole="danger"][semanticEmphasis="hero"] {{ font-size: 17px; font-weight: 700; }}
        QLabel[validationMessage="true"] {{ color: {t["danger"]}; }}
        QLabel[statusRole="neutral"] {{ color: {t["text_muted"]}; }}
        QLabel[statusRole="danger"] {{ color: {t["danger"]}; }}
        QLabel[statusRole="success"] {{ color: {t["success"]}; }}
        QLabel[sectionTitle="true"] {{
            color: {t["success"]}; font-weight: 600; padding: 6px 2px 2px;
        }}
        QLabel[sectionTitle="true"][sectionSeparated="true"] {{
            border-top: 1px solid {t["border"]};
        }}
        QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox, QComboBox {{
            color: {t["text"]}; background: {t["input_bg"]};
            border: 1px solid {t["border"]}; border-radius: {t["radius_md"]};
        }}
        QLineEdit[semanticRole="code"], QPlainTextEdit[semanticRole="code"], QTextEdit[semanticRole="code"],
        QGroupBox[semanticRole="codeGroup"] {{
            font-family: Consolas, 'Cascadia Mono', monospace;
        }}
        QWidget[semanticRole="mutedContainer"] {{ color: {t["text_muted"]}; }}
        QPushButton[semanticRole="ghost"] {{
            color: {t["text"]};
            background: transparent;
            border: 0;
            border-radius: {t["radius_md"]};
        }}
        QPushButton[semanticRole="ghost"]:hover {{ background: {t["selection_bg"]}; }}
        QPushButton[semanticRole="ghost"]:pressed {{ background: {t["selection_bg_inactive"]}; }}
        QPlainTextEdit[cookieEditor="true"] {{
            color: {t["text"]}; background: {t["input_bg"]};
            border: 1px solid {t["border"]}; border-radius: {t["radius_sm"]};
            font-family: Courier;
        }}
    """


def _apply_dynamic_semantic_styles(self: "MyMAinWindow", dark: bool) -> None:
    preview = getattr(self.Ui, "label_name_template_preview_result", None)
    if preview is not None:
        preview_text = preview.text()
        state = "danger" if "语法错误" in preview_text else "success" if "语法正确" in preview_text else "neutral"
        preview.setStyleSheet("")
        set_semantic_property(preview, "statusRole", state)

    for name in ("label_javdb_cookie_section", "label_javbus_cookie_section", "label_fc2cmadb_cookie_section"):
        label = getattr(self.Ui, name, None)
        if label is not None:
            label.setStyleSheet("")
            set_semantic_property(label, "sectionTitle", True)
            set_semantic_property(label, "sectionSeparated", name != "label_javdb_cookie_section")

    cookie_editor = getattr(self.Ui, "plainTextEdit_cookie_fc2ppvdb", None)
    if cookie_editor is not None:
        cookie_editor.setStyleSheet("")
        set_semantic_property(cookie_editor, "cookieEditor", True)


def _apply_log_document_style(self: "MyMAinWindow", dark: bool) -> None:
    t = _tokens(dark)
    document_style = f"""
        a {{
            color: {t["link"]};
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            color: {t["link_hover"]};
            text-decoration: underline;
        }}
    """
    for text_browser in (
        self.Ui.textBrowser_log_main,
        self.Ui.textBrowser_log_main_2,
        self.Ui.textBrowser_log_main_3,
        self.Ui.textBrowser_net_main,
        self.Ui.textBrowser_about,
        self.Ui.textBrowser_show_success_list,
        self.Ui.textBrowser_show_tips,
    ):
        text_browser.document().setDefaultStyleSheet(document_style)


def set_style(self: "MyMAinWindow"):
    if self.dark_mode:
        self.set_dark_style()
        return

    apply_application_palette(False)
    _adopt_settings_semantic_styles(self)
    _apply_dynamic_semantic_styles(self, False)
    _apply_log_document_style(self, False)
    self.Ui.treeWidget_number.setStyleSheet(build_tree_widget_style(False))

    self.Ui.widget_setting.setStyleSheet(build_sidebar_style(False, self.window_radius))
    if hasattr(self, "_shell_splitter"):
        self._shell_splitter.setStyleSheet(build_shell_splitter_style(False))
    self.Ui.page_main.setStyleSheet(build_main_page_style(False))
    self.Ui.page_tool.setStyleSheet(build_tool_page_style(False))
    self.Ui.page_about.setStyleSheet(build_about_page_style(False))
    # 设置页
    self.Ui.page_setting.setStyleSheet(
        _qss_resources(
            _theme_qss(
                """
        * {
            font-size:13px;
        }
        QScrollArea{
            background-color: rgba(246, 246, 246, 0);
            border-color: rgba(246, 246, 246, 255);
        }
        QTabWidget{
            background-color: rgba(246, 246, 246, 0);
            border-color: rgba(246, 246, 246, 255);
        }
        QTabWidget::tab-bar {
            alignment: center;
        }
        QTabBar::tab{
            color: black;
            border:1px solid #E8E8E8;
            min-height: 28px;
            min-width: 0;
            padding: 2px 8px;
            margin-right: 2px;
            background-color:#FFFFFF;
            border-radius: 8px;
        }
        QTabBar::tab:selected{
            color: white;
            font-weight:bold;
            border: 1px solid #4C6EFF;
            background-color:#4C6EFF;
            border-radius: 8px;
        }
        QWidget#tab1,#tab2,#tab3,#tab4,#tab5,#tab,#tab_2,#tab_3,#tab_4,#tab_5,#tab_6,#tab_7,#scrollAreaWidgetContents_guaxiaomulu,#scrollAreaWidgetContents_guaxiaomoshi,#scrollAreaWidgetContents_guaxiaowangzhan,#scrollAreaWidgetContents_xiazai,#scrollAreaWidgetContents_mingming,#scrollAreaWidgetContents_fanyi,#scrollAreaWidgetContents_zimu,#scrollAreaWidgetContents_shuiyin,#scrollAreaWidgetContents_nfo,#scrollAreaWidgetContents_yanyuan,#scrollAreaWidgetContents_wangluo,#scrollAreaWidgetContents_gaoji{
            background-color: rgba(255, 255, 255, 255);
            border-color: rgba(246, 246, 246, 255);
        }
        QLabel{
            font-size:13px;
            border:0px solid rgba(0, 0, 0, 80);
        }
        QLabel#label_config{
            font-size:13px;
            border:0px solid rgba(230, 230, 230, 80);
            background: rgba(246, 246, 246, 220);
        }

        QLineEdit{
            font-size:13px;
            border:0px solid rgba(130, 30, 30, 20);
            border-radius: 8px;
        }
        QRadioButton{
            font-size:13px;
        }
        QComboBox{
            combobox-popup: 0;
            font-size:13px;
        }
        QCheckBox{
            font-size:13px;
        }
        QCheckBox::indicator, QRadioButton::indicator{
            width: 14px;
            height: 14px;
            border: 1px solid #B8C0CC;
            background: #FFFFFF;
        }
        QCheckBox::indicator{
            border-radius: 3px;
        }
        QRadioButton::indicator{
            border-radius: 7px;
        }
        QCheckBox::indicator:checked{
            background: #4C6EFF;
            border: 1px solid #4C6EFF;
            image: url(resources/Img/check_indicator.svg);
        }
        QRadioButton::indicator:checked{
            background: #4C6EFF;
            border: 1px solid #4C6EFF;
            image: url(resources/Img/radio_indicator.svg);
        }
        QCheckBox::indicator:hover, QRadioButton::indicator:hover{
            border: 1px solid #4C6EFF;
        }
        QPlainTextEdit{
            font-size:13px;
        }
        QGroupBox{
            background-color: rgba(245,245,246,220);
            border-radius: 10px;
        }
        """,
                False,
            )
        )
    )
    self.Ui.page_setting.setStyleSheet(self.Ui.page_setting.styleSheet() + _settings_semantic_style(False))
    # 整个页面
    self.Ui.centralwidget.setStyleSheet(
        _qss_resources(
            _theme_qss(
                f"""
        * {{
            font-family: 'Microsoft YaHei UI', 'Segoe UI Variable', 'PingFang SC', 'Noto Sans CJK SC', 'Segoe UI';
            font-size:13px;
            color: black;
        }}
        QTreeWidget, QTreeView
        {{
            background-color: rgba(246, 246, 246, 0);
            font-size: 12px;
            border:0px solid rgb(120,120,120);
        }}
        QWidget#centralwidget{{
            background: #FFFFFF;
            border: {self.window_border}px solid rgba(20,20,20,50);
            border-radius: {self.window_radius}px;
       }}
        QTextBrowser#textBrowser_log_main,#textBrowser_net_main,#textBrowser_about{{
            font-size:13px;
            border: 0px solid #BEBEBE;
            background-color: rgba(246,246,246,0);
            padding: 2px;
        }}
        QTextBrowser#textBrowser_log_main_2{{
            font-size:13px;
            border-radius: 0px;
            border-top: 1px solid #BEBEBE;
            background-color: rgba(238,245,245,60);
            padding: 2px;
        }}
        QTextBrowser#textBrowser_log_main_3{{
            font-size:13px;
            border-radius: 0px;
            border-right: 1px solid #EDEDED;
            background-color: rgba(239,255,252,240);
            padding: 2px;
        }}
        QTextBrowser#textBrowser_show_success_list,#textBrowser_show_tips{{
            font-size: 13px;
            background-color: rgba(240, 245, 240, 240);
            border: 1px solid #BEBEBE;
            padding: 2px;
        }}
        QWidget#widget_show_success,#widget_show_tips,#widget_nfo{{
            background-color: rgba(246,246,246,255);
            border: 1px solid rgba(20,20,20,50);
            border-radius: 10px;
       }}
        QWidget#scrollAreaWidgetContents_nfo_editor{{
            background-color: rgba(240, 245, 240, 240);
            border: 0px solid rgba(0,0,0,150);
        }}
        QLineEdit, QPlainTextEdit, QTextEdit, QDoubleSpinBox, QSpinBox{{
            font-size:14px;
            background:white;
            border-radius:8px;
            border: 1px solid #D8DEE9;
            padding: 4px 8px;
            selection-background-color: #4C6EFF;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus{{
            border: 1px solid #4C6EFF;
            background: #FFFFFF;
        }}
        QTextEdit#textEdit_nfo_outline,#textEdit_nfo_originalplot,#textEdit_nfo_tag{{
            font-size:14px;
            background:white;
            border: 1px solid #D8DEE9;
            padding: 4px 8px;
        }}
        QComboBox{{
            combobox-popup: 0;
            background: #FFFFFF;
            border: 1px solid #D8DEE9;
            border-radius: 8px;
            padding: 3px 30px 3px 8px;
            selection-background-color: #4C6EFF;
        }}
        QComboBox::drop-down{{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 26px;
            border-left: 1px solid #D8DEE9;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
            background: #F8FAFC;
        }}
        QComboBox::drop-down:hover{{
            background: #EEF2FF;
        }}
        QComboBox::down-arrow{{
            image: url(resources/Img/chevron_down_light.svg);
            width: 14px;
            height: 14px;
        }}
        QComboBox#result_status_combo, QComboBox#result_sort_combo{{
            padding: 2px 24px 2px 6px;
        }}
        QComboBox#result_status_combo::drop-down, QComboBox#result_sort_combo::drop-down{{
            width: 20px;
        }}
        QComboBox#result_status_combo::down-arrow, QComboBox#result_sort_combo::down-arrow{{
            width: 12px;
            height: 12px;
        }}
        QComboBox:focus{{
            border: 1px solid #4C6EFF;
        }}
        QComboBox QAbstractItemView{{
            background: #FFFFFF;
            border: 1px solid #D8DEE9;
            selection-background-color: #4C6EFF;
            selection-color: white;
            outline: 0;
        }}
        QComboBox QAbstractItemView::item{{
            min-height: 24px;
            padding: 4px 8px;
            color: #111827;
        }}
        QComboBox QAbstractItemView::item:selected{{
            color: #FFFFFF;
            background: #4C6EFF;
        }}
        QCheckBox::indicator, QRadioButton::indicator{{
            width: 14px;
            height: 14px;
            border: 1px solid #B8C0CC;
            background: #FFFFFF;
        }}
        QCheckBox::indicator{{
            border-radius: 3px;
        }}
        QRadioButton::indicator{{
            border-radius: 7px;
        }}
        QCheckBox::indicator:checked{{
            background: #4C6EFF;
            border: 1px solid #4C6EFF;
            image: url(resources/Img/check_indicator.svg);
        }}
        QRadioButton::indicator:checked{{
            background: #4C6EFF;
            border: 1px solid #4C6EFF;
            image: url(resources/Img/radio_indicator.svg);
        }}
        QCheckBox::indicator:hover, QRadioButton::indicator:hover{{
            border: 1px solid #4C6EFF;
        }}
        QToolTip{{
            border: 1px solid #D8DEE9;
            border-radius: 8px;
            background: #FFFFFF;
            color: #111827;
            padding: 6px 10px;
        }}
        QPushButton#pushButton_right_menu,#pushButton_play,#pushButton_open_folder,#pushButton_open_nfo,#pushButton_load_nfo,#pushButton_show_hide_logs,#pushButton_save_failed_list,#pushButton_tree_clear{{
            background-color: rgba(181, 181, 181, 0);
            border-radius:10px;
            border: 0px solid rgba(0, 0, 0, 80);
        }}
        QPushButton:hover#pushButton_right_menu,:hover#pushButton_play,:hover#pushButton_open_folder,:hover#pushButton_open_nfo,:hover#pushButton_load_nfo,:hover#pushButton_show_hide_logs,:hover#pushButton_save_failed_list,:hover#pushButton_tree_clear{{
            background-color: rgba(181, 181, 181, 120);
        }}
        QPushButton:pressed#pushButton_right_menu,:pressed#pushButton_play,:pressed#pushButton_open_folder,:pressed#pushButton_open_nfo,:pressed#pushButton_load_nfo,:pressed#pushButton_show_hide_logs,:pressed#pushButton_save_failed_list,:pressed#pushButton_tree_clear{{
            background-color: rgba(150, 150, 150, 120);
        }}
        QPushButton#pushButton_scrape_note,#pushButton_field_tips_website,#pushButton_field_tips_nfo{{
            color: #111827;
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            padding: 3px 10px;
        }}
        QPushButton:hover#pushButton_scrape_note,:hover#pushButton_field_tips_website,:hover#pushButton_field_tips_nfo{{
            color: #FFFFFF;
            background: #4C6EFF;
            border: 1px solid #4C6EFF;
        }}
        QPushButton:pressed#pushButton_scrape_note,:pressed#pushButton_field_tips_website,:pressed#pushButton_field_tips_nfo{{
            color: #FFFFFF;
            background: #3F5FE6;
            border: 1px solid #3F5FE6;
        }}
        QPushButton#pushButton_save_new_config,#pushButton_init_config,#pushButton_success_list_close,#pushButton_success_list_save,#pushButton_success_list_clear,#pushButton_show_tips_close,#pushButton_nfo_close,#pushButton_nfo_save,#pushButton_show_pic_actor,#pushButton_add_actor_pic,#pushButton_add_actor_info,#pushButton_add_actor_pic_kodi,#pushButton_del_actor_folder,#pushButton_move_mp4,#pushButton_select_file,#pushButton_select_local_library,#pushButton_select_netdisk_path,#pushButton_select_localdisk_path,#pushButton_creat_symlink,#pushButton_find_missing_number,#pushButton_select_thumb,#pushButton_start_single_file,#pushButton_select_file_clear_info,#pushButton_add_sub_for_all_video,#pushButton_view_failed_list,#pushButton_select_media_folder,#pushButton_select_media_folder_setting_page,#pushButton_select_softlink_folder,#pushButton_select_sucess_folder,#pushButton_select_failed_folder,#pushButton_view_success_file,#pushButton_select_subtitle_folder,#pushButton_select_actor_photo_folder,#pushButton_select_actor_info_db,#pushButton_select_config_folder,#pushButton_add_all_extrafanart_copy,#pushButton_del_all_extrafanart_copy,#pushButton_add_all_extras,#pushButton_del_all_extras,#pushButton_add_all_theme_videos,#pushButton_del_all_theme_videos,#pushButton_check_and_clean_files,#pushButton_search_by_number,#pushButton_search_by_url{{
            font-size:14px;
            color: #24324A;
            background-color: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 5px 10px;
        }}
        QPushButton:hover#pushButton_show_pic_actor,:hover#pushButton_add_actor_pic,:hover#pushButton_add_actor_info,:hover#pushButton_add_actor_pic_kodi,:hover#pushButton_del_actor_folder,:hover#pushButton_add_sub_for_all_video,:hover#pushButton_view_failed_list,:hover#pushButton_select_media_folder,:hover#pushButton_select_media_folder_setting_page,:hover#pushButton_select_softlink_folder,:hover#pushButton_select_sucess_folder,:hover#pushButton_select_failed_folder,:hover#pushButton_view_success_file,:hover#pushButton_select_subtitle_folder,:hover#pushButton_select_actor_photo_folder,:hover#pushButton_select_actor_info_db,:hover#pushButton_select_config_folder,:hover#pushButton_add_all_extrafanart_copy,:hover#pushButton_del_all_extrafanart_copy,:hover#pushButton_add_all_extras,:hover#pushButton_del_all_extras,:hover#pushButton_add_all_theme_videos,:hover#pushButton_del_all_theme_videos,:hover#pushButton_check_and_clean_files,:hover#pushButton_search_by_number,:hover#pushButton_search_by_url{{
            color: white;
            background-color: rgba(76,110,255,240);
            font-weight:bold;
        }}
        QPushButton:pressed#pushButton_show_pic_actor,:pressed#pushButton_add_actor_pic,:pressed#pushButton_add_actor_info,:pressed#pushButton_add_actor_pic_kodi,:pressed#pushButton_del_actor_folder,:pressed#pushButton_add_sub_for_all_video,:pressed#pushButton_view_failed_list,:pressed#pushButton_select_media_folder,:pressed#pushButton_select_media_folder_setting_page,:pressed#pushButton_select_softlink_folder,:pressed#pushButton_select_sucess_folder,:pressed#pushButton_select_failed_folder,:pressed#pushButton_view_success_file,:pressed#pushButton_select_subtitle_folder,:pressed#pushButton_select_actor_photo_folder,:pressed#pushButton_select_actor_info_db,:pressed#pushButton_select_config_folder,:pressed#pushButton_add_all_extrafanart_copy,:pressed#pushButton_del_all_extrafanart_copy,:pressed#pushButton_add_all_extras,:pressed#pushButton_del_all_extras,:pressed#pushButton_add_all_theme_videos,:pressed#pushButton_del_all_theme_videos,:pressed#pushButton_check_and_clean_files,:pressed#pushButton_search_by_number,:pressed#pushButton_search_by_url{{
            background-color:#4C6EE0;
            border: 1px solid #3F5FE6;
            font-weight:bold;
        }}
        QPushButton#pushButton_save_config{{
            color: white;
            font-size:14px;
            background-color:#4C6EFF;
            border: 1px solid #4C6EFF;
            border-radius: 8px;
            padding: 5px 12px;
        }}
        QPushButton:hover#pushButton_save_config,:hover#pushButton_save_new_config,:hover#pushButton_init_config,:hover#pushButton_success_list_close,:hover#pushButton_success_list_save,:hover#pushButton_success_list_clear,:hover#pushButton_show_tips_close,:hover#pushButton_nfo_close,:hover#pushButton_nfo_save,:hover#pushButton_scraper_failed_list{{
            color: white;
            background-color: rgba(76,110,255,240);
            font-weight:bold;
            }}
        QPushButton:pressed#pushButton_save_config,:pressed#pushButton_save_new_config,:pressed#pushButton_init_config,:pressed#pushButton_success_list_close,:pressed#pushButton_success_list_save,:pressed#pushButton_success_list_clear,:pressed#pushButton_show_tips_close,:pressed#pushButton_nfo_close,:pressed#pushButton_nfo_save,:pressed#pushButton_scraper_failed_list{{
            background-color:#4C6EE0;
            border: 1px solid #3F5FE6;
            font-weight:bold;
        }}
        QPushButton#pushButton_start_cap,#pushButton_start_cap2,#pushButton_check_net,#pushButton_scraper_failed_list{{
            color: white;
            font-size:14px;
            background-color:#4C6EFF;
            border: 1px solid #4C6EFF;
            border-radius: 8px;
            padding: 5px 12px;
            font-weight:bold;
        }}
        QPushButton:hover#pushButton_start_cap,:hover#pushButton_start_cap2,:hover#pushButton_check_net,:hover#pushButton_move_mp4,:hover#pushButton_select_file,:hover#pushButton_select_local_library,:hover#pushButton_select_netdisk_path,:hover#pushButton_select_localdisk_path,:hover#pushButton_creat_symlink,:hover#pushButton_find_missing_number,:hover#pushButton_select_thumb,:hover#pushButton_start_single_file,:hover#pushButton_select_file_clear_info{{
            color: white;
            background-color: rgba(76,110,255,240);
            font-weight:bold;
            }}
        QPushButton:pressed#pushButton_start_cap,:pressed#pushButton_start_cap2,:pressed#pushButton_check_net,:pressed#pushButton_move_mp4,:pressed#pushButton_select_file,:pressed#pushButton_select_local_library,:pressed#pushButton_select_netdisk_path,:pressed#pushButton_select_localdisk_path,:pressed#pushButton_creat_symlink,:pressed#pushButton_find_missing_number,:pressed#pushButton_select_thumb,:pressed#pushButton_start_single_file,:pressed#pushButton_select_file_clear_info{{
            background-color:#4C6EE0;
            border: 1px solid #3F5FE6;
            font-weight:bold;
        }}
        QSlider::groove:horizontal{{
            height: 6px;
            border-radius: 3px;
            background: #D7DDE8;
        }}
        QSlider::sub-page:horizontal{{
            border-radius: 3px;
            background: #4C6EFF;
        }}
        QSlider::add-page:horizontal{{
            border-radius: 3px;
            background: #D7DDE8;
        }}
        QSlider::handle:horizontal{{
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
            border: 2px solid #4C6EFF;
            background: #FFFFFF;
        }}
        QSlider::handle:horizontal:hover{{
            border: 2px solid #2F55EA;
            background: #F8FAFF;
        }}
        {build_scrollbar_style(False)}
        {build_validation_style(False)}
        QProgressBar::chunk{{
            background-color: #5777FF;
            width: 3px; /*区块宽度*/
            margin: 0px;
        }}
        """,
                False,
            )
        )
    )
    self.Ui.centralwidget.setStyleSheet(self.Ui.centralwidget.styleSheet() + build_window_chrome_style(False))
    self.Ui.treeWidget_number.setStyleSheet(build_tree_widget_style(False))
    # Parent styles are applied above, so normalize generated inline styles last.
    _normalize_form_control_radius(self)


def set_dark_style(self: "MyMAinWindow"):
    apply_application_palette(True)
    _adopt_settings_semantic_styles(self)
    _apply_dynamic_semantic_styles(self, True)
    _apply_log_document_style(self, True)
    self.Ui.treeWidget_number.setStyleSheet(build_tree_widget_style(True))

    self.Ui.widget_setting.setStyleSheet(build_sidebar_style(True, self.window_radius))
    if hasattr(self, "_shell_splitter"):
        self._shell_splitter.setStyleSheet(build_shell_splitter_style(True))
    self.Ui.page_main.setStyleSheet(build_main_page_style(True))
    self.Ui.page_tool.setStyleSheet(build_tool_page_style(True))
    self.Ui.page_about.setStyleSheet(build_about_page_style(True))
    # 设置页
    self.Ui.page_setting.setStyleSheet(
        _qss_resources(
            _theme_qss(
                """
        * {
            font-size:13px;
        }
        QScrollArea{
            background-color: rgba(246, 246, 246, 0);
            border-color: rgba(246, 246, 246, 0);
        }
        QTabWidget{
            background-color: rgba(246, 246, 246, 0);
            border-color: rgba(246, 246, 246, 0);
        }
        QTabWidget::tab-bar {
            alignment: center;
        }
        QTabBar::tab{
            border:1px solid #1F272F;
            min-height: 28px;
            min-width: 0;
            padding: 2px 8px;
            margin-right: 2px;
            background-color:#242D37;
            border-radius: 8px;
        }
        QTabBar::tab:selected{
            font-weight:bold;
            border: 1px solid #4C6EFF;
            background-color:#4C6EFF;
            border-radius: 8px;
        }
        QWidget#tab1,#tab2,#tab3,#tab4,#tab5,#tab,#tab_2,#tab_3,#tab_4,#tab_5,#tab_6,#tab_7,#scrollAreaWidgetContents_guaxiaomulu,#scrollAreaWidgetContents_guaxiaomoshi,#scrollAreaWidgetContents_guaxiaowangzhan,#scrollAreaWidgetContents_xiazai,#scrollAreaWidgetContents_mingming,#scrollAreaWidgetContents_fanyi,#scrollAreaWidgetContents_zimu,#scrollAreaWidgetContents_shuiyin,#scrollAreaWidgetContents_nfo,#scrollAreaWidgetContents_yanyuan,#scrollAreaWidgetContents_wangluo,#scrollAreaWidgetContents_gaoji{
            background-color: #18222D;
            border-color: rgba(246, 246, 246, 0);
        }
        QLabel{
            font-size:13px;
            border:0px solid rgba(0, 0, 0, 80);
        }
        QLabel#label_config{
            font-size:13px;
            border:0px solid rgba(0, 0, 0, 80);
            background: rgba(31,39,47,230);
        }
        QLineEdit{
            font-size:13px;
            border:0px solid rgba(130, 30, 30, 20);
            border-radius: 8px;
        }
        QRadioButton{
            font-size:13px;
        }
        QCheckBox{
            font-size:13px;
        }
        QCheckBox::indicator, QRadioButton::indicator{
            width: 14px;
            height: 14px;
            border: 1px solid #5B6673;
            background: #18222D;
        }
        QCheckBox::indicator{
            border-radius: 3px;
        }
        QRadioButton::indicator{
            border-radius: 7px;
        }
        QCheckBox::indicator:checked{
            background: #6684FF;
            border: 1px solid #6684FF;
            image: url(resources/Img/check_indicator.svg);
        }
        QRadioButton::indicator:checked{
            background: #6684FF;
            border: 1px solid #6684FF;
            image: url(resources/Img/radio_indicator.svg);
        }
        QCheckBox::indicator:hover, QRadioButton::indicator:hover{
            border: 1px solid #8EA3FF;
        }
        QPlainTextEdit{
            font-size:13px;
            background:#18222D;
            border-radius: 8px;
        }
        QGroupBox{
            background-color: rgba(180, 180, 180, 20);
            border-radius: 10px;
        }
        QPushButton{
            color: #E5E7EB;
        }
        QPushButton#pushButton_scrape_note,#pushButton_field_tips_website,#pushButton_field_tips_nfo{
            color: #E5E7EB;
            background: #1D2834;
            border: 1px solid #3B4654;
            border-radius: 6px;
            padding: 3px 10px;
        }
        QPushButton:hover#pushButton_scrape_note,:hover#pushButton_field_tips_website,:hover#pushButton_field_tips_nfo{
            color: #FFFFFF;
            background: #6684FF;
            border: 1px solid #6684FF;
        }
        QPushButton:pressed#pushButton_scrape_note,:pressed#pushButton_field_tips_website,:pressed#pushButton_field_tips_nfo{
            color: #FFFFFF;
            background: #4C6EE0;
            border: 1px solid #4C6EE0;
        }
        """,
                True,
            )
        )
    )
    self.Ui.page_setting.setStyleSheet(self.Ui.page_setting.styleSheet() + _settings_semantic_style(True))
    # 整个页面
    self.Ui.centralwidget.setStyleSheet(
        _qss_resources(
            _theme_qss(
                f"""
        * {{
            font-family: 'Microsoft YaHei UI', 'Segoe UI Variable', 'PingFang SC', 'Noto Sans CJK SC', 'Segoe UI';
            font-size:13px;
            color: white;
        }}
        QTreeWidget, QTreeView
        {{
            background-color: rgba(246, 246, 246, 0);
            font-size: 12px;
            border:0px solid rgb(120,120,120);
        }}
        QWidget#centralwidget{{
            background: #18222D;
            border: {self.window_border}px solid rgba(20,20,20,50);
            border-radius: {self.window_radius}px;
       }}
        QTextBrowser#textBrowser_log_main,#textBrowser_net_main,#textBrowser_about{{
            font-size:13px;
            border: 0px solid #BEBEBE;
            background-color: rgba(246,246,246,0);
            padding: 2px;
        }}
        QTextBrowser#textBrowser_log_main_2{{
            font-size:13px;
            border-radius: 0px;
            border-top: 1px solid #BEBEBE;
            background-color: #18222D;
            padding: 2px;
        }}
        QTextBrowser#textBrowser_log_main_3{{
            font-size:13px;
            border-radius: 0px;
            border-right: 1px solid #20303F;
            background-color: #1F272F;
            padding: 2px;
        }}
        QTextBrowser#textBrowser_show_success_list,#textBrowser_show_tips{{
            font-size: 13px;
            border: 1px solid #BEBEBE;
            background-color: #18222D;
            padding: 2px;
        }}
        QWidget#widget_show_success,#widget_show_tips,#widget_nfo{{
            background-color: #1F272F;
            border: 1px solid rgba(240,240,240,150);
            border-radius: 10px;
       }}
        QWidget#scrollAreaWidgetContents_nfo_editor{{
            background-color: #18222D;
            border: 0px solid rgba(0,0,0,150);
        }}
        QLineEdit, QPlainTextEdit, QTextEdit, QDoubleSpinBox, QSpinBox{{
            font-size:13px;
            background:#18222D;
            border-radius:8px;
            border: 1px solid #2F3A46;
            padding: 4px 8px;
            selection-background-color: #4C6EFF;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus{{
            border: 1px solid #6684FF;
            background: #1D2834;
        }}
        QTextEdit#textEdit_nfo_outline,#textEdit_nfo_originalplot,#textEdit_nfo_tag{{
            font-size:13px;
            background:#18222D;
            border: 1px solid #2F3A46;
            padding: 4px 8px;
        }}
        QToolTip{{
            border: 1px solid #2F3A46;
            border-radius: 8px;
            background: #F9FAFB;
            color: #111827;
            padding: 6px 10px;
        }}
        QCheckBox::indicator, QRadioButton::indicator{{
            width: 14px;
            height: 14px;
            border: 1px solid #5B6673;
            background: #18222D;
        }}
        QCheckBox::indicator{{
            border-radius: 3px;
        }}
        QRadioButton::indicator{{
            border-radius: 7px;
        }}
        QCheckBox::indicator:checked{{
            background: #6684FF;
            border: 1px solid #6684FF;
            image: url(resources/Img/check_indicator.svg);
        }}
        QRadioButton::indicator:checked{{
            background: #6684FF;
            border: 1px solid #6684FF;
            image: url(resources/Img/radio_indicator.svg);
        }}
        QCheckBox::indicator:hover, QRadioButton::indicator:hover{{
            border: 1px solid #8EA3FF;
        }}
        QPushButton#pushButton_right_menu,#pushButton_play,#pushButton_open_folder,#pushButton_open_nfo,#pushButton_load_nfo,#pushButton_show_hide_logs,#pushButton_save_failed_list,#pushButton_tree_clear{{
            background-color: rgba(181, 181, 181, 0);
            border-radius:10px;
            border: 0px solid rgba(0, 0, 0, 80);
        }}
        QPushButton:hover#pushButton_right_menu,:hover#pushButton_play,:hover#pushButton_open_folder,:hover#pushButton_open_nfo,:hover#pushButton_load_nfo,:hover#pushButton_show_hide_logs,:hover#pushButton_save_failed_list,:hover#pushButton_tree_clear{{
            background-color: rgba(181, 181, 181, 120);
        }}
        QPushButton:pressed#pushButton_right_menu,:pressed#pushButton_play,:pressed#pushButton_open_folder,:pressed#pushButton_open_nfo,:pressed#pushButton_load_nfo,:pressed#pushButton_show_hide_logs,:pressed#pushButton_save_failed_list,:pressed#pushButton_tree_clear{{
            background-color: rgba(150, 150, 150, 120);
        }}
        QPushButton#pushButton_scrape_note,#pushButton_field_tips_website,#pushButton_field_tips_nfo{{
            color: #E5E7EB;
            background: #1D2834;
            border: 1px solid #3B4654;
            border-radius: 6px;
            padding: 3px 10px;
        }}
        QPushButton:hover#pushButton_scrape_note,:hover#pushButton_field_tips_website,:hover#pushButton_field_tips_nfo{{
            color: #FFFFFF;
            background: #6684FF;
            border: 1px solid #6684FF;
        }}
        QPushButton:pressed#pushButton_scrape_note,:pressed#pushButton_field_tips_website,:pressed#pushButton_field_tips_nfo{{
            color: #FFFFFF;
            background: #4C6EE0;
            border: 1px solid #4C6EE0;
        }}
        QPushButton#pushButton_save_new_config,#pushButton_init_config,#pushButton_success_list_close,#pushButton_success_list_save,#pushButton_success_list_clear,#pushButton_show_tips_close,#pushButton_nfo_close,#pushButton_nfo_save,#pushButton_show_pic_actor,#pushButton_add_actor_pic,#pushButton_add_actor_info,#pushButton_add_actor_pic_kodi,#pushButton_del_actor_folder,#pushButton_move_mp4,#pushButton_select_file,#pushButton_select_local_library,#pushButton_select_netdisk_path,#pushButton_select_localdisk_path,#pushButton_creat_symlink,#pushButton_find_missing_number,#pushButton_select_thumb,#pushButton_start_single_file,#pushButton_select_file_clear_info,#pushButton_add_sub_for_all_video,#pushButton_view_failed_list,#pushButton_select_media_folder,#pushButton_select_media_folder_setting_page,#pushButton_select_softlink_folder,#pushButton_select_sucess_folder,#pushButton_select_failed_folder,#pushButton_view_success_file,#pushButton_select_subtitle_folder,#pushButton_select_actor_photo_folder,#pushButton_select_actor_info_db,#pushButton_select_config_folder,#pushButton_add_all_extrafanart_copy,#pushButton_del_all_extrafanart_copy,#pushButton_add_all_extras,#pushButton_del_all_extras,#pushButton_add_all_theme_videos,#pushButton_del_all_theme_videos,#pushButton_check_and_clean_files,#pushButton_search_by_number,#pushButton_search_by_url{{
            font-size:14px;
            color: #E5E7EB;
            background-color: #202C39;
            border: 1px solid #3B4858;
            border-radius: 8px;
            padding: 5px 10px;
        }}
        QPushButton:hover#pushButton_show_pic_actor,:hover#pushButton_add_actor_pic,:hover#pushButton_add_actor_info,:hover#pushButton_add_actor_pic_kodi,:hover#pushButton_del_actor_folder,:hover#pushButton_add_sub_for_all_video,:hover#pushButton_view_failed_list,:hover#pushButton_scraper_failed_list,:hover#pushButton_select_media_folder,:hover#pushButton_select_media_folder_setting_page,:hover#pushButton_select_softlink_folder,:hover#pushButton_select_sucess_folder,:hover#pushButton_select_failed_folder,:hover#pushButton_view_success_file,:hover#pushButton_select_subtitle_folder,:hover#pushButton_select_actor_photo_folder,:hover#pushButton_select_actor_info_db,:hover#pushButton_select_config_folder,:hover#pushButton_add_all_extrafanart_copy,:hover#pushButton_del_all_extrafanart_copy,:hover#pushButton_add_all_extras,:hover#pushButton_del_all_extras,:hover#pushButton_add_all_theme_videos,:hover#pushButton_del_all_theme_videos,:hover#pushButton_check_and_clean_files,:hover#pushButton_search_by_number,:hover#pushButton_search_by_url{{
            color: white;
            background-color: rgba(76,110,255,240);
            font-weight:bold;
        }}
        QPushButton:pressed#pushButton_show_pic_actor,:pressed#pushButton_add_actor_pic,:pressed#pushButton_add_actor_info,:pressed#pushButton_add_actor_pic_kodi,:pressed#pushButton_del_actor_folder,:pressed#pushButton_add_sub_for_all_video,:pressed#pushButton_view_failed_list,:pressed#pushButton_scraper_failed_list,:pressed#pushButton_select_media_folder,:pressed#pushButton_select_media_folder_setting_page,:pressed#pushButton_select_softlink_folder,:pressed#pushButton_select_sucess_folder,:pressed#pushButton_select_failed_folder,:pressed#pushButton_view_success_file,:pressed#pushButton_select_subtitle_folder,:pressed#pushButton_select_actor_photo_folder,:pressed#pushButton_select_actor_info_db,:pressed#pushButton_select_config_folder,:pressed#pushButton_add_all_extrafanart_copy,:pressed#pushButton_del_all_extrafanart_copy,:pressed#pushButton_add_all_extras,:pressed#pushButton_del_all_extras,:pressed#pushButton_add_all_theme_videos,:pressed#pushButton_del_all_theme_videos,:pressed#pushButton_check_and_clean_files,:pressed#pushButton_search_by_number,:pressed#pushButton_search_by_url{{
            background-color:#4C6EE0;
            border: 1px solid #6684FF;
            font-weight:bold;
        }}
        QPushButton#pushButton_save_config{{
            color: white;
            font-size:14px;
            background-color:#4C6EFF;
            border: 1px solid #6684FF;
            border-radius: 8px;
            padding: 5px 12px;
        }}
        QPushButton:hover#pushButton_save_config,:hover#pushButton_save_new_config,:hover#pushButton_init_config,:hover#pushButton_success_list_close,:hover#pushButton_success_list_save,:hover#pushButton_success_list_clear,:hover#pushButton_show_tips_close,:hover#pushButton_nfo_close,:hover#pushButton_nfo_save{{
            color: white;
            background-color: rgba(76,110,255,240);
            font-weight:bold;
        }}
        QPushButton:pressed#pushButton_save_config,:pressed#pushButton_save_new_config,:pressed#pushButton_init_config,:pressed#pushButton_success_list_close,:pressed#pushButton_success_list_save,:pressed#pushButton_success_list_clear,:pressed#pushButton_show_tips_close,:pressed#pushButton_nfo_close,:pressed#pushButton_nfo_save{{
            background-color:#4C6EE0;
            border: 1px solid #6684FF;
            font-weight:bold;
        }}
        QPushButton#pushButton_start_cap,#pushButton_start_cap2,#pushButton_check_net,#pushButton_scraper_failed_list{{
            color: white;
            font-size:14px;
            background-color:#4C6EFF;
            border: 1px solid #6684FF;
            border-radius: 8px;
            padding: 5px 12px;
            font-weight:bold;
        }}
        QPushButton:hover#pushButton_start_cap,:hover#pushButton_start_cap2,:hover#pushButton_check_net,:hover#pushButton_move_mp4,:hover#pushButton_select_file,:hover#pushButton_select_local_library,:hover#pushButton_select_netdisk_path,:hover#pushButton_select_localdisk_path,:hover#pushButton_creat_symlink,:hover#pushButton_find_missing_number,:hover#pushButton_select_thumb,:hover#pushButton_start_single_file,:hover#pushButton_select_file_clear_info{{
            color: white;
            background-color: rgba(76,110,255,240);
            font-weight:bold;
            }}
        QPushButton:pressed#pushButton_start_cap,:pressed#pushButton_start_cap2,:pressed#pushButton_check_net,:pressed#pushButton_move_mp4,:pressed#pushButton_select_file,:pressed#pushButton_select_local_library,:pressed#pushButton_select_netdisk_path,:pressed#pushButton_select_localdisk_path,:pressed#pushButton_creat_symlink,:pressed#pushButton_find_missing_number,:pressed#pushButton_select_thumb,:pressed#pushButton_start_single_file,:pressed#pushButton_select_file_clear_info{{
            background-color:#4C6EE0;
            border: 1px solid #6684FF;
            font-weight:bold;
        }}
        QSlider::groove:horizontal{{
            height: 6px;
            border-radius: 3px;
            background: #2F3A46;
        }}
        QSlider::sub-page:horizontal{{
            border-radius: 3px;
            background: #6684FF;
        }}
        QSlider::add-page:horizontal{{
            border-radius: 3px;
            background: #2F3A46;
        }}
        QSlider::handle:horizontal{{
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
            border: 2px solid #6684FF;
            background: #F8FAFC;
        }}
        QSlider::handle:horizontal:hover{{
            border: 2px solid #8EA3FF;
            background: #FFFFFF;
        }}
        QComboBox{{
            combobox-popup: 0;
            font-size:13px;
            color: white;
            background:#18222D;
            border: 1px solid #2F3A46;
            border-radius: 8px;
            padding: 3px 30px 3px 8px;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: right;
            width: 26px;
            border-left: 1px solid #2F3A46;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
            background: #1D2834;
        }}
        QComboBox::drop-down:hover {{
            background: #243244;
        }}
        QComboBox::down-arrow {{
            image: url(resources/Img/chevron_down_dark.svg);
            width: 14px;
            height: 14px;
        }}
        QComboBox#result_status_combo, QComboBox#result_sort_combo {{
            padding: 2px 24px 2px 6px;
        }}
        QComboBox#result_status_combo::drop-down, QComboBox#result_sort_combo::drop-down {{
            width: 20px;
        }}
        QComboBox#result_status_combo::down-arrow, QComboBox#result_sort_combo::down-arrow {{
            width: 12px;
            height: 12px;
        }}

        QComboBox QAbstractItemView {{
            color:white;
            background: #1F272F;
            border: 1px solid #2F3A46;
            selection-color:white;
            selection-background-color: #6684FF;
            outline: 0;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 24px;
            padding: 4px 8px;
            color: #E5E7EB;
        }}
        QComboBox QAbstractItemView::item:selected {{
            color: #FFFFFF;
            background: #6684FF;
        }}
        {build_scrollbar_style(True)}
        {build_validation_style(True)}
        QProgressBar::chunk{{
            background-color: #5777FF;
            width: 3px; /*区块宽度*/
            margin: 0px;
        }}
        """,
                True,
            )
        )
    )
    self.Ui.centralwidget.setStyleSheet(self.Ui.centralwidget.styleSheet() + build_window_chrome_style(True))
    self.Ui.treeWidget_number.setStyleSheet(build_tree_widget_style(True))
    # Parent styles are applied above, so normalize generated inline styles last.
    _normalize_form_control_radius(self)
