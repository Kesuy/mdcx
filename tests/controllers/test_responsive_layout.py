from types import SimpleNamespace

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QLabel, QMainWindow, QPushButton, QStackedWidget, QTreeWidget, QWidget

from mdcx.controllers.main_window.init import setup_local_nfo_button
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import (
    BASE_WINDOW_HEIGHT,
    BASE_WINDOW_WIDTH,
    COMPACT_BREAKPOINT,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    NARROW_BREAKPOINT,
    apply_responsive_layout,
    calculate_layout_metrics,
    setup_responsive_ui,
    show_responsive_overlay,
)
from mdcx.controllers.main_window.settings_page import SettingsPageController
from tests.layout_test_support import APP, generated_ui_window


def test_layout_metrics_preserve_designer_baseline_and_fix_result_clipping():
    metrics = calculate_layout_metrics(BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT)

    assert (metrics.stacked_width, metrics.stacked_height) == (820, 692)
    assert (metrics.result_x, metrics.result_width, metrics.result_height) == (590, 220, 533)
    assert metrics.result_x + metrics.result_width <= metrics.stacked_width
    assert metrics.path_width == 786


def test_layout_metrics_keep_usable_result_panel_at_minimum_window_size():
    metrics = calculate_layout_metrics(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

    assert (metrics.stacked_width, metrics.stacked_height) == (820, 692)
    assert metrics.result_width == 220
    assert metrics.result_height == 533
    assert metrics.result_x + metrics.result_width <= metrics.stacked_width


def test_layout_metrics_give_extra_space_to_result_panel():
    metrics = calculate_layout_metrics(1400, 900)

    assert metrics.result_width == 531
    assert metrics.result_height == 733
    assert metrics.viewport_width == 1101
    assert metrics.viewport_height == 892


def test_load_nfo_button_is_adjacent_to_edit_nfo_button():
    page_main = QWidget()
    edit_nfo_button = QPushButton(page_main)
    edit_nfo_button.setGeometry(427, 110, 40, 40)
    window = SimpleNamespace(
        Ui=SimpleNamespace(page_main=page_main, pushButton_open_nfo=edit_nfo_button),
        main_load_nfo_click=lambda: None,
    )

    setup_local_nfo_button(window)

    load_nfo_button = window.Ui.pushButton_load_nfo
    assert load_nfo_button.geometry().right() + 1 == edit_nfo_button.geometry().left()


def _window_harness() -> QMainWindow:
    window = QMainWindow()
    central = QWidget(window)
    window.setCentralWidget(central)
    stacked = QStackedWidget(central)
    page_main = QWidget()
    stacked.addWidget(page_main)

    tree = QTreeWidget(page_main)
    result = QLabel(page_main)
    path = QLabel(page_main)
    line = QWidget(page_main)
    select_button = QPushButton(page_main)
    start_button = QPushButton(page_main)
    clear_button = QPushButton(page_main)
    sort_combo = QWidget(page_main)
    sort_order = QWidget(page_main)

    page_log = QWidget()
    page_net = QWidget()
    page_tool = QWidget()
    page_setting = QWidget()
    page_about = QWidget()
    for page in (page_log, page_net, page_tool, page_setting, page_about):
        stacked.addWidget(page)

    window.Ui = SimpleNamespace(
        centralwidget=central,
        stackedWidget=stacked,
        widget_setting=QWidget(central),
        left_backgroud_widget=QWidget(central),
        label_show_version=QLabel(central),
        label_local_number=QLabel(central),
        progressBar_scrape=QWidget(central),
        page_main=page_main,
        treeWidget_number=tree,
        label_result=result,
        label_file_path=path,
        line_14=line,
        pushButton_select_media_folder=select_button,
        pushButton_start_cap=start_button,
        pushButton_tree_clear=clear_button,
        result_sort_combo=sort_combo,
        result_sort_order_button=sort_order,
        page_log=page_log,
        textBrowser_log_main=QWidget(page_log),
        textBrowser_log_main_2=QWidget(page_log),
        textBrowser_log_main_3=QWidget(page_log),
        pushButton_start_cap2=QPushButton(page_log),
        page_net=page_net,
        textBrowser_net_main=QWidget(page_net),
        pushButton_check_net=QPushButton(page_net),
        page_tool=page_tool,
        scrollArea_10=QWidget(page_tool),
        page_setting=page_setting,
        tabWidget=QWidget(page_setting),
        page_about=page_about,
        textBrowser_about=QWidget(page_about),
    )
    window.result_sort_combo = sort_combo
    window.result_sort_order_button = sort_order
    return window


def test_apply_responsive_layout_does_not_restore_removed_compatibility_geometry():
    window = _window_harness()
    setup_responsive_ui(window)
    window.show()
    window.resize(1400, 900)
    APP.processEvents()
    apply_responsive_layout(window)

    assert window.minimumWidth() == MIN_WINDOW_WIDTH
    assert window.minimumHeight() == MIN_WINDOW_HEIGHT
    assert window.Ui.stackedWidget.size().isEmpty()
    assert not hasattr(window, "_shell_splitter")
    assert not hasattr(window, "_main_splitter")
    assert not hasattr(window, "_simple_page_layouts_ready")
    assert window._resize_grip.isVisible() is True
    assert not hasattr(window, "_splitter_left")
    assert not hasattr(window, "_splitter_right")
    window.close()


def test_standard_compact_and_narrow_breakpoints_are_all_reachable():
    assert MIN_WINDOW_WIDTH < NARROW_BREAKPOINT < COMPACT_BREAKPOINT
    window = generated_ui_window()
    SettingsPageController(window)
    setup_responsive_ui(window)
    window.show()

    window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    apply_responsive_layout(window)
    APP.processEvents()
    assert window._responsive_mode == "narrow"
    assert window._main_splitter.orientation() == Qt.Orientation.Vertical
    assert window.Ui.pushButton_main.text() == ""
    assert window.Ui.pushButton_main.toolTip()

    window.resize(1100, MIN_WINDOW_HEIGHT)
    apply_responsive_layout(window)
    APP.processEvents()
    assert window._responsive_mode == "compact"
    assert window._main_splitter.orientation() == Qt.Orientation.Horizontal
    assert window.Ui.pushButton_main.text()

    window.resize(1400, 900)
    apply_responsive_layout(window)
    APP.processEvents()
    assert window._responsive_mode == "standard"
    window.close()


def test_simple_pages_expand_with_their_layouts_and_log_detail_collapses():
    window = generated_ui_window()
    setup_responsive_ui(window)
    window.resize(1400, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    assert window.Ui.page_log.layout() is not None
    assert window.Ui.page_net.layout() is not None
    assert window.Ui.page_tool.layout() is not None
    assert window.Ui.page_setting.layout() is not None
    assert window.Ui.page_about.layout() is not None

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_net)
    APP.processEvents()
    assert window.Ui.textBrowser_net_main.height() > 700
    assert window.Ui.pushButton_check_net.parentWidget().objectName() == "network_toolbar"
    assert window.Ui.pushButton_check_net.size().width() == 120
    assert window.Ui.pushButton_check_net.size().height() == 40
    button_pos = window.Ui.pushButton_check_net.mapTo(window.Ui.page_net, QPoint())
    assert button_pos.x() + window.Ui.pushButton_check_net.width() == window.Ui.page_net.width() - 10
    assert window.Ui.textBrowser_net_main.geometry().top() > button_pos.y() + window.Ui.pushButton_check_net.height()

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_about)
    APP.processEvents()
    assert window.Ui.textBrowser_about.height() > 700
    assert window.Ui.textBrowser_about.font().family() == window.Ui.textBrowser_log_main.font().family()
    assert window.Ui.textBrowser_about.font().pixelSize() == window.Ui.textBrowser_log_main.font().pixelSize()

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    APP.processEvents()
    assert window.Ui.tabWidget.geometry().bottom() < window.Ui.label_config.geometry().top()
    assert window.Ui.label_config.width() == window.Ui.tabWidget.width()
    assert window.Ui.comboBox_change_config.width() >= 140
    assert window.Ui.pushButton_save_new_config.width() >= 80
    assert window.Ui.pushButton_init_config.width() >= 80
    assert window.Ui.pushButton_save_config.width() >= 160

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_log)
    APP.processEvents()
    assert window.Ui.pushButton_view_failed_list.parentWidget().objectName() == "log_toolbar"
    assert window.Ui.pushButton_start_cap2.parentWidget().objectName() == "log_toolbar"
    assert window.Ui.pushButton_show_hide_logs.parentWidget().objectName() == "log_footer"
    assert window.Ui.pushButton_view_failed_list.size().width() == 101
    assert window.Ui.pushButton_start_cap2.size().width() == 120
    assert window.Ui.pushButton_show_hide_logs.size().width() == 40
    assert window.Ui.pushButton_view_failed_list.x() < window.Ui.pushButton_start_cap2.x()
    expanded_height = window.Ui.textBrowser_log_main.height()
    window.Ui.textBrowser_log_main_2.hide()
    APP.processEvents()
    assert window.Ui.textBrowser_log_main.height() > expanded_height
    window.close()


