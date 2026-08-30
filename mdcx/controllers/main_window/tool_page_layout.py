from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QSizePolicy, QVBoxLayout


def _prepare_group(group: QGroupBox) -> None:
    group.setMinimumSize(0, 0)
    group.setMaximumSize(16777215, 16777215)
    group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def _single_file_group(ui: object) -> None:
    group = ui.groupBox_7
    _prepare_group(group)
    layout = QGridLayout(group)
    layout.setContentsMargins(24, 24, 24, 18)
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(12)
    layout.addWidget(ui.label_3, 0, 0)
    layout.addWidget(ui.lineEdit_single_file_path, 0, 1)
    layout.addWidget(ui.pushButton_select_file, 0, 2)
    layout.addWidget(ui.label_10, 1, 0)
    layout.addWidget(ui.lineEdit_appoint_url, 1, 1)
    layout.addWidget(ui.pushButton_select_file_clear_info, 1, 2)
    layout.addWidget(ui.label, 2, 0, 1, 3)
    layout.addWidget(ui.pushButton_start_single_file, 3, 1)
    layout.setColumnStretch(1, 1)


def _missing_number_group(ui: object) -> None:
    group = ui.groupBox_19
    _prepare_group(group)
    layout = QGridLayout(group)
    layout.setContentsMargins(24, 24, 24, 18)
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(12)
    layout.addWidget(ui.gridLayoutWidget_18, 0, 0, 1, 2)
    layout.addWidget(ui.pushButton_select_local_library, 0, 2, alignment=Qt.AlignmentFlag.AlignTop)
    layout.addWidget(ui.label_62, 1, 0, 1, 3)
    layout.addWidget(ui.pushButton_find_missing_number, 2, 1)
    layout.setColumnStretch(1, 1)


def _move_group(ui: object) -> None:
    group = ui.groupBox_6
    _prepare_group(group)
    layout = QGridLayout(group)
    layout.setContentsMargins(24, 24, 24, 18)
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(10)
    layout.addWidget(ui.label_41, 0, 0)
    layout.addWidget(ui.lineEdit_escape_dir_move, 0, 1)
    layout.addWidget(ui.label_8, 1, 0, 1, 2)
    layout.addWidget(ui.pushButton_move_mp4, 2, 1)
    layout.setColumnStretch(1, 1)


def _thumbnail_group(ui: object) -> None:
    group = ui.groupBox_13
    _prepare_group(group)
    layout = QVBoxLayout(group)
    layout.setContentsMargins(24, 24, 24, 18)
    layout.setSpacing(12)
    layout.addWidget(ui.label_6)
    layout.addWidget(ui.pushButton_select_thumb, alignment=Qt.AlignmentFlag.AlignHCenter)


def _netdisk_group(ui: object) -> None:
    group = ui.groupBox_21
    _prepare_group(group)
    layout = QGridLayout(group)
    layout.setContentsMargins(24, 24, 24, 18)
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(10)
    layout.addWidget(ui.gridLayoutWidget_36, 0, 0, 1, 2)
    buttons = QVBoxLayout()
    buttons.addWidget(ui.pushButton_select_netdisk_path)
    buttons.addWidget(ui.pushButton_select_localdisk_path)
    buttons.addStretch(1)
    layout.addLayout(buttons, 0, 2)
    layout.addWidget(ui.label_340, 1, 0, 1, 3)
    layout.addWidget(ui.layoutWidget, 2, 0, 1, 3)
    actions = QHBoxLayout()
    actions.addStretch(1)
    actions.addWidget(ui.pushButton_creat_symlink)
    actions.addWidget(ui.checkBox_create_link)
    actions.addStretch(1)
    layout.addLayout(actions, 3, 0, 1, 3)
    layout.setColumnStretch(1, 1)


def install_tool_page_layout(ui: object) -> None:
    """Replace generated absolute positioning in the tool page with layouts."""

    if ui.groupBox_7.layout() is not None:
        return
    _single_file_group(ui)
    _missing_number_group(ui)
    _move_group(ui)
    _thumbnail_group(ui)
    _netdisk_group(ui)
