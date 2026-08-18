from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRect, QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .ui_text import set_elided_label_text

if TYPE_CHECKING:
    from .main_window import MyMAinWindow

BASE_WINDOW_WIDTH = 1089
BASE_WINDOW_HEIGHT = 700
MIN_WINDOW_WIDTH = 1030
MIN_WINDOW_HEIGHT = 650
STACKED_LEFT = 210
STACKED_TOP = 6
STACKED_RIGHT_MARGIN = 59
STACKED_BOTTOM_MARGIN = 2
RESULT_LEFT = 590
RESULT_RIGHT_MARGIN = 10
DETAIL_FIELD_ROW_HEIGHT = 50
MAIN_SUMMARY_HEIGHT = 80
IMAGE_FOOTER_HEIGHT = 30
IMAGE_MIN_HEIGHT = 160
IMAGE_MAX_HEIGHT = 280
POSTER_ASPECT_WIDTH = 156
THUMB_ASPECT_WIDTH = 328
IMAGE_ASPECT_HEIGHT = 220


@dataclass(frozen=True)
class LayoutMetrics:
    window_width: int
    window_height: int
    stacked_width: int
    stacked_height: int
    width_delta: int
    height_delta: int
    result_x: int
    result_width: int
    result_height: int
    path_width: int
    line_width: int
    viewport_width: int
    viewport_height: int


def calculate_layout_metrics(window_width: int, window_height: int) -> LayoutMetrics:
    width = max(MIN_WINDOW_WIDTH, window_width)
    height = max(MIN_WINDOW_HEIGHT, window_height)
    stacked_width = width - STACKED_LEFT - STACKED_RIGHT_MARGIN
    stacked_height = height - STACKED_TOP - STACKED_BOTTOM_MARGIN
    width_delta = stacked_width - 820
    height_delta = stacked_height - 692
    return LayoutMetrics(
        window_width=width,
        window_height=height,
        stacked_width=stacked_width,
        stacked_height=stacked_height,
        width_delta=width_delta,
        height_delta=height_delta,
        result_x=RESULT_LEFT,
        result_width=max(160, stacked_width - RESULT_LEFT - RESULT_RIGHT_MARGIN),
        result_height=max(300, stacked_height - 159),
        path_width=max(727, stacked_width - 34),
        line_width=max(712, stacked_width - 49),
        viewport_width=max(731, stacked_width - 30),
        viewport_height=max(642, stacked_height),
    )


def _set_geometry(widget, x: int, y: int, width: int, height: int) -> None:
    widget.setGeometry(QRect(x, y, max(1, width), max(1, height)))


def _make_container(parent: QWidget, object_name: str, layout_type=QVBoxLayout) -> tuple[QWidget, object]:
    container = QWidget(parent)
    container.setObjectName(object_name)
    layout = layout_type(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    return container, layout


def _set_fixed_size(widget: QWidget, width: int, height: int) -> None:
    widget.setMinimumSize(width, height)
    widget.setMaximumSize(width, height)


def _add_underlined_field(
    layout: QGridLayout,
    parent: QWidget,
    caption: QWidget,
    value: QWidget,
    line: QWidget,
    row: int,
    column: int,
) -> None:
    field, field_layout = _make_container(parent, f"{value.objectName()}_field")
    field_layout.setSpacing(0)
    field.setFixedHeight(DETAIL_FIELD_ROW_HEIGHT)
    caption.setFixedHeight(DETAIL_FIELD_ROW_HEIGHT)
    caption.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    value.setWordWrap(False)
    value.setMinimumHeight(30)
    value.setMaximumHeight(32)
    line.setMinimumHeight(18)
    line.setMaximumHeight(18)
    field_layout.addWidget(value, 1)
    field_layout.addWidget(line)
    caption.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
    value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.setRowMinimumHeight(row, DETAIL_FIELD_ROW_HEIGHT)
    layout.addWidget(caption, row, column)
    layout.addWidget(field, row, column + 1)


def _sync_shell_sidebar(window: "MyMAinWindow") -> None:
    if not hasattr(window, "_shell_splitter"):
        return

    ui = window.Ui
    splitter = window._shell_splitter
    sidebar_width = ui.widget_setting.width()
    content_width = max(1, splitter.width() - sidebar_width)
    _set_geometry(ui.left_backgroud_widget, 0, 0, sidebar_width, splitter.height())
    _set_geometry(ui.label_show_version, 0, max(0, splitter.height() - 211), sidebar_width, 201)
    _set_geometry(ui.label_local_number, 0, max(0, splitter.height() - 21), 21, 21)
    _set_geometry(ui.progressBar_scrape, sidebar_width - 1, -1, content_width + 3, 7)


def _sync_after_shell_splitter_move(window: "MyMAinWindow") -> None:
    _sync_shell_sidebar(window)
    _schedule_content_pane_sync(window)


def _sync_content_panes(window: "MyMAinWindow") -> None:
    _sync_main_image_sizes(window)
    _sync_settings_scroll_areas(window)
    _sync_tool_scroll_area(window)


def _schedule_content_pane_sync(window: "MyMAinWindow") -> None:
    timer = getattr(window, "_responsive_content_sync_timer", None)
    if timer is None:
        timer = QTimer(window)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: _sync_content_panes(window))
        window._responsive_content_sync_timer = timer
    timer.start(0)


