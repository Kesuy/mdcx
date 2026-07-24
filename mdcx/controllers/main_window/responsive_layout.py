from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QFrame, QHeaderView, QSizeGrip, QSizePolicy

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
RESULT_LEFT_DEFAULT = 590
RESULT_RIGHT_MARGIN = 10

# 按钮行布局常量 - 避免与标题重叠
TITLE_MAX_WIDTH = 290  # label_title 最大宽度, 避免与右侧按钮重叠
SORT_COMBO_WIDTH = 120  # 排序下拉框宽度, 确保"完成顺序"完整显示
SORT_ORDER_BTN_WIDTH = 34

# 可拖拽分割条常量
SPLITTER_WIDTH = 4
SPLITTER_MIN_DETAIL = 400  # 详情区最小宽度
SPLITTER_MIN_TREE = 160  # 结果树最小宽度


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
        result_x=RESULT_LEFT_DEFAULT,
        result_width=max(160, stacked_width - RESULT_LEFT_DEFAULT - RESULT_RIGHT_MARGIN),
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
    
    # 使用分割条位置（如果存在）
    if hasattr(window, "_splitter_x"):
        from dataclasses import replace
        metrics = replace(
            metrics,
            result_x=window._splitter_x,
            result_width=max(160, metrics.stacked_width - window._splitter_x - RESULT_RIGHT_MARGIN),
        )
    
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

    # 修复: label_title 宽度限制, 避免与右侧按钮重叠
    title_width = min(TITLE_MAX_WIDTH, metrics.result_x - 90)  # 留出按钮空间
    _set_geometry(ui.label_title, 80, 110, title_width, 40)

    _set_geometry(ui.label_file_path, 30, 10, metrics.path_width, 50)
    _set_geometry(ui.line_14, 30, 60, metrics.line_width, 20)
    _set_geometry(ui.pushButton_select_media_folder, 565 + metrics.width_delta, 13, 101, 40)
    _set_geometry(ui.pushButton_start_cap, 680 + metrics.width_delta, 13, 120, 40)
    _set_geometry(ui.label_result, metrics.result_x, 70, metrics.result_width, 40)
    _set_geometry(ui.treeWidget_number, metrics.result_x, 140, metrics.result_width, metrics.result_height)
    _set_geometry(ui.pushButton_tree_clear, metrics.stacked_width - 60, 110, 20, 20)

    # 修复: 排序下拉框加宽, 确保"完成顺序"完整显示
    result_sort_combo = getattr(window, "result_sort_combo", None)
    if result_sort_combo is not None:
        _set_geometry(result_sort_combo, metrics.result_x, 110, SORT_COMBO_WIDTH, 26)
    result_sort_order_button = getattr(window, "result_sort_order_button", None)
    if result_sort_order_button is not None:
        _set_geometry(result_sort_order_button, metrics.result_x + SORT_COMBO_WIDTH + 4, 110, SORT_ORDER_BTN_WIDTH, 26)

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
    
    # 更新分割条位置
    if hasattr(window, "_main_splitter_bar"):
        splitter_x = metrics.result_x
        splitter_y = 10
        splitter_h = metrics.stacked_height - 20
        window._main_splitter_bar.setGeometry(
            splitter_x - SPLITTER_WIDTH // 2, splitter_y, SPLITTER_WIDTH, splitter_h
        )


def setup_main_splitter(window: "MyMAinWindow") -> None:
    """
    在详情区和结果树之间添加可拖拽的分割条。
    用户可以拖拽分割条来调整左右两部分的宽度比例。
    """
    if hasattr(window, "_main_splitter_bar"):
        return

    ui = window.Ui
    page = ui.page_main

    # 创建分割条 (垂直条)
    splitter_bar = QFrame(page)
    splitter_bar.setObjectName("main_splitter_bar")
    splitter_bar.setFrameShape(QFrame.Shape.VLine)
    splitter_bar.setFrameShadow(QFrame.Shadow.Raised)
    splitter_bar.setLineWidth(SPLITTER_WIDTH)
    splitter_bar.setCursor(QCursor(Qt.CursorShape.SplitHCursor))
    splitter_bar.setToolTip("拖拽调整宽度")

    # 存储拖拽状态
    window._main_splitter_bar = splitter_bar
    window._splitter_dragging = False
    window._splitter_drag_start_x = 0
    window._splitter_x = RESULT_LEFT_DEFAULT

    # 鼠标事件处理
    def on_mouse_press(event):
        if event.button() == Qt.MouseButton.LeftButton:
            window._splitter_dragging = True
            window._splitter_drag_start_x = event.pos().x()

    def on_mouse_release(event):
        window._splitter_dragging = False

    def on_mouse_move(event):
        if window._splitter_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.pos().x() - window._splitter_drag_start_x
            new_x = window._splitter_x + delta

            # 限制范围
            min_x = SPLITTER_MIN_DETAIL + 30
            max_x = page.width() - SPLITTER_MIN_TREE - RESULT_RIGHT_MARGIN
            window._splitter_x = max(min_x, min(max_x, new_x))

            # 更新布局
            apply_responsive_layout(window)

    splitter_bar.mousePressEvent = on_mouse_press
    splitter_bar.mouseReleaseEvent = on_mouse_release
    splitter_bar.mouseMoveEvent = on_mouse_move

    # 初始位置
    splitter_x = RESULT_LEFT_DEFAULT
    splitter_y = 10
    splitter_h = page.height() - 20
    splitter_bar.setGeometry(splitter_x - SPLITTER_WIDTH // 2, splitter_y, SPLITTER_WIDTH, splitter_h)
    splitter_bar.show()
