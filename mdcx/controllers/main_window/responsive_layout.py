from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QSizeGrip,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

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
    field_layout.addWidget(value)
    field_layout.addWidget(line)
    caption.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
    value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout.addWidget(caption, row, column)
    layout.addWidget(field, row, column + 1)


def _setup_shell_splitter(window: "MyMAinWindow") -> None:
    if hasattr(window, "_shell_splitter"):
        return

    ui = window.Ui
    splitter = QSplitter(Qt.Orientation.Horizontal, ui.centralwidget)
    splitter.setObjectName("window_shell_splitter")
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(5)
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
    window._shell_splitter = splitter


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

    summary_panel, summary_layout = _make_container(window._main_detail_pane, "main_summary_panel", QGridLayout)
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
    image_row.setMinimumHeight(220)
    image_row.setMaximumHeight(320)
    image_layout.setColumnStretch(1, 1)
    image_layout.setColumnStretch(2, 2)
    image_layout.addWidget(ui.label_poster1, 0, 0, Qt.AlignmentFlag.AlignTop)
    for image_label, stretch, minimum_width in (
        (ui.label_poster, 1, 100),
        (ui.label_thumb, 2, 180),
    ):
        image_label.setMinimumSize(minimum_width, 200)
        image_label.setMaximumHeight(280)
        image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        image_layout.addWidget(image_label, 0, stretch)
    image_layout.addWidget(ui.label_poster_size, 1, 1)
    image_info, image_info_layout = _make_container(image_row, "main_image_info", QHBoxLayout)
    image_info_layout.addWidget(ui.label_thumb_size, 1)
    image_info_layout.addWidget(ui.checkBox_cover)
    image_layout.addWidget(image_info, 1, 2)
    detail_pane_layout.addWidget(image_row)

    detail_panel, detail_layout = _make_container(window._main_detail_pane, "main_text_detail_panel", QGridLayout)
    detail_layout.setColumnStretch(1, 1)
    _add_underlined_field(detail_layout, detail_panel, ui.label_18, ui.label_outline, ui.line_6, 0, 0)
    _add_underlined_field(detail_layout, detail_panel, ui.label_33, ui.label_tag, ui.line_7, 1, 0)
    detail_pane_layout.addWidget(detail_panel)

    metadata_panel, metadata_layout = _make_container(window._main_detail_pane, "main_metadata_panel", QGridLayout)
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
    page_layout.addWidget(splitter, 1)


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
    net_toolbar, net_toolbar_layout = _make_container(ui.page_net, "network_toolbar", QHBoxLayout)
    net_toolbar_layout.addStretch(1)
    net_toolbar_layout.addWidget(ui.pushButton_check_net)
    net_layout.addWidget(net_toolbar)
    net_layout.addWidget(ui.textBrowser_net_main, 1)

    tool_layout = QVBoxLayout(ui.page_tool)
    tool_layout.setContentsMargins(10, 0, 8, 4)
    tool_layout.addWidget(ui.scrollArea_10)

    settings_layout = QVBoxLayout(ui.page_setting)
    settings_layout.setContentsMargins(18, 8, 10, 8)
    settings_layout.setSpacing(6)
    settings_layout.addWidget(ui.tabWidget, 1)
    ui.label_config.setMinimumHeight(74)
    ui.label_config.setMaximumHeight(74)
    settings_footer_layout = QHBoxLayout(ui.label_config)
    settings_footer_layout.setContentsMargins(12, 8, 12, 8)
    settings_footer_layout.setSpacing(10)
    ui.comboBox_change_config.setMinimumWidth(140)
    ui.pushButton_save_new_config.setMinimumWidth(80)
    ui.pushButton_init_config.setMinimumWidth(80)
    ui.pushButton_save_config.setMinimumWidth(160)
    settings_footer_layout.addWidget(ui.label_241)
    settings_footer_layout.addWidget(ui.comboBox_change_config)
    settings_footer_layout.addWidget(ui.pushButton_save_new_config)
    settings_footer_layout.addWidget(ui.pushButton_init_config)
    settings_footer_layout.addStretch(1)
    settings_footer_layout.addWidget(ui.pushButton_save_config)
    settings_layout.addWidget(ui.label_config)
    window._settings_page_layout_ready = True

    about_layout = QVBoxLayout(ui.page_about)
    about_layout.setContentsMargins(18, 0, 10, 4)
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
        sidebar_width = ui.widget_setting.width()
        content_width = max(1, central.width() - sidebar_width)
        _set_geometry(ui.left_backgroud_widget, 0, 0, sidebar_width, central.height())
        _set_geometry(ui.label_show_version, 0, max(0, central.height() - 211), sidebar_width, 201)
        _set_geometry(ui.label_local_number, 0, max(0, central.height() - 21), 21, 21)
        _set_geometry(ui.progressBar_scrape, sidebar_width - 1, -1, content_width + 3, 7)
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

    grip = window._resize_grip
    grip_size = grip.sizeHint()
    grip.resize(grip_size)
    grip.move(max(0, central.width() - grip.width()), max(0, central.height() - grip.height()))
    grip.raise_()