def _setup_shell_splitter(window: "MyMAinWindow") -> None:
    if hasattr(window, "_shell_splitter"):
        return

    ui = window.Ui
    splitter = QSplitter(Qt.Orientation.Horizontal, ui.centralwidget)
    splitter.setObjectName("window_shell_splitter")
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(3)
    splitter.setStyleSheet("QSplitter#window_shell_splitter::handle:horizontal { background: transparent; }")
    splitter.addWidget(ui.widget_setting)
    splitter.addWidget(ui.stackedWidget)
    ui.widget_setting.setMinimumWidth(180)
    ui.widget_setting.setMaximumWidth(280)
    ui.stackedWidget.setMinimumWidth(760)
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)
    splitter.setCollapsible(0, False)
    splitter.setCollapsible(1, False)
    splitter.setSizes([STACKED_LEFT, BASE_WINDOW_WIDTH - STACKED_LEFT])
    splitter.splitterMoved.connect(lambda *_: _sync_after_shell_splitter_move(window))
    window._shell_splitter = splitter


def _sync_main_image_sizes(window: "MyMAinWindow") -> None:
    if not hasattr(window, "_main_image_row"):
        return

    ui = window.Ui
    detail_pane = window._main_detail_pane
    image_layout = window._main_image_row.layout()
    spacing = max(0, image_layout.horizontalSpacing())
    caption_width = max(50, ui.label_poster1.sizeHint().width())
    available_width = max(
        1,
        detail_pane.width() - caption_width - spacing * 3,
    )
    height_from_width = available_width * IMAGE_ASPECT_HEIGHT // (POSTER_ASPECT_WIDTH + THUMB_ASPECT_WIDTH)
    available_height = (
        detail_pane.height()
        - MAIN_SUMMARY_HEIGHT
        - DETAIL_FIELD_ROW_HEIGHT * 5
        - IMAGE_FOOTER_HEIGHT
        - detail_pane.layout().spacing() * 3
    )
    height_limits = [IMAGE_MAX_HEIGHT, height_from_width]
    if available_height >= IMAGE_MIN_HEIGHT:
        height_limits.append(available_height)
    image_height = max(
        IMAGE_MIN_HEIGHT,
        min(height_limits),
    )
    poster_width = round(image_height * POSTER_ASPECT_WIDTH / IMAGE_ASPECT_HEIGHT)
    thumb_width = round(image_height * THUMB_ASPECT_WIDTH / IMAGE_ASPECT_HEIGHT)

    _set_fixed_size(ui.label_poster, poster_width, image_height)
    _set_fixed_size(ui.label_thumb, thumb_width, image_height)
    _set_fixed_size(ui.label_poster_size, poster_width, IMAGE_FOOTER_HEIGHT)
    _set_fixed_size(window._main_image_info, thumb_width, IMAGE_FOOTER_HEIGHT)
    window._main_image_row.setFixedHeight(image_height + IMAGE_FOOTER_HEIGHT)
    refresh_preview_pixmaps = getattr(window, "refresh_preview_pixmaps", None)
    if refresh_preview_pixmaps is not None:
        refresh_preview_pixmaps()
    for label in (
        ui.label_number,
        ui.label_outline,
        ui.label_tag,
        ui.label_release,
        ui.label_runtime,
        ui.label_director,
        ui.label_series,
        ui.label_studio,
        ui.label_publish,
    ):
        full_text = label.property("mdcxFullText")
        if full_text is not None:
            set_elided_label_text(label, full_text, mode=Qt.TextElideMode.ElideRight)
    restore_source_tooltip = getattr(window, "_restore_number_source_tooltip", None)
    if restore_source_tooltip is not None:
        restore_source_tooltip()


