"""Self-contained result pane used by the main page."""

from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

RESULT_PANE_MIN_WIDTH = 252


def _row(parent: QWidget, object_name: str) -> tuple[QWidget, QHBoxLayout]:
    widget = QWidget(parent)
    widget.setObjectName(object_name)
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    return widget, layout


class ResultPanel(QWidget):
    """Compose result count, compact controls and the model/view result tree."""

    def __init__(
        self,
        result_label,
        filter_edit,
        status_combo,
        sort_combo,
        sort_order_button,
        clear_button,
        result_tree,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("main_result_pane")
        self.setMinimumWidth(RESULT_PANE_MIN_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(result_label)

        self.toolbar = QWidget(self)
        self.toolbar.setObjectName("main_result_toolbar")
        toolbar_layout = QVBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(4)

        self.search_row, search_layout = _row(self.toolbar, "main_result_search_row")
        filter_edit.setMinimumWidth(100)
        filter_edit.setFixedHeight(28)
        clear_button.setFixedSize(28, 28)
        search_layout.addWidget(filter_edit, 1)
        search_layout.addWidget(clear_button)
        toolbar_layout.addWidget(self.search_row)

        self.sort_row, sort_layout = _row(self.toolbar, "main_result_sort_row")
        status_combo.setFixedSize(88, 28)
        sort_combo.setMinimumSize(116, 28)
        sort_combo.setMaximumSize(148, 28)
        sort_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sort_order_button.setFixedSize(32, 28)
        sort_layout.addWidget(status_combo)
        sort_layout.addWidget(sort_combo, 1)
        sort_layout.addWidget(sort_order_button)
        toolbar_layout.addWidget(self.sort_row)

        layout.addWidget(self.toolbar)
        result_tree.setMinimumWidth(RESULT_PANE_MIN_WIDTH)
        layout.addWidget(result_tree, 1)
