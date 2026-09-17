from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLayout, QSizePolicy, QWidget

_ALIGNMENT = Qt.AlignmentFlag.AlignVCenter


def _is_multiline_label(widget: QWidget) -> bool:
    if not isinstance(widget, QLabel):
        return False
    text = widget.text().lower()
    return widget.wordWrap() or "\n" in text or "<br" in text


def _prepare_multiline_help_label(widget: QLabel) -> None:
    """Let help text grow vertically instead of clipping at narrower widths."""

    if widget.property("semanticRole") != "help" or not _is_multiline_label(widget):
        return
    widget.setWordWrap(True)
    policy = widget.sizePolicy()
    if policy.verticalPolicy() != QSizePolicy.Policy.Preferred:
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        widget.setSizePolicy(policy)
    widget.setMaximumHeight(16777215)
    widget.updateGeometry()


def _align_item(parent_layout: QLayout, item) -> None:
    widget = item.widget()
    if widget is not None:
        if not _is_multiline_label(widget):
            parent_layout.setAlignment(widget, _ALIGNMENT)
        return

    child_layout = item.layout()
    if child_layout is None:
        return

    parent_layout.setAlignment(child_layout, _ALIGNMENT)
    for index in range(child_layout.count()):
        _align_item(child_layout, child_layout.itemAt(index))


def polish_settings_layout(ui: object) -> None:
    """Vertically center compact controls across every settings form row.

    Qt Designer generated several rows where 18/23/26 px labels and controls
    were top-aligned inside a 30 px grid row. That creates the 2-6 px baseline
    drift visible on Windows. Keep wrapped help text untouched, but center all
    compact widgets and nested horizontal layouts inside their existing cells.
    """

    tab_widget = getattr(ui, "tabWidget", None)
    if tab_widget is None:
        return

    for label in tab_widget.findChildren(QLabel):
        _prepare_multiline_help_label(label)

    for grid in tab_widget.findChildren(QGridLayout):
        for index in range(grid.count()):
            row, _column, row_span, _column_span = grid.getItemPosition(index)
            if row_span != 1:
                continue
            item = grid.itemAt(index)
            _align_item(grid, item)
            grid.setRowMinimumHeight(row, max(grid.rowMinimumHeight(row), 30))

    for horizontal in tab_widget.findChildren(QHBoxLayout):
        for index in range(horizontal.count()):
            _align_item(horizontal, horizontal.itemAt(index))