def _setup_main_page_layout(window: "MyMAinWindow") -> None:
    if hasattr(window, "_main_splitter"):
        return

    ui = window.Ui
    page_layout = QVBoxLayout(ui.page_main)
    page_layout.setContentsMargins(18, 8, 10, 8)
    page_layout.setSpacing(6)

    window._main_top_bar, top_layout = _make_container(ui.page_main, "main_top_bar", QHBoxLayout)
    top_layout.addWidget(ui.label_file_path, 1)
    _set_fixed_size(ui.pushButton_select_media_folder, 101, 40)
    _set_fixed_size(ui.pushButton_start_cap, 120, 40)
    top_layout.addWidget(ui.pushButton_select_media_folder)
    top_layout.addWidget(ui.pushButton_start_cap)
    page_layout.addWidget(window._main_top_bar)
    page_layout.addWidget(ui.line_14)

    splitter = QSplitter(Qt.Orientation.Horizontal, ui.page_main)
    splitter.setObjectName("main_content_splitter")
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(5)
    window._main_splitter = splitter

    # Keep the original movie-detail composition together as the middle column.
    # Splitting metadata and artwork into separate panes creates an unintended
    # fourth visual column once the navigation sidebar is counted.
    window._main_detail_pane, detail_pane_layout = _make_container(splitter, "main_detail_pane")
    detail_pane_layout.setSpacing(6)

    summary_panel, summary_layout = _make_container(window._main_detail_pane, "main_summary_panel", QGridLayout)
    summary_panel.setFixedHeight(MAIN_SUMMARY_HEIGHT)
    summary_layout.setVerticalSpacing(0)
    summary_layout.setRowMinimumHeight(0, 40)
    summary_layout.setRowMinimumHeight(1, 40)
    summary_layout.setColumnStretch(1, 2)
    summary_layout.setColumnStretch(3, 2)
    summary_layout.addWidget(ui.label_number1, 0, 0)
    summary_layout.addWidget(ui.label_number, 0, 1)
    summary_layout.addWidget(ui.label_actor1, 0, 2)
    summary_layout.addWidget(ui.label_actor, 0, 3)
    summary_layout.addWidget(ui.label_source, 0, 4)
    summary_layout.addWidget(ui.label_title1, 1, 0)
    summary_layout.addWidget(ui.label_title, 1, 1)

    action_bar, action_layout = _make_container(summary_panel, "main_preview_actions", QHBoxLayout)
    for button in (
        ui.pushButton_load_nfo,
        ui.pushButton_open_nfo,
        ui.pushButton_open_folder,
        ui.pushButton_play,
        ui.pushButton_right_menu,
    ):
        _set_fixed_size(button, 40, 40)
        action_layout.addWidget(button)
    summary_layout.addWidget(action_bar, 1, 2, 1, 3, Qt.AlignmentFlag.AlignRight)
    detail_pane_layout.addWidget(summary_panel)

    image_row, image_layout = _make_container(window._main_detail_pane, "main_image_row", QGridLayout)
    window._main_image_row = image_row
    image_layout.setVerticalSpacing(0)
    image_layout.setColumnStretch(3, 1)
    image_layout.addWidget(ui.label_poster1, 0, 0, Qt.AlignmentFlag.AlignTop)
    for image_label, column in ((ui.label_poster, 1), (ui.label_thumb, 2)):
        image_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        image_layout.addWidget(
            image_label,
            0,
            column,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
    image_layout.addWidget(ui.label_poster_size, 1, 1)
    image_info, image_info_layout = _make_container(image_row, "main_image_info", QHBoxLayout)
    window._main_image_info = image_info
    image_info_layout.addWidget(ui.label_thumb_size, 1)
    image_info_layout.addWidget(ui.checkBox_cover)
    image_layout.addWidget(image_info, 1, 2)
    detail_pane_layout.addWidget(image_row)

    detail_panel, detail_layout = _make_container(window._main_detail_pane, "main_text_detail_panel", QGridLayout)
    detail_panel.setFixedHeight(DETAIL_FIELD_ROW_HEIGHT * 2)
    detail_layout.setSpacing(0)
    detail_layout.setColumnStretch(1, 1)
    ui.label_outline.setWordWrap(False)
    ui.label_tag.setWordWrap(False)
    _add_underlined_field(detail_layout, detail_panel, ui.label_18, ui.label_outline, ui.line_6, 0, 0)
    _add_underlined_field(detail_layout, detail_panel, ui.label_33, ui.label_tag, ui.line_7, 1, 0)
    detail_pane_layout.addWidget(detail_panel)

    metadata_panel, metadata_layout = _make_container(window._main_detail_pane, "main_metadata_panel", QGridLayout)
    metadata_panel.setFixedHeight(DETAIL_FIELD_ROW_HEIGHT * 3)
    metadata_layout.setSpacing(0)
    metadata_layout.setColumnStretch(1, 1)
    metadata_layout.setColumnStretch(3, 1)
    for row, left_field, right_field in (
        (0, (ui.label_13, ui.label_release, ui.line_8), (ui.label_22, ui.label_runtime, ui.line_9)),
        (1, (ui.label_23, ui.label_director, ui.line_12), (ui.label_31, ui.label_series, ui.line_10)),
        (2, (ui.label_30, ui.label_studio, ui.line_13), (ui.label_24, ui.label_publish, ui.line_11)),
    ):
        _add_underlined_field(metadata_layout, metadata_panel, *left_field, row, 0)
        _add_underlined_field(metadata_layout, metadata_panel, *right_field, row, 2)
    detail_pane_layout.addWidget(metadata_panel)
    detail_pane_layout.addStretch(1)

    window._main_result_pane, result_layout = _make_container(splitter, "main_result_pane")
    result_layout.addWidget(ui.label_result)
    result_sort_bar, result_sort_layout = _make_container(window._main_result_pane, "main_result_sort_bar", QHBoxLayout)
    _set_fixed_size(window.result_sort_combo, 130, 26)
    _set_fixed_size(window.result_sort_order_button, 34, 26)
    _set_fixed_size(ui.pushButton_tree_clear, 20, 20)
    result_sort_layout.addWidget(window.result_sort_combo)
    result_sort_layout.addWidget(window.result_sort_order_button)
    result_sort_layout.addStretch(1)
    result_sort_layout.addWidget(ui.pushButton_tree_clear)
    result_layout.addWidget(result_sort_bar)
    ui.treeWidget_number.setMinimumWidth(220)
    result_layout.addWidget(ui.treeWidget_number, 1)

    window._main_detail_pane.setMinimumWidth(520)
    window._main_result_pane.setMinimumWidth(220)
    for index, factor in enumerate((5, 2)):
        splitter.setStretchFactor(index, factor)
        splitter.setCollapsible(index, False)
    splitter.setSizes([570, 240])
    splitter.splitterMoved.connect(lambda *_: _sync_main_image_sizes(window))
    page_layout.addWidget(splitter, 1)


def _setup_settings_scroll_areas(window: "MyMAinWindow") -> None:
    ui = window.Ui
    ui.tabWidget.tabBar().setExpanding(False)
    ui.tabWidget.setStyleSheet(f"{ui.tabWidget.styleSheet()}\nQTabWidget::tab-bar {{ alignment: center; }}")

    scroll_metrics = []
    for index in range(ui.tabWidget.count()):
        tab = ui.tabWidget.widget(index)
        scroll_areas = tab.findChildren(
            QScrollArea,
            options=Qt.FindChildOption.FindDirectChildrenOnly,
        )
        if len(scroll_areas) != 1:
            continue

        scroll_area = scroll_areas[0]
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        tab_layout.addWidget(scroll_area)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = scroll_area.widget()
        content_width = content.width()
        content_height = content.height()
        group_metrics = []
        for group in content.findChildren(
            QGroupBox,
            options=Qt.FindChildOption.FindDirectChildrenOnly,
        ):
            group.setMaximumWidth(16777215)
            group_right_margin = content_width - group.geometry().right() - 1
            holder_metrics = []
            for holder in group.findChildren(
                QWidget,
                options=Qt.FindChildOption.FindDirectChildrenOnly,
            ):
                if holder.layout() is None or holder.width() < group.width() * 3 // 4:
                    continue
                holder_right_margin = group.width() - holder.geometry().right() - 1
                holder_metrics.append((holder, holder_right_margin))
            group_metrics.append((group, group_right_margin, holder_metrics))

        scroll_metrics.append((scroll_area, content, content_width, content_height, group_metrics))

    window._settings_scroll_metrics = scroll_metrics
    ui.tabWidget.currentChanged.connect(lambda *_: _schedule_content_pane_sync(window))


def _sync_settings_scroll_areas(window: "MyMAinWindow") -> None:
    for scroll_area, content, base_width, base_height, group_metrics in getattr(
        window,
        "_settings_scroll_metrics",
        (),
    ):
        content_width = max(base_width, scroll_area.viewport().width())
        content.resize(content_width, base_height)
        for group, group_right_margin, holder_metrics in group_metrics:
            group.resize(
                max(1, content_width - group.x() - group_right_margin),
                group.height(),
            )
            for holder, holder_right_margin in holder_metrics:
                holder.resize(
                    max(1, group.width() - holder.x() - holder_right_margin),
                    holder.height(),
                )


def _setup_tool_scroll_area(window: "MyMAinWindow") -> None:
    scroll_area = window.Ui.scrollArea_10
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_area.setWidgetResizable(True)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    content = scroll_area.widget()
    groups = sorted(
        content.findChildren(
            QGroupBox,
            options=Qt.FindChildOption.FindDirectChildrenOnly,
        ),
        key=lambda group: group.y(),
    )
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(12, 12, 12, 12)
    content_layout.setSpacing(18)
    for group in groups:
        # These designer groups contain absolutely positioned children and
        # therefore report a title-only sizeHint(). Preserve their authored
        # geometry before putting them in a layout, otherwise Qt collapses
        # every form to a one-line group-box title.
        group.setFixedSize(group.size())
        group.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        content_layout.addWidget(group, 0, Qt.AlignmentFlag.AlignHCenter)
    content_layout.addStretch(1)
    window._tool_scroll_metrics = (scroll_area, content, groups)


def _sync_tool_scroll_area(window: "MyMAinWindow") -> None:
    metrics = getattr(window, "_tool_scroll_metrics", None)
    if metrics is None:
        return

    scroll_area, content, _groups = metrics
    content.setMinimumWidth(max(1, scroll_area.viewport().width()))


def _setup_overlay_layouts(window: "MyMAinWindow") -> None:
    if hasattr(window, "_responsive_overlay_sizes"):
        return

    ui = window.Ui

    success_layout = QVBoxLayout(ui.widget_show_success)
    success_layout.setContentsMargins(10, 6, 10, 10)
    success_layout.setSpacing(6)
    success_layout.addWidget(ui.label_success_title)
    success_layout.addWidget(ui.textBrowser_show_success_list, 1)
    success_footer = QHBoxLayout()
    success_footer.addStretch(1)
    for button in (
        ui.pushButton_success_list_clear,
        ui.pushButton_success_list_save,
        ui.pushButton_success_list_close,
    ):
        _set_fixed_size(button, 91, 40)
        success_footer.addWidget(button)
    success_footer.addStretch(1)
    success_layout.addLayout(success_footer)

    tips_layout = QVBoxLayout(ui.widget_show_tips)
    tips_layout.setContentsMargins(10, 6, 10, 10)
    tips_layout.setSpacing(6)
    tips_layout.addWidget(ui.label_show_tips_title)
    tips_layout.addWidget(ui.textBrowser_show_tips, 1)
    tips_footer = QHBoxLayout()
    tips_footer.addStretch(1)
    _set_fixed_size(ui.pushButton_show_tips_close, 91, 40)
    tips_footer.addWidget(ui.pushButton_show_tips_close)
    tips_footer.addStretch(1)
    tips_layout.addLayout(tips_footer)

    nfo_layout = QVBoxLayout(ui.widget_nfo)
    nfo_layout.setContentsMargins(10, 6, 10, 10)
    nfo_layout.setSpacing(6)
    nfo_layout.addWidget(ui.label_4)
    nfo_layout.addWidget(ui.scrollArea_nfo, 1)
    nfo_footer = QHBoxLayout()
    nfo_footer.addWidget(ui.label_save_tips, 1)
    _set_fixed_size(ui.pushButton_nfo_save, 91, 40)
    _set_fixed_size(ui.pushButton_nfo_close, 91, 40)
    nfo_footer.addWidget(ui.pushButton_nfo_save)
    nfo_footer.addWidget(ui.pushButton_nfo_close)
    nfo_layout.addLayout(nfo_footer)

    window._responsive_overlay_sizes = {
        ui.widget_show_success: QSize(811, 511),
        ui.widget_show_tips: QSize(811, 511),
        ui.widget_nfo: QSize(791, 681),
    }
    for widget in window._responsive_overlay_sizes:
        widget.hide()


def _sync_overlay_widgets(window: "MyMAinWindow") -> None:
    for widget, preferred_size in getattr(window, "_responsive_overlay_sizes", {}).items():
        parent = widget.parentWidget()
        width = min(preferred_size.width(), max(1, parent.width() - 16))
        height = min(preferred_size.height(), max(1, parent.height() - 16))
        _set_geometry(
            widget,
            max(0, (parent.width() - width) // 2),
            max(0, (parent.height() - height) // 2),
            width,
            height,
        )
        if not widget.isHidden():
            widget.raise_()


def show_responsive_overlay(window: "MyMAinWindow", widget: QWidget) -> None:
    _sync_overlay_widgets(window)
    widget.show()
    widget.raise_()


def _setup_simple_page_layouts(window: "MyMAinWindow") -> None:
    if hasattr(window, "_simple_page_layouts_ready"):
        return
    ui = window.Ui

    log_layout = QVBoxLayout(ui.page_log)
    log_layout.setContentsMargins(18, 8, 10, 8)
    log_layout.setSpacing(6)
    log_toolbar, log_toolbar_layout = _make_container(ui.page_log, "log_toolbar", QHBoxLayout)
    log_toolbar_layout.addStretch(1)
    _set_fixed_size(ui.pushButton_view_failed_list, 101, 40)
    _set_fixed_size(ui.pushButton_start_cap2, 120, 40)
    log_toolbar_layout.addWidget(ui.pushButton_view_failed_list)
    log_toolbar_layout.addWidget(ui.pushButton_start_cap2)
    log_layout.addWidget(log_toolbar)
    window._log_splitter = QSplitter(Qt.Orientation.Vertical, ui.page_log)
    window._log_splitter.setObjectName("log_content_splitter")
    window._log_splitter.setChildrenCollapsible(False)
    window._log_splitter.addWidget(ui.textBrowser_log_main)
    window._log_splitter.addWidget(ui.textBrowser_log_main_2)
    window._log_splitter.setStretchFactor(0, 3)
    window._log_splitter.setStretchFactor(1, 2)
    window._log_splitter.setSizes([420, 270])
    log_layout.addWidget(window._log_splitter, 1)
    log_footer, log_footer_layout = _make_container(ui.page_log, "log_footer", QHBoxLayout)
    _set_fixed_size(ui.pushButton_show_hide_logs, 40, 40)
    log_footer_layout.addWidget(ui.pushButton_show_hide_logs)
    log_footer_layout.addStretch(1)
    log_layout.addWidget(log_footer)

    net_layout = QVBoxLayout(ui.page_net)
    net_layout.setContentsMargins(18, 8, 10, 8)
    net_layout.setSpacing(6)
    net_toolbar, net_toolbar_layout = _make_container(ui.page_net, "network_toolbar", QHBoxLayout)
    net_toolbar_layout.addStretch(1)
    _set_fixed_size(ui.pushButton_check_net, 120, 40)
    net_toolbar_layout.addWidget(ui.pushButton_check_net)
    net_layout.addWidget(net_toolbar)
    net_layout.addWidget(ui.textBrowser_net_main, 1)

    tool_layout = QVBoxLayout(ui.page_tool)
    tool_layout.setContentsMargins(10, 0, 8, 4)
    tool_layout.addWidget(ui.scrollArea_10)
    _setup_tool_scroll_area(window)

    settings_layout = QVBoxLayout(ui.page_setting)
    settings_layout.setContentsMargins(18, 8, 10, 8)
    settings_layout.setSpacing(6)
    settings_layout.addWidget(ui.tabWidget, 1)
    _setup_settings_scroll_areas(window)
    ui.label_config.setMinimumHeight(74)
    ui.label_config.setMaximumHeight(74)
    settings_footer_layout = QHBoxLayout(ui.label_config)
    settings_footer_layout.setContentsMargins(12, 8, 12, 8)
    settings_footer_layout.setSpacing(10)
    _set_fixed_size(ui.comboBox_change_config, 151, 30)
    _set_fixed_size(ui.pushButton_save_new_config, 91, 40)
    _set_fixed_size(ui.pushButton_init_config, 91, 40)
    _set_fixed_size(ui.pushButton_save_config, 200, 50)
    settings_footer_layout.addWidget(ui.label_241)
    settings_footer_layout.addWidget(ui.comboBox_change_config)
    settings_footer_layout.addWidget(ui.pushButton_save_new_config)
    settings_footer_layout.addWidget(ui.pushButton_init_config)
    settings_footer_layout.addStretch(1)
    settings_footer_layout.addWidget(ui.pushButton_save_config)
    settings_layout.addWidget(ui.label_config)
    window._settings_page_layout_ready = True

    about_layout = QVBoxLayout(ui.page_about)
    about_layout.setContentsMargins(18, 8, 10, 8)
    ui.textBrowser_about.setFont(ui.textBrowser_log_main.font())
    about_layout.addWidget(ui.textBrowser_about)

    window._simple_page_layouts_ready = True


def setup_responsive_ui(window: "MyMAinWindow") -> None:
    window.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    window.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    tree = window.Ui.treeWidget_number
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.setSizeAdjustPolicy(tree.SizeAdjustPolicy.AdjustIgnored)

    required_main_widgets = (
        "pushButton_load_nfo",
        "label_number",
        "label_poster",
        "treeWidget_number",
    )
    if all(hasattr(window.Ui, name) for name in required_main_widgets) and hasattr(window, "result_sort_combo"):
        _setup_shell_splitter(window)
        _setup_main_page_layout(window)
        _setup_simple_page_layouts(window)
        _setup_overlay_layouts(window)

    if not hasattr(window, "_resize_grip"):
        window._resize_grip = QSizeGrip(window.Ui.centralwidget)
        window._resize_grip.setObjectName("main_window_resize_grip")
        window._resize_grip.setToolTip("拖动调整窗口大小")
        window._resize_grip.raise_()

    apply_responsive_layout(window)


def apply_responsive_layout(window: "MyMAinWindow") -> None:
    central = window.Ui.centralwidget
    metrics = calculate_layout_metrics(central.width(), central.height())
    ui = window.Ui

    if hasattr(window, "_shell_splitter"):
        _set_geometry(window._shell_splitter, 0, 0, central.width(), central.height())
        _sync_shell_sidebar(window)
    else:
        _set_geometry(
            ui.stackedWidget,
            STACKED_LEFT,
            STACKED_TOP,
            metrics.stacked_width,
            metrics.stacked_height,
        )
        _set_geometry(ui.widget_setting, 0, 0, STACKED_LEFT, metrics.window_height)
        _set_geometry(ui.left_backgroud_widget, 0, 0, STACKED_LEFT, metrics.window_height)
        _set_geometry(ui.label_show_version, 0, 489 + metrics.height_delta, STACKED_LEFT, 201)
        _set_geometry(ui.label_local_number, 0, 680 + metrics.height_delta, 21, 21)
        _set_geometry(ui.progressBar_scrape, 209, -1, metrics.stacked_width + 3, 7)

    if not hasattr(window, "_main_splitter"):
        _set_geometry(ui.label_file_path, 30, 10, metrics.path_width, 50)
        _set_geometry(ui.line_14, 30, 60, metrics.line_width, 20)
        _set_geometry(ui.pushButton_select_media_folder, 565 + metrics.width_delta, 13, 101, 40)
        _set_geometry(ui.pushButton_start_cap, 680 + metrics.width_delta, 13, 120, 40)
        _set_geometry(ui.label_result, metrics.result_x, 70, metrics.result_width, 40)
        _set_geometry(ui.treeWidget_number, metrics.result_x, 140, metrics.result_width, metrics.result_height)
        _set_geometry(ui.pushButton_tree_clear, metrics.stacked_width - 60, 110, 20, 20)

        result_sort_combo = getattr(window, "result_sort_combo", None)
        if result_sort_combo is not None:
            _set_geometry(result_sort_combo, metrics.result_x, 110, 130, 26)
        result_sort_order_button = getattr(window, "result_sort_order_button", None)
        if result_sort_order_button is not None:
            _set_geometry(result_sort_order_button, metrics.result_x + 134, 110, 34, 26)

    if not hasattr(window, "_simple_page_layouts_ready"):
        _set_geometry(ui.textBrowser_log_main, 28, 0, metrics.viewport_width, 421)
        _set_geometry(
            ui.textBrowser_log_main_2,
            28,
            421,
            metrics.viewport_width,
            271 + metrics.height_delta,
        )
        _set_geometry(ui.pushButton_start_cap2, 680 + metrics.width_delta, 13, 120, 40)
        _set_geometry(ui.textBrowser_net_main, 30, 0, metrics.viewport_width, metrics.viewport_height)
        _set_geometry(ui.pushButton_check_net, 680 + metrics.width_delta, 13, 120, 40)
        _set_geometry(ui.scrollArea_10, 20, 0, metrics.stacked_width - 24, metrics.stacked_height - 3)
        _set_geometry(ui.textBrowser_about, 30, 0, metrics.viewport_width, metrics.stacked_height - 3)

    _set_geometry(ui.textBrowser_log_main_3, 0, 0, metrics.stacked_width - 130, metrics.stacked_height)
    if hasattr(ui, "pushButton_scraper_failed_list"):
        _set_geometry(ui.pushButton_scraper_failed_list, 20, 13, metrics.stacked_width - 289, 40)
    if hasattr(ui, "pushButton_save_failed_list"):
        _set_geometry(ui.pushButton_save_failed_list, 0, metrics.stacked_height - 42, 40, 40)
    if not hasattr(window, "_settings_page_layout_ready"):
        _set_geometry(ui.tabWidget, 20, 10, metrics.stacked_width - 18, metrics.stacked_height - 8)
    else:
        _sync_settings_scroll_areas(window)

    _sync_main_image_sizes(window)
    _sync_tool_scroll_area(window)
    _sync_overlay_widgets(window)
    _schedule_content_pane_sync(window)

    grip = window._resize_grip
    grip_size = grip.sizeHint()
    grip.resize(grip_size)
    grip.move(max(0, central.width() - grip.width()), max(0, central.height() - grip.height()))
    grip.raise_()
