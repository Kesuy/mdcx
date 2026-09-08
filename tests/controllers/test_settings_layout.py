from pathlib import Path

import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QFontDatabase, QWheelEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QAbstractItemView, QComboBox, QGroupBox, QLabel, QScrollArea, QWidget

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import (
    FORM_SECTION_HORIZONTAL_MARGIN,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    apply_responsive_layout,
    setup_responsive_ui,
)
from mdcx.controllers.main_window.settings_page import SettingsPageController
from mdcx.controllers.main_window.style import set_dark_style, set_style
from tests.layout_test_support import APP, generated_ui_window


def test_settings_scrollbars_adapt_to_viewport_and_visible_content(monkeypatch):
    monkeypatch.setattr(MyMAinWindow, "load_config", lambda self: None)
    monkeypatch.setattr(MyMAinWindow, "_finish_startup", lambda self: None)
    window = MyMAinWindow()
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.show()
    saw_scrollbar = saw_fitting_page = False
    try:
        for width, height in ((880, 700), (1600, 1600), (1089, 900)):
            window.resize(width, height)
            for advanced in (True, False):
                window.settings_controller._toggle_advanced(advanced)
                for index in range(window.Ui.tabWidget.count()):
                    window.Ui.tabWidget.setCurrentIndex(index)
                    for _ in range(6):
                        APP.processEvents()
                    assert not window._responsive_content_sync_timer.isActive()
                    for area in window.Ui.tabWidget.currentWidget().findChildren(QScrollArea):
                        bar = area.verticalScrollBar()
                        viewport = area.viewport()
                        context = (width, height, advanced, index, area.objectName())
                        assert area.widget().width() == viewport.width(), context
                        assert bar.maximum() == max(0, area.widget().height() - viewport.height()), context
                        assert bar.pageStep() == viewport.height(), context
                        if bar.maximum():
                            saw_scrollbar = True
                            assert bar.isVisible(), context
                            assert abs(bar.height() - viewport.height()) <= 2, context
                            bar.setValue(bar.maximum())
                            assert area.widget().y() + area.widget().height() == viewport.height(), context
                        else:
                            saw_fitting_page = True
                            assert not bar.isVisible(), context
        assert saw_scrollbar and saw_fitting_page
    finally:
        window.task_manager.shutdown()
        window.hide()
        window.deleteLater()
        APP.processEvents()


@pytest.mark.parametrize("dark", [False, True])
def test_settings_mouse_tabs_scrollbars_and_open_combo_popups(monkeypatch, dark):
    monkeypatch.setattr(MyMAinWindow, "load_config", lambda self: None)
    monkeypatch.setattr(MyMAinWindow, "_finish_startup", lambda self: None)
    window = MyMAinWindow()
    window.dark_mode = dark
    (set_dark_style if dark else set_style)(window)
    window.settings_controller._toggle_advanced(True)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(1089, 700)
    window.show()
    APP.installEventFilter(window)
    visited = set()
    scrolled = 0
    try:
        tabs = window.Ui.tabWidget
        for page_index in range(tabs.count()):
            QTest.mouseClick(tabs.tabBar(), Qt.MouseButton.LeftButton, pos=tabs.tabBar().tabRect(page_index).center())
            APP.processEvents()
            assert tabs.currentIndex() == page_index
            for area in tabs.currentWidget().findChildren(QScrollArea):
                bar = area.verticalScrollBar()
                if bar.maximum() > 0:
                    assert bar.isVisible() and bar.height() > 100, area.objectName()
                    bar.setValue(0)
                    point = QPointF(area.viewport().rect().center())
                    wheel = QWheelEvent(
                        point,
                        point,
                        QPoint(),
                        QPoint(0, -120),
                        Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase,
                        False,
                    )
                    APP.sendEvent(area.viewport(), wheel)
                    assert bar.value() > 0, area.objectName()
                    QTest.keyClick(bar, Qt.Key.Key_End)
                    assert bar.value() == bar.maximum()
                    scrolled += 1
                for combo in area.findChildren(QComboBox):
                    if not combo.isVisible():
                        continue
                    assert combo.count() > 0, combo.objectName()
                    area.ensureWidgetVisible(combo)
                    APP.processEvents()
                    QTest.mouseClick(combo, Qt.MouseButton.LeftButton, pos=combo.rect().center())
                    # Let Qt's popup-opening mouse-release guard expire before
                    # the separate user click selecting an option.
                    QTest.qWait(160)
                    view = combo.view()
                    assert view.isVisible(), combo.objectName()
                    assert view.viewport().height() >= view.sizeHintForRow(0), combo.objectName()
                    index = view.model().index(combo.count() - 1, 0)
                    view.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtBottom)
                    APP.processEvents()
                    rect = view.visualRect(index)
                    assert view.viewport().rect().contains(rect.center()), combo.objectName()
                    QTest.mouseMove(view.viewport(), rect.center())
                    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
                    assert combo.currentIndex() == combo.count() - 1, combo.objectName()
                    visited.add(combo.objectName())
                    combo.hidePopup()
        assert {"comboBox_website_all", "comboBox_fixed_scraping_type"} <= visited
        assert scrolled >= 8
    finally:
        APP.removeEventFilter(window)
        window.task_manager.shutdown()
        window.hide()
        window.deleteLater()
        APP.processEvents()


