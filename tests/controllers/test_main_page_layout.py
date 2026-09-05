from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSplitter, QWidget

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import (
    BASE_WINDOW_HEIGHT,
    BASE_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    apply_responsive_layout,
    setup_responsive_ui,
)
from mdcx.controllers.main_window.style import set_style
from tests.layout_test_support import APP, generated_ui_window


def test_main_page_uses_complete_three_pane_splitter_with_layout_managed_controls():
    window = generated_ui_window()

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
    """Protect the result pane from single-row toolbar regressions."""
    window = generated_ui_window()
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
    window = generated_ui_window()
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
    window = generated_ui_window()
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
    window = generated_ui_window()
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
