from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QLabel, QWidget

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


def _find_widget(window: MyMAinWindow, name: str) -> QWidget | None:
    """Resolve generated UI controls and controls created by controllers."""

    widget = getattr(window.Ui, name, None)
    if not isinstance(widget, QWidget):
        widget = getattr(window, name, None)
    return widget if isinstance(widget, QWidget) else None


def _existing_widgets(window: MyMAinWindow, names: Iterable[str]) -> list[QWidget]:
    return [widget for name in names if (widget := _find_widget(window, name)) is not None]


def _set_tab_sequence(window: MyMAinWindow, names: Iterable[str]) -> None:
    widgets = _existing_widgets(window, names)
    for current, following in zip(widgets, widgets[1:], strict=False):
        QWidget.setTabOrder(current, following)


def install_accessibility(window: MyMAinWindow) -> None:
    """Install stable names, label buddies and keyboard order for primary workflows."""

    ui = window.Ui
    accessible_names = {
        "pushButton_select_media_folder": "选择待刮削目录",
        "pushButton_start_cap": "开始或停止刮削",
        "pushButton_load_nfo": "加载本地 NFO",
        "pushButton_open_nfo": "编辑所选项目 NFO",
        "pushButton_open_folder": "打开所选项目文件夹",
        "pushButton_play": "播放所选媒体",
        "treeWidget_number": "刮削结果列表",
        "result_filter_edit": "搜索刮削结果",
        "result_status_combo": "筛选刮削结果状态",
        "result_sort_combo": "选择刮削结果排序",
        "result_sort_order_button": "切换升序或降序",
        "lineEdit_single_file_path": "单文件路径",
        "lineEdit_appoint_url": "单文件指定网址",
        "pushButton_start_single_file": "开始单文件刮削",
        "lineEdit_settings_search": "搜索设置",
        "toolButton_advanced_settings": "显示或隐藏高级设置",
    }
    for name, accessible_name in accessible_names.items():
        widget = _find_widget(window, name)
        if widget is not None:
            widget.setAccessibleName(accessible_name)

    buddy_pairs = {
        "label_3": "lineEdit_single_file_path",
        "label_10": "lineEdit_appoint_url",
        "label_41": "lineEdit_escape_dir_move",
        "label_72": "lineEdit_local_library_path",
        "label_53": "lineEdit_actors_name",
        "label_339": "lineEdit_netdisk_path",
        "label_338": "lineEdit_localdisk_path",
    }
    for label_name, field_name in buddy_pairs.items():
        label = getattr(ui, label_name, None)
        field = _find_widget(window, field_name)
        if isinstance(label, QLabel) and isinstance(field, QWidget):
            label.setBuddy(field)

    _set_tab_sequence(
        window,
        (
            "pushButton_select_media_folder",
            "pushButton_start_cap",
            "pushButton_load_nfo",
            "pushButton_open_nfo",
            "pushButton_open_folder",
            "pushButton_play",
            "result_filter_edit",
            "result_status_combo",
            "result_sort_combo",
            "result_sort_order_button",
            "treeWidget_number",
        ),
    )
    _set_tab_sequence(
        window,
        (
            "lineEdit_single_file_path",
            "pushButton_select_file",
            "lineEdit_appoint_url",
            "pushButton_select_file_clear_info",
            "pushButton_start_single_file",
            "lineEdit_local_library_path",
            "lineEdit_actors_name",
            "pushButton_find_missing_number",
            "lineEdit_escape_dir_move",
            "pushButton_move_mp4",
            "pushButton_select_thumb",
            "lineEdit_netdisk_path",
            "lineEdit_localdisk_path",
            "pushButton_creat_symlink",
        ),
    )
    _set_tab_sequence(window, ("lineEdit_settings_search", "toolButton_advanced_settings", "tabWidget"))
