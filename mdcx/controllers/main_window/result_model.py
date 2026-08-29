from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PyQt6.QtCore import (
    QAbstractItemModel,
    QItemSelectionModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PyQt6.QtWidgets import QAbstractItemView, QTreeView, QTreeWidget, QTreeWidgetItem

_INVALID_INDEX = QModelIndex()


def _role_value(role: int | Qt.ItemDataRole) -> int:
    return role.value if isinstance(role, Qt.ItemDataRole) else int(role)


class ResultTreeItem:
    """Small tree node used by the result model and its legacy-compatible API."""

    def __init__(self, parent: ResultTreeItem | ResultTreeView | None = None):
        self._parent: ResultTreeItem | None = None
        self._children: list[ResultTreeItem] = []
        self._texts: dict[int, str] = {}
        self._data: dict[tuple[int, int], Any] = {}
        self._hidden = False
        self._model: ResultTreeModel | None = None
        self._view: ResultTreeView | None = None
        if isinstance(parent, ResultTreeItem):
            parent.addChild(self)
        elif isinstance(parent, ResultTreeView):
            parent.addTopLevelItem(self)

    def _attach(self, model: ResultTreeModel | None, view: ResultTreeView | None) -> None:
        self._model = model
        self._view = view
        for child in self._children:
            child._attach(model, view)

    def _refresh(self) -> None:
        if self._model is not None:
            self._model.refresh()

    def text(self, column: int) -> str:
        return self._texts.get(column, "")

    def setText(self, column: int, text: str) -> None:
        self._texts[column] = str(text)
        if self._model is not None:
            self._model.notify_item_changed(self)

    def data(self, column: int, role: int | Qt.ItemDataRole) -> Any:
        return self._data.get((column, _role_value(role)))

    def setData(self, column: int, role: int | Qt.ItemDataRole, value: Any) -> None:
        self._data[(column, _role_value(role))] = value
        if self._model is not None:
            self._model.notify_item_changed(self)

    def parent(self) -> ResultTreeItem | None:
        return self._parent

    def child(self, index: int) -> ResultTreeItem:
        return self._children[index]

    def childCount(self) -> int:
        return len(self._children)

    def indexOfChild(self, child: ResultTreeItem) -> int:
        try:
            return self._children.index(child)
        except ValueError:
            return -1

    def addChild(self, child: ResultTreeItem) -> None:
        if child._parent is self and child in self._children:
            return
        if child._parent is not None:
            child._parent.removeChild(child)
        child._parent = self
        self._children.append(child)
        child._attach(self._model, self._view)
        self._refresh()

    def addChildren(self, children: Iterable[ResultTreeItem]) -> None:
        for child in children:
            if child._parent is not None and child._parent is not self:
                child._parent.removeChild(child)
            child._parent = self
            child._attach(self._model, self._view)
            self._children.append(child)
        self._refresh()

    def takeChild(self, index: int) -> ResultTreeItem:
        child = self._children.pop(index)
        child._parent = None
        self._refresh()
        return child

    def takeChildren(self) -> list[ResultTreeItem]:
        children = self._children
        self._children = []
        for child in children:
            child._parent = None
        self._refresh()
        return children

    def removeChild(self, child: ResultTreeItem) -> None:
        index = self.indexOfChild(child)
        if index >= 0:
            self.takeChild(index)

    def setHidden(self, hidden: bool) -> None:
        hidden = bool(hidden)
        if self._hidden == hidden:
            return
        self._hidden = hidden
        if self._view is not None:
            self._view.proxy_model.invalidateFilter()

    def isHidden(self) -> bool:
        return self._hidden

    def setSelected(self, selected: bool) -> None:
        if self._view is not None:
            self._view.setItemSelected(self, selected)


class ResultTreeModel(QAbstractItemModel):
    def __init__(self, view: ResultTreeView):
        super().__init__(view)
        self.view = view
        self.root = ResultTreeItem()
        self.root._attach(self, view)

    def rowCount(self, parent: QModelIndex = _INVALID_INDEX) -> int:
        item = self.item_from_index(parent)
        return item.childCount()

    def columnCount(self, parent: QModelIndex = _INVALID_INDEX) -> int:
        del parent
        return 1

    def index(self, row: int, column: int, parent: QModelIndex = _INVALID_INDEX) -> QModelIndex:
        parent_item = self.item_from_index(parent)
        if row < 0 or row >= parent_item.childCount() or column != 0:
            return QModelIndex()
        return self.createIndex(row, column, parent_item.child(row))

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        item = index.internalPointer()
        if not isinstance(item, ResultTreeItem):
            return QModelIndex()
        parent_item = item.parent()
        if parent_item is None or parent_item is self.root:
            return QModelIndex()
        grandparent = parent_item.parent() or self.root
        row = grandparent.indexOfChild(parent_item)
        return self.createIndex(row, 0, parent_item) if row >= 0 else QModelIndex()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        item = index.internalPointer()
        if not isinstance(item, ResultTreeItem):
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return item.text(index.column())
        return item.data(index.column(), role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def item_from_index(self, index: QModelIndex) -> ResultTreeItem:
        if not index.isValid():
            return self.root
        item = index.internalPointer()
        return item if isinstance(item, ResultTreeItem) else self.root

    def index_for_item(self, item: ResultTreeItem) -> QModelIndex:
        parent = item.parent()
        if parent is None:
            return QModelIndex()
        row = parent.indexOfChild(item)
        if row < 0:
            return QModelIndex()
        return self.createIndex(row, 0, item)

    def notify_item_changed(self, item: ResultTreeItem) -> None:
        index = self.index_for_item(item)
        if index.isValid():
            self.dataChanged.emit(index, index)

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()
        self.view.proxy_model.invalidateFilter()


class ResultFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source_index = self.sourceModel().index(source_row, 0, source_parent)
        item = source_index.internalPointer()
        return isinstance(item, ResultTreeItem) and not item.isHidden()


class ResultTreeView(QTreeView):
    """Model/View result list with a narrow QTreeWidget compatibility surface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_model = ResultTreeModel(self)
        self.proxy_model = ResultFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        super().setModel(self.proxy_model)
        self.setHeaderHidden(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setUniformRowHeights(True)

    @classmethod
    def replace(cls, old: QTreeWidget) -> ResultTreeView:
        tree = cls(old.parentWidget())
        tree.setObjectName(old.objectName())
        tree.setGeometry(old.geometry())
        tree.setMinimumSize(old.minimumSize())
        tree.setMaximumSize(old.maximumSize())
        tree.setSizePolicy(old.sizePolicy())
        tree.setFont(old.font())
        tree.setContextMenuPolicy(old.contextMenuPolicy())
        tree.setHorizontalScrollBarPolicy(old.horizontalScrollBarPolicy())
        tree.setVerticalScrollBarPolicy(old.verticalScrollBarPolicy())
        tree.setIndentation(old.indentation())
        tree.setAnimated(old.isAnimated())
        tree.setRootIsDecorated(old.rootIsDecorated())
        tree.show()
        tree.raise_()
        old.hide()
        old.deleteLater()
        return tree

    def setAllColumnsShowFocus(self, enabled: bool) -> None:
        del enabled

    def clear(self) -> None:
        self.source_model.root.takeChildren()

    def addTopLevelItem(self, item: ResultTreeItem) -> None:
        self.source_model.root.addChild(item)

    def topLevelItem(self, index: int) -> ResultTreeItem:
        return self.source_model.root.child(index)

    def topLevelItemCount(self) -> int:
        return self.source_model.root.childCount()

    def selectedItems(self) -> list[ResultTreeItem]:
        items: list[ResultTreeItem] = []
        seen: set[int] = set()
        for proxy_index in self.selectionModel().selectedRows(0):
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.source_model.item_from_index(source_index)
            if id(item) not in seen:
                seen.add(id(item))
                items.append(item)
        return items

    def itemAt(self, position) -> ResultTreeItem | None:
        proxy_index = self.indexAt(position)
        if not proxy_index.isValid():
            return None
        return self.source_model.item_from_index(self.proxy_model.mapToSource(proxy_index))

    def indexFromItem(self, item: ResultTreeItem) -> QModelIndex:
        source_index = self.source_model.index_for_item(item)
        return self.proxy_model.mapFromSource(source_index)

    def setItemSelected(self, item: ResultTreeItem, selected: bool) -> None:
        index = self.indexFromItem(item)
        if not index.isValid():
            return
        flag = QItemSelectionModel.SelectionFlag.Select if selected else QItemSelectionModel.SelectionFlag.Deselect
        self.selectionModel().select(index, flag | QItemSelectionModel.SelectionFlag.Rows)

    def setCurrentItem(self, item: ResultTreeItem) -> None:
        index = self.indexFromItem(item)
        if index.isValid():
            self.setCurrentIndex(index)

    def scrollToItem(self, item: ResultTreeItem) -> None:
        index = self.indexFromItem(item)
        if index.isValid():
            self.scrollTo(index)


ResultItem = ResultTreeItem | QTreeWidgetItem


def create_result_item(
    parent: ResultTreeItem | ResultTreeView | QTreeWidget | QTreeWidgetItem | None = None,
) -> ResultItem:
    if isinstance(parent, (ResultTreeItem, ResultTreeView)) or parent is None:
        return ResultTreeItem(parent)
    return QTreeWidgetItem(parent)
