"""Layout construction for the legacy NFO editor overlay.

The generated Designer view still provides the named controls consumed by the
controller.  This module owns their composition so the editor no longer relies
on a 752x1300 absolute-coordinate canvas.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLayout, QSizePolicy, QVBoxLayout, QWidget


def _prepare_field(widget: QWidget) -> None:
    widget.setMinimumHeight(36)
    widget.setMaximumHeight(40)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def _add_full_width_field(
    layout: QGridLayout,
    row: int,
    label: QWidget,
    field: QWidget,
) -> None:
    layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(field, row, 1, 1, 5)


def setup_nfo_editor_form(ui) -> None:
    """Replace the generated absolute geometry with a scrollable form layout."""
    content = ui.scrollAreaWidgetContents_nfo_editor
    if content.layout() is not None:
        return

    ui.scrollArea_nfo.setWidgetResizable(True)
    root = QVBoxLayout(content)
    root.setContentsMargins(20, 14, 20, 20)
    root.setSpacing(10)
    root.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

    form = QGridLayout()
    form.setHorizontalSpacing(10)
    form.setVerticalSpacing(8)
    form.setColumnStretch(1, 1)
    form.setColumnStretch(3, 1)
    root.addLayout(form)

    for field in (
        ui.lineEdit_nfo_number,
        ui.comboBox_nfo,
        ui.lineEdit_nfo_year,
        ui.lineEdit_nfo_actor,
        ui.lineEdit_nfo_title,
        ui.lineEdit_nfo_originaltitle,
        ui.lineEdit_nfo_release,
        ui.lineEdit_nfo_runtime,
        ui.lineEdit_nfo_score,
        ui.lineEdit_nfo_wanted,
        ui.lineEdit_nfo_director,
        ui.lineEdit_nfo_series,
        ui.lineEdit_nfo_studio,
        ui.lineEdit_nfo_publisher,
        ui.lineEdit_nfo_poster,
        ui.lineEdit_nfo_cover,
        ui.lineEdit_nfo_trailer,
        ui.lineEdit_nfo_website,
    ):
        _prepare_field(field)

    form.addWidget(ui.label_381, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.addWidget(ui.label_nfo, 0, 1, 1, 5)

    form.addWidget(ui.label_360, 1, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.addWidget(ui.lineEdit_nfo_number, 1, 1)
    form.addWidget(ui.label_369, 1, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.addWidget(ui.comboBox_nfo, 1, 3)
    form.addWidget(ui.label_380, 1, 4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.addWidget(ui.lineEdit_nfo_year, 1, 5)
    form.setColumnStretch(5, 1)

    _add_full_width_field(form, 2, ui.label_359, ui.lineEdit_nfo_actor)
    form.addWidget(ui.label_370, 3, 1, 1, 5)
    _add_full_width_field(form, 4, ui.label_361, ui.lineEdit_nfo_title)
    _add_full_width_field(form, 5, ui.label_372, ui.lineEdit_nfo_originaltitle)

    for text_edit in (ui.textEdit_nfo_outline, ui.textEdit_nfo_originalplot):
        text_edit.setMinimumHeight(110)
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    form.addWidget(ui.label_19, 6, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
    form.addWidget(ui.textEdit_nfo_outline, 6, 1, 1, 5)
    form.addWidget(ui.label_371, 7, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
    form.addWidget(ui.textEdit_nfo_originalplot, 7, 1, 1, 5)

    ui.textEdit_nfo_tag.setMinimumHeight(90)
    ui.textEdit_nfo_tag.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    form.addWidget(ui.label_362, 8, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
    form.addWidget(ui.textEdit_nfo_tag, 8, 1, 1, 5)
    form.addWidget(ui.label_379, 9, 1, 1, 5)

    detail_fields = (
        (ui.label_363, ui.lineEdit_nfo_release, ui.label_364, ui.lineEdit_nfo_runtime),
        (ui.label_373, ui.lineEdit_nfo_score, ui.label_374, ui.lineEdit_nfo_wanted),
        (ui.label_366, ui.lineEdit_nfo_director, ui.label_365, ui.lineEdit_nfo_series),
        (ui.label_368, ui.lineEdit_nfo_studio, ui.label_367, ui.lineEdit_nfo_publisher),
    )
    for row, (left_label, left_field, right_label, right_field) in enumerate(detail_fields, start=10):
        form.addWidget(left_label, row, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(left_field, row, 1, 1, 2)
        form.addWidget(right_label, row, 3, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(right_field, row, 4, 1, 2)

    for row, label, field in (
        (14, ui.label_375, ui.lineEdit_nfo_poster),
        (15, ui.label_376, ui.lineEdit_nfo_cover),
        (16, ui.label_377, ui.lineEdit_nfo_trailer),
        (17, ui.label_378, ui.lineEdit_nfo_website),
    ):
        form.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(field, row, 1, 1, 5)

    root.addStretch(1)
