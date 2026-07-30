import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from mdcx.controllers.main_window.init import setup_local_nfo_button
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import (
    BASE_WINDOW_HEIGHT,
    BASE_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    apply_responsive_layout,
    calculate_layout_metrics,
    setup_responsive_ui,
    show_responsive_overlay,
)
from mdcx.views.MDCx import Ui_MDCx

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


def _generated_ui_window() -> QMainWindow:
    window = QMainWindow()
    window.Ui = Ui_MDCx()
    window.Ui.setupUi(window)
    window._sort_success_results = lambda: None
    window._toggle_result_sort_order = lambda: None
    window.main_load_nfo_click = lambda: None

    from mdcx.controllers.main_window.init import setup_result_sort_ui

    setup_result_sort_ui(window)
    setup_local_nfo_button(window)
    return window


def test_main_page_uses_complete_three_pane_splitter_with_layout_managed_controls():
    window = _generated_ui_window()

    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    window.resize(1400, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    shell_splitter = window._shell_splitter
    assert isinstance(shell_splitter, QSplitter)
    assert shell_splitter.orientation() == Qt.Orientation.Horizontal
    assert shell_splitter.count() == 2
    assert shell_splitter.widget(0) is window.Ui.widget_setting
    assert shell_splitter.widget(1) is window.Ui.stackedWidget
    assert all(not shell_splitter.isCollapsible(index) for index in range(2))

    content_splitter = window._main_splitter
    assert isinstance(content_splitter, QSplitter)
    assert content_splitter.orientation() == Qt.Orientation.Horizontal
    assert content_splitter.count() == 2
    assert [content_splitter.widget(index).sizePolicy().horizontalStretch() for index in range(2)] == [5, 2]
    assert all(not content_splitter.isCollapsible(index) for index in range(2))

    assert window._main_detail_pane.isAncestorOf(window.Ui.label_number)
    assert window._main_detail_pane.isAncestorOf(window.Ui.label_poster)
    assert window._main_detail_pane.isAncestorOf(window.Ui.label_release)
    assert window._main_detail_pane.isAncestorOf(window.Ui.label_publish)
    assert window.Ui.treeWidget_number.parentWidget() is window._main_result_pane
    assert window.Ui.pushButton_start_cap.parentWidget() is window._main_top_bar
    assert window.Ui.pushButton_select_media_folder.size().width() == 101
    assert window.Ui.pushButton_start_cap.size().width() == 120
    assert window.Ui.treeWidget_number.width() >= window.Ui.treeWidget_number.minimumWidth()
    assert 200 <= window.Ui.label_poster.height() <= 300
    assert 200 <= window.Ui.label_thumb.height() <= 300

    window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    APP.processEvents()
    assert window._main_detail_pane.width() >= window._main_detail_pane.minimumWidth()
    assert window._main_result_pane.width() >= window._main_result_pane.minimumWidth()
    assert window.Ui.pushButton_select_media_folder.width() == 101
    assert window.Ui.pushButton_start_cap.width() == 120

    visible_direct_children = {
        child.objectName()
        for child in window.Ui.page_main.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)
        if child.isVisible()
    }
    assert visible_direct_children == {"main_top_bar", "line_14", "main_content_splitter"}
    window.close()