@pytest.mark.parametrize("width", [880, 1089, 1600])
@pytest.mark.parametrize("advanced", [False, True])
@pytest.mark.parametrize("dark", [False, True])
def test_real_settings_pages_have_no_overlaps_or_stretched_help(monkeypatch, width, advanced, dark):
    # Exercise real dynamic controls, theme, resize callbacks and event delivery.
    # Disable startup I/O and user-config loading, not UI initialization.
    monkeypatch.setattr(MyMAinWindow, "load_config", lambda self: None)
    monkeypatch.setattr(MyMAinWindow, "_finish_startup", lambda self: None)
    # The Windows offscreen plugin does not discover system fonts itself.
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    font_id = QFontDatabase.addApplicationFont(str(font_path)) if font_path.exists() else -1
    window = MyMAinWindow()
    window.dark_mode = dark
    (set_dark_style if dark else set_style)(window)
    window.settings_controller._toggle_advanced(advanced)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(width, 900)
    window.show()
    try:
        for index in range(window.Ui.tabWidget.count()):
            window.Ui.tabWidget.setCurrentIndex(index)
            for _ in range(4):
                APP.processEvents()
                apply_responsive_layout(window)
            page = window.Ui.tabWidget.currentWidget()
            for parent in page.findChildren(QWidget):
                if not parent.isVisible() or parent.layout() is None:
                    continue
                children = [
                    child
                    for child in parent.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)
                    if child.isVisible() and (not isinstance(child, QLabel) or child.text())
                ]
                for position, child in enumerate(children):
                    context = (width, advanced, index, parent.objectName(), child.objectName())
                    assert parent.rect().adjusted(-2, -2, 2, 2).contains(child.geometry()), context
                    for sibling in children[position + 1 :]:
                        overlap = child.geometry().intersected(sibling.geometry())
                        assert overlap.width() <= 2 or overlap.height() <= 2, (*context, sibling.objectName())
                    if (
                        isinstance(child, QLabel)
                        and child.wordWrap()
                        and child.sizePolicy().verticalPolicy() == child.sizePolicy().Policy.Preferred
                    ):
                        expected = max(child.minimumHeight(), child.heightForWidth(child.width()))
                        assert child.height() <= expected + 4, (*context, child.height(), expected)
        assert window.Ui.label_267.text() == "导演语言："
        assert window.Ui.lineEdit_actor_name_max.y() < window.Ui.label_168.y()
        assert window.Ui.lineEdit_actor_name_max.x() == window.Ui.lineEdit_file_name_max.x()
    finally:
        window.hide()
        window.deleteLater()
        APP.processEvents()
        if font_id >= 0:
            QFontDatabase.removeApplicationFont(font_id)


