from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

CAPTION_WIDTH = 104
FIELD_HEIGHT = 34
SELECT_BUTTON_WIDTH = 92
ACTION_BUTTON_WIDTH = 220
ACTION_BUTTON_HEIGHT = 38


def _prepare_group(group: QGroupBox) -> None:
    group.setMinimumSize(0, 0)
    group.setMaximumSize(16777215, 16777215)
    group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def _prepare_caption(label: QLabel) -> None:
    label.setFixedWidth(CAPTION_WIDTH)
    label.setMinimumHeight(FIELD_HEIGHT)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


def _prepare_field(field: QLineEdit) -> None:
    # Generated controls carry several different inline border/radius rules.
    # The tool page owns their visual style, so remove those legacy overrides.
    field.setStyleSheet("")
    field.setMinimumHeight(FIELD_HEIGHT)
    field.setMaximumHeight(FIELD_HEIGHT)
    field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def _prepare_select_button(button: QPushButton) -> None:
    button.setProperty("toolRole", "secondary")
    button.setFixedSize(SELECT_BUTTON_WIDTH, FIELD_HEIGHT)


def _prepare_help(label: QLabel, *, centered: bool = False) -> None:
    label.setStyleSheet("")
    label.setProperty("toolRole", "help")
    label.setWordWrap(True)
    label.setAlignment(
        (Qt.AlignmentFlag.AlignHCenter if centered else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter
    )


def _add_action_row(layout: QGridLayout, button: QPushButton, row: int, *, trailing=None) -> None:
    button.setProperty("toolRole", "primary")
    button.setFixedSize(ACTION_BUTTON_WIDTH, ACTION_BUTTON_HEIGHT)
    actions = QHBoxLayout()
    actions.setSpacing(12)
    actions.addStretch(1)
    actions.addWidget(button)
    if trailing is not None:
        actions.addWidget(trailing)
    actions.addStretch(1)
    layout.addLayout(actions, row, 0, 1, 3)


def _prepare_form_grid(layout: QGridLayout) -> None:
    layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    layout.setContentsMargins(24, 24, 24, 18)
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(12)
    layout.setColumnMinimumWidth(0, CAPTION_WIDTH)
    layout.setColumnMinimumWidth(2, SELECT_BUTTON_WIDTH)
    layout.setColumnStretch(1, 1)


def _single_file_group(ui: object) -> None:
    group = ui.groupBox_7
    _prepare_group(group)
    layout = QGridLayout(group)
    _prepare_form_grid(layout)
    for label in (ui.label_3, ui.label_10):
        _prepare_caption(label)
    for field in (ui.lineEdit_single_file_path, ui.lineEdit_appoint_url):
        _prepare_field(field)
    for button in (ui.pushButton_select_file, ui.pushButton_select_file_clear_info):
        _prepare_select_button(button)
    _prepare_help(ui.label)
    layout.addWidget(ui.label_3, 0, 0)
    layout.addWidget(ui.lineEdit_single_file_path, 0, 1)
    layout.addWidget(ui.pushButton_select_file, 0, 2)
    layout.addWidget(ui.label_10, 1, 0)
    layout.addWidget(ui.lineEdit_appoint_url, 1, 1)
    layout.addWidget(ui.pushButton_select_file_clear_info, 1, 2)
    layout.addWidget(ui.label, 2, 1, 1, 2)
    _add_action_row(layout, ui.pushButton_start_single_file, 3)


def _missing_number_group(ui: object) -> None:
    group = ui.groupBox_19
    _prepare_group(group)
    layout = QGridLayout(group)
    _prepare_form_grid(layout)
    for label in (ui.label_72, ui.label_53):
        _prepare_caption(label)
    for field in (ui.lineEdit_local_library_path, ui.lineEdit_actors_name):
        _prepare_field(field)
    _prepare_select_button(ui.pushButton_select_local_library)
    _prepare_help(ui.label_62)
    layout.addWidget(ui.label_72, 0, 0)
    layout.addWidget(ui.lineEdit_local_library_path, 0, 1)
    layout.addWidget(ui.pushButton_select_local_library, 0, 2)
    layout.addWidget(ui.label_53, 1, 0)
    layout.addWidget(ui.lineEdit_actors_name, 1, 1)
    layout.addWidget(ui.label_62, 2, 1, 1, 2)
    _add_action_row(layout, ui.pushButton_find_missing_number, 3)
    ui.gridLayoutWidget_18.hide()


def _move_group(ui: object) -> None:
    group = ui.groupBox_6
    _prepare_group(group)
    layout = QGridLayout(group)
    _prepare_form_grid(layout)
    _prepare_caption(ui.label_41)
    _prepare_field(ui.lineEdit_escape_dir_move)
    _prepare_help(ui.label_8)
    layout.addWidget(ui.label_41, 0, 0)
    layout.addWidget(ui.lineEdit_escape_dir_move, 0, 1, 1, 2)
    layout.addWidget(ui.label_8, 1, 1, 1, 2)
    _add_action_row(layout, ui.pushButton_move_mp4, 2)


def _thumbnail_group(ui: object) -> None:
    group = ui.groupBox_13
    _prepare_group(group)
    layout = QVBoxLayout(group)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    layout.setContentsMargins(24, 24, 24, 18)
    layout.setSpacing(12)
    _prepare_help(ui.label_6, centered=True)
    ui.pushButton_select_thumb.setProperty("toolRole", "secondary")
    ui.pushButton_select_thumb.setFixedSize(ACTION_BUTTON_WIDTH, ACTION_BUTTON_HEIGHT)
    layout.addWidget(ui.label_6)
    layout.addWidget(ui.pushButton_select_thumb, alignment=Qt.AlignmentFlag.AlignHCenter)


def _netdisk_group(ui: object) -> None:
    group = ui.groupBox_21
    _prepare_group(group)
    layout = QGridLayout(group)
    _prepare_form_grid(layout)
    for label in (ui.label_339, ui.label_338):
        _prepare_caption(label)
    for field in (ui.lineEdit_netdisk_path, ui.lineEdit_localdisk_path):
        _prepare_field(field)
    for button in (ui.pushButton_select_netdisk_path, ui.pushButton_select_localdisk_path):
        _prepare_select_button(button)
    for label in (ui.label_340, ui.label_341):
        _prepare_help(label)
    layout.addWidget(ui.label_339, 0, 0)
    layout.addWidget(ui.lineEdit_netdisk_path, 0, 1)
    layout.addWidget(ui.pushButton_select_netdisk_path, 0, 2)
    layout.addWidget(ui.label_338, 1, 0)
    layout.addWidget(ui.lineEdit_localdisk_path, 1, 1)
    layout.addWidget(ui.pushButton_select_localdisk_path, 1, 2)
    layout.addWidget(ui.label_340, 2, 1, 1, 2)
    layout.addWidget(ui.checkBox_copy_netdisk_nfo, 3, 1, 1, 2)
    layout.addWidget(ui.label_341, 4, 1, 1, 2)
    _add_action_row(layout, ui.pushButton_creat_symlink, 5, trailing=ui.checkBox_create_link)
    ui.gridLayoutWidget_36.hide()
    ui.layoutWidget.hide()


def install_tool_page_layout(ui: object) -> None:
    """Replace generated absolute positioning in the tool page with layouts."""

    if ui.groupBox_7.layout() is not None:
        return
    _single_file_group(ui)
    _missing_number_group(ui)
    _move_group(ui)
    _thumbnail_group(ui)
    _netdisk_group(ui)
