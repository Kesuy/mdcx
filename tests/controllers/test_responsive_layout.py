import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
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
    COMPACT_BREAKPOINT,
    FORM_SECTION_HORIZONTAL_MARGIN,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    NARROW_BREAKPOINT,
    apply_responsive_layout,
    calculate_layout_metrics,
    setup_responsive_ui,
    show_responsive_overlay,
)
from mdcx.controllers.main_window.settings_page import SettingsPageController
from mdcx.controllers.main_window.style import set_dark_style, set_style
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


def test_standard_compact_and_narrow_breakpoints_are_all_reachable():
    assert MIN_WINDOW_WIDTH < NARROW_BREAKPOINT < COMPACT_BREAKPOINT
    window = _generated_ui_window()
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


def test_tool_page_groups_use_page_owned_layouts_instead_of_fixed_geometry():
    window = _generated_ui_window()

    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    window.resize(1200, 850)
    window.show()
    APP.processEvents()

    for group in (
        window.Ui.groupBox_7,
        window.Ui.groupBox_19,
        window.Ui.groupBox_6,
        window.Ui.groupBox_13,
        window.Ui.groupBox_21,
    ):
        assert group.layout() is not None
        assert group.maximumWidth() == 16777215
        assert group.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding

    assert window.Ui.groupBox_7.layout().indexOf(window.Ui.lineEdit_single_file_path) >= 0
    assert window.Ui.groupBox_19.layout().indexOf(window.Ui.lineEdit_local_library_path) >= 0
    assert window.Ui.groupBox_6.layout().indexOf(window.Ui.lineEdit_escape_dir_move) >= 0
    assert window.Ui.groupBox_13.layout().indexOf(window.Ui.pushButton_select_thumb) >= 0
    assert window.Ui.groupBox_21.layout().indexOf(window.Ui.lineEdit_netdisk_path) >= 0

    for button in (
        window.Ui.pushButton_select_file,
        window.Ui.pushButton_select_file_clear_info,
        window.Ui.pushButton_select_local_library,
        window.Ui.pushButton_select_netdisk_path,
        window.Ui.pushButton_select_localdisk_path,
    ):
        assert button.size().width() == 92
        assert button.size().height() == 34
        assert button.property("toolRole") == "secondary"
    for button in (
        window.Ui.pushButton_start_single_file,
        window.Ui.pushButton_find_missing_number,
        window.Ui.pushButton_move_mp4,
        window.Ui.pushButton_creat_symlink,
    ):
        assert button.size().width() == 220
        assert button.size().height() == 38
        assert button.property("toolRole") == "primary"
    window.close()


def test_primary_workflows_have_accessible_names_buddies_and_tab_order():
    window = _generated_ui_window()

    setup_responsive_ui(window)

    assert window.Ui.pushButton_start_cap.accessibleName() == "开始或停止刮削"
    assert window.result_filter_edit.accessibleName() == "搜索刮削结果"
    assert window.Ui.lineEdit_single_file_path.accessibleName() == "单文件路径"
    assert window.Ui.label_3.buddy() is window.Ui.lineEdit_single_file_path
    assert window.Ui.label_10.buddy() is window.Ui.lineEdit_appoint_url
    assert window.Ui.pushButton_select_media_folder.nextInFocusChain() is window.Ui.pushButton_start_cap
    window.close()


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

    search_row = window._main_result_search_row
    sort_row = window._main_result_sort_row
    assert search_row.geometry().bottom() < sort_row.geometry().top()
    assert window.result_filter_edit.geometry().right() < window.Ui.pushButton_tree_clear.geometry().left()
    assert window.result_status_combo.geometry().right() < window.result_sort_combo.geometry().left()
    assert window.result_sort_combo.geometry().right() < window.result_sort_order_button.geometry().left()
    assert window.result_filter_edit.width() >= 100
    assert window.result_status_combo.width() == 88
    assert window.result_sort_combo.width() >= 116
    assert window.result_sort_order_button.width() == 32
    assert window.Ui.pushButton_tree_clear.width() == 28

    for control in (
        window.result_filter_edit,
        window.result_status_combo,
        window.result_sort_combo,
        window.result_sort_order_button,
        window.Ui.pushButton_tree_clear,
    ):
        top_left = control.mapTo(window._main_result_pane, QPoint(0, 0))
        assert top_left.x() >= 0
        assert top_left.x() + control.width() <= window._main_result_pane.width()

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