def test_settings_tabs_contents_scrollbars_and_footer_expand_consistently():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    window.dark_mode = False
    window.window_radius = 0
    window.window_border = 0
    set_style(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(1600, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    tab_bar = window.Ui.tabWidget.tabBar()
    assert abs(tab_bar.x() * 2 + tab_bar.width() - window.Ui.tabWidget.width()) <= 4
    assert "QTabWidget::tab-bar" in window.Ui.page_setting.styleSheet()

    first_tab = window.Ui.tabWidget.widget(0)
    first_scroll = window.Ui.scrollArea_2
    first_content = first_scroll.widget()
    first_scrollbar_x = first_scroll.verticalScrollBar().mapTo(window.Ui.tabWidget, QPoint()).x()
    assert first_scroll.width() == first_tab.width()
    assert first_scrollbar_x >= window.Ui.tabWidget.width() - 30
    assert first_content.width() == first_scroll.viewport().width()
    assert window.Ui.groupBox_16.width() > 701
    assert window.Ui.gridLayoutWidget_7.width() > 661
    assert first_content.width() - window.Ui.groupBox_16.geometry().right() - 1 in (29, 30)

    window.Ui.tabWidget.setCurrentIndex(8)
    APP.processEvents()
    APP.processEvents()
    nfo_tab = window.Ui.tabWidget.widget(8)
    nfo_scroll = window.Ui.scrollArea_13
    nfo_scrollbar_x = nfo_scroll.verticalScrollBar().mapTo(window.Ui.tabWidget, QPoint()).x()
    assert nfo_scroll.width() == nfo_tab.width()
    assert nfo_scrollbar_x >= window.Ui.tabWidget.width() - 30
    assert nfo_scroll.widget().width() == nfo_scroll.viewport().width()
    assert window.Ui.groupBox_81.width() > 701
    assert nfo_scroll.widget().layout() is None

    window.Ui.tabWidget.setCurrentIndex(2)
    APP.processEvents()
    website_scroll = window.Ui.scrollArea_8
    website_content = website_scroll.widget()
    assert website_content.layout() is None
    website_separator = window.Ui.layoutWidget1
    assert website_separator.parentWidget() is website_content
    assert website_separator.width() > 701

    window.Ui.tabWidget.setCurrentWidget(window.Ui.tab3)
    window.Ui.plainTextEdit_cookie_javdb.setPlainText("session=" + "x" * 4000)
    network_scroll = window.Ui.scrollArea_3
    network_scroll.verticalScrollBar().setValue(network_scroll.verticalScrollBar().maximum())
    APP.processEvents()
    network_scroll.verticalScrollBar().setValue(network_scroll.verticalScrollBar().minimum())
    APP.processEvents()
    APP.processEvents()

    network_content = window.Ui.scrollAreaWidgetContents_wangluo
    expected_network_width = network_scroll.viewport().width() - 30 - FORM_SECTION_HORIZONTAL_MARGIN
    for group in (window.Ui.groupBox_10, window.Ui.groupBox_28, window.Ui.groupBox_44, window.Ui.groupBox_14):
        assert group.maximumWidth() == 16777215
        assert group.width() in (expected_network_width - 1, expected_network_width)
        assert group.x() == 30
        assert network_content.width() - group.geometry().right() - 1 in (
            FORM_SECTION_HORIZONTAL_MARGIN,
            FORM_SECTION_HORIZONTAL_MARGIN + 1,
        )

    assert all(metrics[1].layout() is None for metrics in window._settings_scroll_metrics)

    for tab_index in range(window.Ui.tabWidget.count()):
        window.Ui.tabWidget.setCurrentIndex(tab_index)
        APP.processEvents()
        for group in window.Ui.tabWidget.currentWidget().findChildren(QGroupBox):
            if not group.isVisible():
                continue
            for child in group.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                if child.isVisible():
                    assert group.rect().adjusted(-2, -2, 2, 2).contains(child.geometry()), (
                        group.objectName(),
                        child.objectName(),
                    )

    assert window.Ui.comboBox_change_config.size().width() == 151
    assert window.Ui.comboBox_change_config.size().height() == 30
    assert window.Ui.pushButton_save_new_config.size().width() == 91
    assert window.Ui.pushButton_save_new_config.size().height() == 40
    assert window.Ui.pushButton_init_config.size().width() == 91
    assert window.Ui.pushButton_init_config.size().height() == 40
    assert window.Ui.pushButton_save_config.size().width() == 200
    assert window.Ui.pushButton_save_config.size().height() == 50
    assert window.Ui.pushButton_save_config.geometry().right() <= window.Ui.label_config.rect().right() - 12
    window.close()


def test_all_settings_tabs_remain_visible_at_minimum_window_width():
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    window.dark_mode = False
    window.window_radius = 0
    window.window_border = 0
    set_style(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    tab_bar = window.Ui.tabWidget.tabBar()
    tab_rects = [tab_bar.tabRect(index) for index in range(tab_bar.count())]
    assert all(tab_bar.tabText(index) == tab_bar.tabText(index).strip() for index in range(tab_bar.count()))
    assert sum(rect.width() for rect in tab_rects) <= tab_bar.width()
    assert tab_rects[0].left() >= 0
    assert tab_rects[-1].right() < tab_bar.width()
    assert "border-radius: 8px" in window.Ui.page_setting.styleSheet()

    window.close()


def test_settings_theme_uses_semantic_properties_without_inline_widget_qss():
    window = generated_ui_window()
    MyMAinWindow._setup_fc2ppvdb_cookie_ui(window)
    MyMAinWindow._setup_baidu_translate_ui(window)
    SettingsPageController(window)
    window.dark_mode = False
    window.window_radius = 0
    window.window_border = 0

    set_style(window)

    inline_widgets = [
        widget.objectName() for widget in window.Ui.page_setting.findChildren(QWidget) if widget.styleSheet().strip()
    ]
    assert inline_widgets == []
    assert window.Ui.label_javbus_cookie_section.property("sectionTitle") is True
    assert window.Ui.plainTextEdit_cookie_fc2ppvdb.property("cookieEditor") is True
    assert window.Ui.label_name_template_preview_result.property("statusRole") == "neutral"
    window.close()
