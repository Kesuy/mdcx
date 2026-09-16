from PyQt6.QtWidgets import QGridLayout, QLabel

from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout, setup_responsive_ui
from mdcx.controllers.main_window.settings_composites import _ensure_force_avwiki_actor_checkbox
from mdcx.controllers.main_window.settings_layout_polish import polish_settings_layout
from mdcx.controllers.main_window.settings_page import SettingsPageController
from tests.layout_test_support import APP, generated_ui_window


def _walk_item_widgets(item):
    widget = item.widget()
    if widget is not None:
        yield widget
        return
    layout = item.layout()
    if layout is None:
        return
    for index in range(layout.count()):
        yield from _walk_item_widgets(layout.itemAt(index))


def _is_multiline(widget) -> bool:
    if not isinstance(widget, QLabel):
        return False
    text = widget.text().lower()
    return widget.wordWrap() or "\n" in text or "<br" in text


def _is_compact_control(widget) -> bool:
    return any(
        widget.inherits(class_name)
        for class_name in (
            "QAbstractButton",
            "QLineEdit",
            "QComboBox",
            "QAbstractSpinBox",
            "QAbstractSlider",
        )
    )


def test_all_single_row_settings_controls_are_vertically_centered_at_full_hd():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    _ensure_force_avwiki_actor_checkbox(window.Ui)
    polish_settings_layout(window.Ui)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(1920, 1080)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    polish_settings_layout(window.Ui)
    APP.processEvents()

    checked = []
    tabs = window.Ui.tabWidget
    try:
        for tab_index in range(tabs.count()):
            tab = tabs.widget(tab_index)
            tabs.setCurrentIndex(tab_index)
            APP.processEvents()
            apply_responsive_layout(window)
            polish_settings_layout(window.Ui)
            APP.processEvents()

            for grid in tab.findChildren(QGridLayout):
                parent = grid.parentWidget()
                row_items: dict[int, list[object]] = {}
                for index in range(grid.count()):
                    row, _column, row_span, _column_span = grid.getItemPosition(index)
                    if row_span != 1:
                        continue
                    row_items.setdefault(row, []).append(grid.itemAt(index))

                for row, items in row_items.items():
                    widgets = [
                        widget for item in items for widget in _walk_item_widgets(item) if widget.isVisibleTo(tab)
                    ]
                    if len(widgets) < 2 or not any(_is_compact_control(widget) for widget in widgets):
                        continue
                    if any(_is_multiline(widget) for widget in widgets):
                        continue

                    centers = [widget.mapTo(parent, widget.rect().center()).y() for widget in widgets]
                    context = (
                        tab_index,
                        tab.objectName(),
                        grid.objectName(),
                        row,
                        [widget.objectName() for widget in widgets],
                    )
                    assert max(centers) - min(centers) <= 1, context
                    checked.append(context)

        assert checked
    finally:
        window.close()
        window.deleteLater()
        APP.processEvents()


def test_actor_source_download_link_is_centered_with_radio_buttons():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    _ensure_force_avwiki_actor_checkbox(window.Ui)
    polish_settings_layout(window.Ui)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.Ui.tabWidget.setCurrentWidget(window.Ui.tab_3)
    window.resize(1920, 1080)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    polish_settings_layout(window.Ui)
    APP.processEvents()

    try:
        widgets = (
            window.Ui.label_293,
            window.Ui.radioButton_actor_photo_net,
            window.Ui.radioButton_actor_photo_local,
            window.Ui.label_download_actor_zip,
        )
        parent = window.Ui.gridLayout.parentWidget()
        centers = [widget.mapTo(parent, widget.rect().center()).y() for widget in widgets]
        assert max(centers) - min(centers) <= 1
    finally:
        window.close()
        window.deleteLater()
        APP.processEvents()