def test_result_toolbar_remains_usable_at_baseline_window_width():
    """Protect the 220 px result pane from single-row toolbar regressions."""
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.dark_mode = False
    window.window_radius = 0
    window.window_border = 0
    set_style(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    window.resize(BASE_WINDOW_WIDTH, BASE_WINDOW_HEIGHT)
    window.show()
    APP.processEvents()
    apply_responsive_layout(window)
    APP.processEvents()

    assert window._main_splitter.orientation() == Qt.Orientation.Horizontal
    assert window._main_result_pane.width() >= 252
    assert window._main_result_search_row.geometry().bottom() < window._main_result_sort_row.geometry().top()
    assert window.result_filter_edit.width() >= 100
    assert window.result_sort_combo.width() >= 116
    assert window.result_status_combo.width() >= window.result_status_combo.minimumSizeHint().width()
    assert window.result_sort_combo.width() >= window.result_sort_combo.minimumSizeHint().width()
    assert window.result_filter_edit.geometry().right() < window.Ui.pushButton_tree_clear.geometry().left()
    assert window.result_status_combo.geometry().right() < window.result_sort_combo.geometry().left()
    assert window.result_sort_combo.geometry().right() < window.result_sort_order_button.geometry().left()
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

    assert shell_splitter.handleWidth() == 1
    assert "#FFFFFF" not in shell_splitter.styleSheet()
    assert "#D8DEE9" not in shell_splitter.styleSheet()
    assert window.Ui.left_backgroud_widget.width() == window.Ui.widget_setting.width()
    assert window.Ui.left_backgroud_widget.geometry().right() == window.Ui.widget_setting.rect().right()
    assert window.Ui.label_show_version.width() == window.Ui.widget_setting.width()
    assert window.Ui.stackedWidget.x() == window.Ui.widget_setting.geometry().right() + 2
    assert window.Ui.progressBar_scrape.geometry().top() == 0
    assert window.Ui.progressBar_scrape.geometry().left() == window.Ui.stackedWidget.geometry().left()
    assert window.Ui.progressBar_scrape.width() == window.Ui.stackedWidget.width()
    sidebar_bottom = window.Ui.widget_setting.mapToGlobal(QPoint(0, window.Ui.widget_setting.height() - 1)).y()
    content_bottom = window.Ui.stackedWidget.mapToGlobal(QPoint(0, window.Ui.stackedWidget.height() - 1)).y()
    assert sidebar_bottom == content_bottom

    window.resize(700, 500)
    APP.processEvents()
    assert window.width() >= MIN_WINDOW_WIDTH
    assert window.height() >= MIN_WINDOW_HEIGHT

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
    assert not window.Ui.label_outline.wordWrap()
    assert not window.Ui.label_tag.wordWrap()
    assert window.Ui.label_release.height() == 32
    for label in (
        window.Ui.label_release,
        window.Ui.label_runtime,
        window.Ui.label_director,
        window.Ui.label_series,
        window.Ui.label_studio,
        window.Ui.label_publish,
    ):
        assert not label.wordWrap()
        assert label.alignment() & Qt.AlignmentFlag.AlignVCenter
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
    window = _generated_ui_window()
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
    window = _generated_ui_window()
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


def test_tool_page_expands_layout_managed_forms_and_keeps_scrollbar_at_right():
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
    groups = (
        window.Ui.groupBox_7,
        window.Ui.groupBox_19,
        window.Ui.groupBox_6,
        window.Ui.groupBox_13,
        window.Ui.groupBox_21,
    )
    for group in groups:
        assert group.width() == scroll_area.viewport().width() - 2 * FORM_SECTION_HORIZONTAL_MARGIN
        assert group.layout() is not None
        assert abs(group.geometry().center().x() - content.rect().center().x()) <= 1
        visible_children = [child for child in group.children() if isinstance(child, QWidget) and child.isVisible()]
        assert visible_children
        assert all(group.rect().contains(child.geometry()) for child in visible_children)
    scrollbar_x = scroll_area.verticalScrollBar().mapTo(window.Ui.page_tool, QPoint()).x()
    assert scrollbar_x >= window.Ui.page_tool.width() - 30
    page_margins = window.Ui.page_tool.layout().contentsMargins()
    assert (page_margins.left(), page_margins.top(), page_margins.right(), page_margins.bottom()) == (18, 8, 10, 8)
    content_margins = content.layout().contentsMargins()
    assert (content_margins.left(), content_margins.right()) == (
        FORM_SECTION_HORIZONTAL_MARGIN,
        FORM_SECTION_HORIZONTAL_MARGIN,
    )
    window.close()


def test_tool_page_resyncs_width_when_opened_after_startup_without_window_resize():
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    window.resize(1100, 700)
    window.show()
    APP.processEvents()

    groups = (
        window.Ui.groupBox_7,
        window.Ui.groupBox_19,
        window.Ui.groupBox_6,
        window.Ui.groupBox_13,
        window.Ui.groupBox_21,
    )
    for group in groups:
        group.setMinimumWidth(400)

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    APP.processEvents()

    viewport_width = window.Ui.scrollArea_10.viewport().width()
    expected_width = viewport_width - 2 * FORM_SECTION_HORIZONTAL_MARGIN
    assert expected_width > 400
    assert window.Ui.scrollArea_10.widget().width() == viewport_width
    assert all(group.width() == expected_width for group in groups)
    window.close()


def test_tool_page_reopens_at_top_and_form_controls_share_one_radius():
    window = _generated_ui_window()
    setup_responsive_ui(window)
    window.dark_mode = False
    window.window_radius = 0
    window.window_border = 0
    set_style(window)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_tool)
    window.resize(1200, 720)
    window.show()
    APP.processEvents()

    scroll_bar = window.Ui.scrollArea_10.verticalScrollBar()
    scroll_bar.setValue(scroll_bar.maximum())
    assert scroll_bar.value() > scroll_bar.minimum()
    MyMAinWindow._reset_tool_scroll_position(window)
    assert scroll_bar.value() == scroll_bar.minimum()

    for control in (
        window.Ui.lineEdit_single_file_path,
        window.result_sort_combo,
        window.Ui.plainTextEdit_cookie_javdb,
    ):
        assert control.property("mdcxControlRadius") == 8
        assert control.styleSheet() == ""
        assert "border-radius: 15px" not in control.styleSheet()
    assert "border-radius:8px" in window.Ui.centralwidget.styleSheet().replace(" ", "")

    tool_style = window.Ui.page_tool.styleSheet()
    assert "background: #FFFFFF" in tool_style
    assert "background: #F5F5F6" in tool_style
    assert "margin-top: 10px" not in tool_style
    assert "margin-top: 0" in tool_style
    assert "subcontrol-origin: border" in tool_style
    assert 'QPushButton[toolRole="primary"]' in tool_style
    sidebar_style = window.Ui.widget_setting.styleSheet()
    assert "border-top-right-radius: 0" in sidebar_style
    assert "border-bottom-right-radius: 0" in sidebar_style

    window.dark_mode = True
    set_dark_style(window)
    assert "background: #18222D" in window.Ui.page_tool.styleSheet()
    assert "background: rgba(180, 180, 180, 20)" in window.Ui.page_tool.styleSheet()
    assert "margin-top: 10px" not in window.Ui.page_tool.styleSheet()
    assert "background: #2F3A46" in window._shell_splitter.styleSheet()

    window.dark_mode = False
    set_style(window)
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
