import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QStackedWidget, QTreeWidget, QWidget

from mdcx.controllers.main_window.init import setup_local_nfo_button
from mdcx.controllers.main_window.responsive_layout import (
    BASE_WINDOW_HEIGHT,
    BASE_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    apply_responsive_layout,
    calculate_layout_metrics,
    setup_responsive_ui,
)

APP = QApplication.instance() or QApplication([])


def test_layout_metrics_preserve_designer_baseline_and_fix_result_clipping():
    metrics = calculate_layout_metrics(BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT)

    assert (metrics.stacked_width, metrics.stacked_height) == (820, 692)
    assert (metrics.result_x, metrics.result_width, metrics.result_height) == (590, 220, 533)
    assert metrics.result_x + metrics.result_width <= metrics.stacked_width
    assert metrics.path_width == 786


def test_layout_metrics_keep_usable_result_panel_at_minimum_window_size():
    metrics = calculate_layout_metrics(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

    assert (metrics.stacked_width, metrics.stacked_height) == (761, 642)
    assert metrics.result_width == 161
    assert metrics.result_height == 483
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


def test_apply_responsive_layout_resizes_main_result_and_page_viewports():
    window = _window_harness()
    setup_responsive_ui(window)
    window.show()
    window.resize(1400, 900)
    APP.processEvents()
    apply_responsive_layout(window)

    assert window.minimumWidth() == MIN_WINDOW_WIDTH
    assert window.minimumHeight() == MIN_WINDOW_HEIGHT
    assert window.Ui.stackedWidget.size().width() == 1131
    assert window.Ui.treeWidget_number.geometry().getRect() == (590, 140, 531, 733)
    assert window.Ui.label_result.geometry().getRect() == (590, 70, 531, 40)
    assert window.Ui.textBrowser_net_main.geometry().getRect() == (30, 0, 1101, 892)
    assert window.Ui.tabWidget.geometry().getRect() == (20, 10, 1113, 884)
    assert window._resize_grip.isVisible() is True
    assert not hasattr(window, "_splitter_left")
    assert not hasattr(window, "_splitter_right")
    window.close()