def test_sidebar_and_artwork_follow_splitter_resizes_without_leaving_gaps():
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    window.resize(1400, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    shell_splitter = window._shell_splitter
    shell_splitter.setSizes([270, shell_splitter.width() - 270])
    shell_splitter.splitterMoved.emit(270, 1)
    APP.processEvents()
    APP.processEvents()

    assert shell_splitter.handleWidth() == 3
    assert "background: transparent" in shell_splitter.styleSheet()
    assert window.Ui.left_backgroud_widget.width() == window.Ui.widget_setting.width()
    assert window.Ui.left_backgroud_widget.geometry().right() == window.Ui.widget_setting.rect().right()
    assert window.Ui.label_show_version.width() == window.Ui.widget_setting.width()

    content_splitter = window._main_splitter
    expanded_height = window.Ui.label_poster.height()
    content_splitter.setSizes([520, content_splitter.width() - 520])
    content_splitter.splitterMoved.emit(520, 1)
    APP.processEvents()
    APP.processEvents()

    poster = window.Ui.label_poster.size()
    thumb = window.Ui.label_thumb.size()
    assert poster.height() < expanded_height
    assert abs(poster.width() / poster.height() - 156 / 220) < 0.01
    assert abs(thumb.width() / thumb.height() - 328 / 220) < 0.01
    assert poster.height() == thumb.height()
    window.close()


def test_preview_pixmaps_keep_source_aspect_ratio_and_center_in_frames():
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.resize(1400, 900)
    window.show()
    APP.processEvents()

    poster_source = QPixmap(1200, 1200)
    poster_source.fill(Qt.GlobalColor.red)
    thumb_source = QPixmap(1600, 900)
    thumb_source.fill(Qt.GlobalColor.blue)
    window._poster_source_pixmap = poster_source
    window._thumb_source_pixmap = thumb_source
    window.refresh_preview_pixmaps = lambda: (
        MyMAinWindow._render_preview_pixmap(window.Ui.label_poster, window._poster_source_pixmap),
        MyMAinWindow._render_preview_pixmap(window.Ui.label_thumb, window._thumb_source_pixmap),
    )
    window.refresh_preview_pixmaps()

    poster_display = window.Ui.label_poster.pixmap().size()
    thumb_display = window.Ui.label_thumb.pixmap().size()
    assert poster_display.width() == poster_display.height()
    assert abs(thumb_display.width() / thumb_display.height() - 16 / 9) < 0.01
    assert poster_display.width() <= window.Ui.label_poster.width()
    assert poster_display.height() <= window.Ui.label_poster.height()
    assert thumb_display.width() <= window.Ui.label_thumb.width()
    assert thumb_display.height() <= window.Ui.label_thumb.height()
    assert window.Ui.label_poster.alignment() == Qt.AlignmentFlag.AlignCenter
    assert window.Ui.label_thumb.alignment() == Qt.AlignmentFlag.AlignCenter
    window.close()


def test_main_metadata_rows_keep_the_original_fifty_pixel_rhythm():
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    window.resize(1400, 900)
    window.show()
    APP.processEvents()

    def detail_y(widget):
        return widget.mapTo(window._main_detail_pane, QPoint(0, 0)).y()

    assert detail_y(window.Ui.label_33) - detail_y(window.Ui.label_18) == 50
    assert detail_y(window.Ui.label_23) - detail_y(window.Ui.label_13) == 50
    assert detail_y(window.Ui.label_30) - detail_y(window.Ui.label_23) == 50
    assert window.Ui.label_outline.height() == 32
    assert window.Ui.label_release.height() == 32
    window.close()


def test_simple_pages_expand_with_their_layouts_and_log_detail_collapses():
    window = _generated_ui_window()
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


def test_settings_tabs_contents_scrollbars_and_footer_expand_consistently():
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.resize(1600, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    tab_bar = window.Ui.tabWidget.tabBar()
    assert abs(tab_bar.x() * 2 + tab_bar.width() - window.Ui.tabWidget.width()) <= 4
    assert "QTabWidget::tab-bar { alignment: center; }" in window.Ui.tabWidget.styleSheet()

    first_tab = window.Ui.tabWidget.widget(0)
    first_scroll = window.Ui.scrollArea_2
    first_content = first_scroll.widget()
    first_scrollbar_x = first_scroll.verticalScrollBar().mapTo(window.Ui.tabWidget, QPoint()).x()
    assert first_scroll.width() == first_tab.width()
    assert first_scrollbar_x >= window.Ui.tabWidget.width() - 30
    assert first_content.width() == first_scroll.viewport().width()
    assert window.Ui.groupBox_16.width() > 701
    assert window.Ui.gridLayoutWidget_7.width() > 661
    assert first_content.width() - window.Ui.groupBox_16.geometry().right() - 1 == 29

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


def test_tool_page_centers_its_fixed_width_forms_and_keeps_scrollbar_at_right():
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    window.resize(1600, 900)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    scroll_area = window.Ui.scrollArea_10
    content = scroll_area.widget()
    assert content.width() == scroll_area.viewport().width()
    assert isinstance(content.layout(), QVBoxLayout)
    assert content.layout().spacing() == 18
    for group in (window.Ui.groupBox_7, window.Ui.groupBox_13, window.Ui.groupBox_19):
        assert abs(group.geometry().center().x() - content.rect().center().x()) <= 1
    scrollbar_x = scroll_area.verticalScrollBar().mapTo(window.Ui.page_tool, QPoint()).x()
    assert scrollbar_x >= window.Ui.page_tool.width() - 30
    window.close()


def test_responsive_overlays_are_centered_fit_and_raise_above_page_content():
    window = _generated_ui_window()
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
    window = _generated_ui_window()
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
