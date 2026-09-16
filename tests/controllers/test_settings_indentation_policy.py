from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QScrollArea

from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout, setup_responsive_ui
from mdcx.controllers.main_window.settings_composites import (
    SETTINGS_FORM_ROW_HEIGHT,
    SETTINGS_SECTION_HORIZONTAL_MARGIN,
    _ensure_force_avwiki_actor_checkbox,
)
from mdcx.controllers.main_window.settings_page import SettingsPageController
from tests.layout_test_support import APP, generated_ui_window


def _direct_children(widget, widget_type):
    return widget.findChildren(widget_type, options=Qt.FindChildOption.FindDirectChildrenOnly)


def _buttons_in_layout_item(item):
    widget = item.widget()
    if widget is not None:
        return [widget] if widget.inherits("QAbstractButton") else []

    layout = item.layout()
    if layout is None:
        return []

    buttons = []
    for index in range(layout.count()):
        buttons.extend(_buttons_in_layout_item(layout.itemAt(index)))
    return buttons


def _settings_button_rows(ui, tab):
    for layout in vars(ui).values():
        inherits = getattr(layout, "inherits", None)
        if not callable(inherits) or not layout.inherits("QGridLayout"):
            continue
        parent = layout.parentWidget()
        if parent is None or not tab.isAncestorOf(parent):
            continue

        for row in range(layout.rowCount()):
            caption_item = layout.itemAtPosition(row, 0)
            if caption_item is None:
                continue
            caption = caption_item.widget()
            if caption is None or not caption.inherits("QLabel") or not caption.text().strip():
                continue

            buttons = []
            seen_items = set()
            for column in range(1, layout.columnCount()):
                item = layout.itemAtPosition(row, column)
                if item is None or id(item) in seen_items:
                    continue
                seen_items.add(id(item))
                buttons.extend(_buttons_in_layout_item(item))
            if buttons:
                yield layout, row, caption, buttons


def test_every_settings_tab_section_uses_shared_horizontal_inset():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    _ensure_force_avwiki_actor_checkbox(window.Ui)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(1089, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    tabs = window.Ui.tabWidget
    checked_sections = []
    try:
        for tab_index in range(tabs.count()):
            tab = tabs.widget(tab_index)
            areas = _direct_children(tab, QScrollArea)
            assert areas, tab.objectName()

            tab_sections = []
            for area in areas:
                content = area.widget()
                assert content is not None, area.objectName()
                for group in _direct_children(content, QGroupBox):
                    layout = group.layout()
                    assert layout is not None, group.objectName()
                    margins = layout.contentsMargins()
                    context = (tab_index, tab.objectName(), group.objectName())
                    assert margins.left() == SETTINGS_SECTION_HORIZONTAL_MARGIN, context
                    assert margins.right() == SETTINGS_SECTION_HORIZONTAL_MARGIN, context
                    tab_sections.append(group.objectName())
                    checked_sections.append(context)

            assert tab_sections, (tab_index, tab.objectName())

        assert len(checked_sections) > tabs.count()
    finally:
        window.close()
        window.deleteLater()
        APP.processEvents()


def test_every_settings_button_row_has_consistent_text_height_at_full_hd():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    _ensure_force_avwiki_actor_checkbox(window.Ui)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(1920, 1080)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    tabs = window.Ui.tabWidget
    checked_rows = []
    try:
        for tab_index in range(tabs.count()):
            tab = tabs.widget(tab_index)
            tabs.setCurrentIndex(tab_index)
            APP.processEvents()
            apply_responsive_layout(window)
            APP.processEvents()

            for layout, row, caption, buttons in _settings_button_rows(window.Ui, tab):
                context = (tab_index, tab.objectName(), layout.objectName(), row, caption.objectName())
                assert caption.minimumHeight() >= SETTINGS_FORM_ROW_HEIGHT, context
                for button in buttons:
                    assert button.minimumHeight() >= SETTINGS_FORM_ROW_HEIGHT, (*context, button.objectName())
                checked_rows.append(context)

        assert checked_rows
    finally:
        window.close()
        window.deleteLater()
        APP.processEvents()


def test_translation_checkbox_rows_are_vertically_aligned_at_full_hd():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    _ensure_force_avwiki_actor_checkbox(window.Ui)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.Ui.tabWidget.setCurrentWidget(window.Ui.tab_6)
    window.resize(1920, 1080)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    pairs = (
        (window.Ui.label_244, window.Ui.checkBox_title_translate),
        (window.Ui.label_166, window.Ui.checkBox_outline_translate),
        (window.Ui.label_250, window.Ui.checkBox_actor_realname),
    )
    try:
        for caption, checkbox in pairs:
            assert caption.parentWidget() is checkbox.parentWidget()
            assert caption.minimumHeight() >= SETTINGS_FORM_ROW_HEIGHT
            assert checkbox.minimumHeight() >= SETTINGS_FORM_ROW_HEIGHT
            assert abs(caption.geometry().center().y() - checkbox.geometry().center().y()) <= 1
    finally:
        window.close()
        window.deleteLater()
        APP.processEvents()


def test_force_avwiki_option_is_a_real_nested_row_in_actor_section():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    child = _ensure_force_avwiki_actor_checkbox(window.Ui)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.Ui.tabWidget.setCurrentWidget(window.Ui.tab_6)
    window.resize(1089, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    try:
        container = window.Ui.avwiki_actor_settings_container
        grid = window.Ui.gridLayout_50
        child_position = grid.getItemPosition(grid.indexOf(container))
        help_position = grid.getItemPosition(grid.indexOf(window.Ui.label_249))
        child_margins = container.layout().contentsMargins()

        assert child_position == (2, 1, 1, 1)
        assert help_position == (3, 1, 1, 1)
        assert child_margins.left() == 24
        assert child.text() == "强制使用 AV-Wiki（所有作品）"
        assert container.geometry().top() >= window.Ui.checkBox_actor_realname.geometry().bottom()

        master = window.Ui.checkBox_actor_realname
        master.setChecked(False)
        APP.processEvents()
        assert child.isEnabled() is False
        assert child.isChecked() is False
        child.click()
        assert child.isChecked() is False

        master.setChecked(True)
        APP.processEvents()
        assert child.isEnabled() is True
        child.setChecked(True)
        assert child.isChecked() is True

        master.setChecked(False)
        APP.processEvents()
        assert child.isEnabled() is False
        assert child.isChecked() is False
    finally:
        window.close()
        window.deleteLater()
        APP.processEvents()
