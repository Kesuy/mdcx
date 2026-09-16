from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QScrollArea

from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout, setup_responsive_ui
from mdcx.controllers.main_window.settings_composites import (
    SETTINGS_SECTION_HORIZONTAL_MARGIN,
    _ensure_force_avwiki_actor_checkbox,
)
from mdcx.controllers.main_window.settings_page import SettingsPageController
from tests.layout_test_support import APP, generated_ui_window


def _direct_children(widget, widget_type):
    return widget.findChildren(widget_type, options=Qt.FindChildOption.FindDirectChildrenOnly)


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


def test_force_avwiki_option_is_a_real_nested_row_in_actor_section():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    child = _ensure_force_avwiki_actor_checkbox(window.Ui)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.Ui.tabWidget.setCurrentWidget(window.Ui.tab_13)
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
    finally:
        window.close()
        window.deleteLater()
        APP.processEvents()
