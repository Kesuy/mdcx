from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, QPoint, Qt
from PyQt6.QtGui import QKeyEvent
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
    assert view.itemFromIndex(view.indexFromItem(entry)) is entry

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


def test_adding_and_reordering_results_keeps_selection_and_roots_expanded() -> None:
    _app()
    view = ResultTreeView()
    success = create_result_item(view)
    assert isinstance(success, ResultTreeItem)
    success.setText(0, "成功")
    first = create_result_item(success)
    second = create_result_item(success)
    assert isinstance(first, ResultTreeItem)
    assert isinstance(second, ResultTreeItem)
    first.setText(0, "first")
    second.setText(0, "second")
    first.setSelected(True)
    view.setCurrentItem(first)

    third = create_result_item(success)
    assert isinstance(third, ResultTreeItem)
    third.setText(0, "third")

    assert view.isExpanded(view.indexFromItem(success))
    assert view.selectedItems() == [first]

    success.reorderChildren([third, second, first])

    assert view.isExpanded(view.indexFromItem(success))
    assert view.selectedItems() == [first]
    assert success.child(0) is third


def test_result_item_factory_keeps_lightweight_qtreewidget_harnesses_compatible() -> None:
    _app()
    tree = QTreeWidget()
    root = create_result_item(tree)
    child = create_result_item(root)

    assert isinstance(root, QTreeWidgetItem)
    assert isinstance(child, QTreeWidgetItem)
    assert root.child(0) is child


def test_ctrl_a_selects_only_current_result_category() -> None:
    _app()
    view = ResultTreeView()
    view.setSelectionMode(view.SelectionMode.ExtendedSelection)
    success = create_result_item(view)
    failure = create_result_item(view)
    assert isinstance(success, ResultTreeItem)
    assert isinstance(failure, ResultTreeItem)
    success.setText(0, "成功")
    failure.setText(0, "失败")
    success_items = [create_result_item(success), create_result_item(success)]
    failure_items = [create_result_item(failure), create_result_item(failure)]
    assert all(isinstance(item, ResultTreeItem) for item in success_items + failure_items)

    view.setCurrentItem(success_items[0])
    view.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier))
    assert set(view.selectedItems()) == set(success_items)

    view.clearSelection()
    view.setCurrentItem(failure_items[0])
    view.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier))
    assert set(view.selectedItems()) == set(failure_items)
