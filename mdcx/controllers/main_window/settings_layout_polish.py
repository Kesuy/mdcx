from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLayout, QSizePolicy, QWidget

_ALIGNMENT = Qt.AlignmentFlag.AlignVCenter
_HELP_BASE_HEIGHT_PROPERTY = "mdcx_help_base_minimum_height"


def _is_multiline_label(widget: QWidget) -> bool:
    if not isinstance(widget, QLabel):
        return False
    text = widget.text().lower()
    return widget.wordWrap() or "\n" in text or "<br" in text


def _activate_layout_chain(widget: QWidget) -> None:
    """Recalculate containing layouts after dynamic settings widgets are inserted."""
    current = widget
    while current is not None:
        layout = current.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()
        current = current.parentWidget()


def _prepare_multiline_help_label(widget: QLabel) -> None:
    """Keep help labels responsive without overriding Qt layout geometry."""
    if widget.property("semanticRole") != "help" or not _is_multiline_label(widget):
        return

    widget.setWordWrap(True)

    policy = widget.sizePolicy()
    if policy.verticalPolicy() != QSizePolicy.Policy.Preferred:
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        widget.setSizePolicy(policy)

    if widget.property(_HELP_BASE_HEIGHT_PROPERTY) is None:
        widget.setProperty(_HELP_BASE_HEIGHT_PROPERTY, widget.minimumHeight())

    base_height = widget.property(_HELP_BASE_HEIGHT_PROPERTY)
    if isinstance(base_height, int):
        widget.setMinimumHeight(base_height)

    widget.setMaximumHeight(16777215)
    widget.updateGeometry()

    # Dynamic settings components can move labels between layouts. Activate the
    # actual parent chain instead of forcing QLabel geometry with resize/minHeight.
    _activate_layout_chain(widget)


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
    """Polish settings alignment without changing Designer row geometry."""
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
            _align_item(grid, grid.itemAt(index))

    for horizontal in tab_widget.findChildren(QHBoxLayout):
        for index in range(horizontal.count()):
            _align_item(horizontal, horizontal.itemAt(index))