def test_responsive_overlays_are_centered_fit_and_raise_above_page_content():
    window = generated_ui_window()
    setup_responsive_ui(window)
    window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    for overlay in (window.Ui.widget_show_success, window.Ui.widget_show_tips):
        parent = overlay.parentWidget()
        assert overlay.width() <= parent.width() - 16
        assert overlay.height() <= parent.height() - 16
        assert abs(overlay.geometry().center().x() - parent.rect().center().x()) <= 1
        assert abs(overlay.geometry().center().y() - parent.rect().center().y()) <= 1

    nfo = window.Ui.widget_nfo
    assert nfo.height() <= window.Ui.centralwidget.height() - 16
    assert nfo.layout() is not None
    assert window.Ui.scrollArea_nfo.height() > 400
    nfo_content = window.Ui.scrollAreaWidgetContents_nfo_editor
    assert nfo_content.layout() is not None
    assert window.Ui.lineEdit_nfo_number.parentWidget() is nfo_content
    assert window.Ui.lineEdit_nfo_year.geometry().left() > window.Ui.comboBox_nfo.geometry().right()
    assert window.Ui.lineEdit_nfo_actor.width() > window.Ui.lineEdit_nfo_number.width()
    assert window.Ui.textEdit_nfo_outline.width() == window.Ui.textEdit_nfo_originalplot.width()
    assert window.Ui.lineEdit_nfo_poster.width() == window.Ui.lineEdit_nfo_website.width()

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    show_responsive_overlay(window, window.Ui.widget_show_tips)
    APP.processEvents()
    center = window.Ui.widget_show_tips.geometry().center()
    child = window.Ui.page_setting.childAt(center)
    while child is not None and child.parentWidget() is not window.Ui.page_setting:
        child = child.parentWidget()
    assert child is window.Ui.widget_show_tips

    show_responsive_overlay(window, nfo)
    APP.processEvents()
    center = nfo.geometry().center()
    child = window.Ui.centralwidget.childAt(center)
    while child is not None and child.parentWidget() is not window.Ui.centralwidget:
        child = child.parentWidget()
    assert child is nfo
    window.close()


def test_failed_log_overlay_stays_above_layout_managed_log_widgets():
    window = generated_ui_window()
    setup_responsive_ui(window)
    window.resize(1400, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_log)

    MyMAinWindow.show_hide_failed_list(window, True)
    APP.processEvents()

    child = window.Ui.page_log.childAt(100, 100)
    while child is not None and child.parentWidget() is not window.Ui.page_log:
        child = child.parentWidget()
    assert child is window.Ui.textBrowser_log_main_3
    window.close()
