from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

from mdcx.controllers.main_window.result_model import ResultTreeItem, ResultTreeView, create_result_item


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_result_tree_model_supports_hierarchy_filter_and_selection() -> None:
    _app()
    view = ResultTreeView()
    success = create_result_item(view)
    assert isinstance(success, ResultTreeItem)
    success.setText(0, "成功")
    entry = create_result_item(success)
    assert isinstance(entry, ResultTreeItem)
    entry.setText(0, "ABC-123")
    entry.setData(0, Qt.ItemDataRole.UserRole, 7)

    assert view.topLevelItemCount() == 1
    assert success.childCount() == 1
    assert entry.data(0, Qt.ItemDataRole.UserRole) == 7
    assert view.proxy_model.rowCount() == 1

    view.expandAll()
    entry.setSelected(True)
    assert view.selectedItems() == [entry]

    entry.setHidden(True)
    assert view.proxy_model.rowCount(view.proxy_model.index(0, 0)) == 0
    entry.setHidden(False)
    assert view.proxy_model.rowCount(view.proxy_model.index(0, 0)) == 1


def test_result_tree_view_replaces_designer_widget() -> None:
    _app()
    old = QTreeWidget()
    old.setObjectName("treeWidget_number")
    old.setGeometry(10, 20, 300, 400)

    view = ResultTreeView.replace(old)

    assert view.objectName() == "treeWidget_number"
    assert view.geometry() == old.geometry()
    assert view.itemAt(QPoint(-1, -1)) is None


def test_result_item_factory_keeps_lightweight_qtreewidget_harnesses_compatible() -> None:
    _app()
    tree = QTreeWidget()
    root = create_result_item(tree)
    child = create_result_item(root)

    assert isinstance(root, QTreeWidgetItem)
    assert isinstance(child, QTreeWidgetItem)
    assert root.child(0) is child
