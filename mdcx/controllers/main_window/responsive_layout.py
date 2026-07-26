from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QHeaderView, QSizeGrip, QSizePolicy

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


def setup_responsive_ui(window: "MyMAinWindow") -> None:
    window.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    window.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    tree = window.Ui.treeWidget_number
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.setSizeAdjustPolicy(tree.SizeAdjustPolicy.AdjustIgnored)

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
    _set_geometry(ui.tabWidget, 20, 10, metrics.stacked_width - 18, metrics.stacked_height - 8)
    _set_geometry(ui.textBrowser_about, 30, 0, metrics.viewport_width, metrics.stacked_height - 3)

    grip = window._resize_grip
    grip_size = grip.sizeHint()
    grip.resize(grip_size)
    grip.move(max(0, central.width() - grip.width()), max(0, central.height() - grip.height()))
    grip.raise_()
