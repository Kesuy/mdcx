from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from mdcx.models.failure import FailureRecord

FAILURE_RECORD_ROLE = Qt.ItemDataRole.UserRole.value + 31


class FailureCenterDialog(QDialog):
    """Grouped, retry-aware view over structured scrape failures."""

    def __init__(
        self,
        parent=None,
        *,
        retry_callback: Callable[[list[FailureRecord]], bool | None] | None = None,
        legacy_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("failure_center")
        self.setWindowTitle("失败中心")
        self.resize(820, 560)
        self._retry_callback = retry_callback
        self._records: list[FailureRecord] = []

        layout = QVBoxLayout(self)
        self.summary = QLabel(self)
        layout.addWidget(self.summary)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["类别 / 阶段 / 文件", "站点", "可重试"])
        self.tree.setAlternatingRowColors(True)
        self.tree.currentItemChanged.connect(self._show_current)
        layout.addWidget(self.tree, 3)
        self.detail = QTextBrowser(self)
        self.detail.setPlaceholderText("选择一条失败记录查看详细原因")
        layout.addWidget(self.detail, 2)

        actions = QHBoxLayout()
        self.retry_one = QPushButton("重试所选", self)
        self.retry_group = QPushButton("重试当前分类", self)
        self.show_debug = QPushButton("显示调试信息", self)
        self.show_debug.setCheckable(True)
        self.show_debug.setVisible(False)
        self.retry_one.clicked.connect(self._retry_selected)
        self.retry_group.clicked.connect(self._retry_selected_group)
        self.show_debug.toggled.connect(lambda _checked: self._show_current(self.tree.currentItem(), None))
        actions.addWidget(self.retry_one)
        actions.addWidget(self.retry_group)
        actions.addWidget(self.show_debug)
        if legacy_callback is not None:
            legacy = QPushButton("查看旧失败日志", self)
            legacy.clicked.connect(legacy_callback)
            actions.addWidget(legacy)
        actions.addStretch(1)
        close = QPushButton("关闭", self)
        close.clicked.connect(self.close)
        actions.addWidget(close)
        layout.addLayout(actions)

    def set_records(self, records: Iterable[FailureRecord]) -> None:
        self._records = list(records)
        self.show_debug.setChecked(False)
        self.tree.clear()
        grouped: dict[object, dict[str, list[FailureRecord]]] = defaultdict(lambda: defaultdict(list))
        for record in self._records:
            grouped[record.category][record.stage].append(record)

        for category, stages in sorted(grouped.items(), key=lambda item: item[0].value):
            count = sum(len(records) for records in stages.values())
            category_item = QTreeWidgetItem([f"{category.value} ({count})"])
            category_item.setData(0, FAILURE_RECORD_ROLE, [record for records in stages.values() for record in records])
            self.tree.addTopLevelItem(category_item)
            for stage, records in sorted(stages.items()):
                stage_item = QTreeWidgetItem([f"{stage} ({len(records)})"])
                stage_item.setData(0, FAILURE_RECORD_ROLE, records)
                category_item.addChild(stage_item)
                for record in records:
                    item = QTreeWidgetItem(
                        [record.path.name or str(record.path), record.site or "—", "是" if record.retryable else "否"]
                    )
                    item.setToolTip(0, record.message)
                    item.setData(0, FAILURE_RECORD_ROLE, record)
                    stage_item.addChild(item)
            category_item.setExpanded(True)
        self.summary.setText(f"共 {len(self._records)} 条失败记录，{sum(r.retryable for r in self._records)} 条可重试")
        self._sync_retry_actions(None)

    def _records_for_item(self, item: QTreeWidgetItem | None) -> list[FailureRecord]:
        if item is None:
            return []
        payload = item.data(0, FAILURE_RECORD_ROLE)
        if isinstance(payload, FailureRecord):
            return [payload]
        if isinstance(payload, list):
            return [record for record in payload if isinstance(record, FailureRecord)]
        return []

    def _show_current(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        records = self._records_for_item(current)
        if len(records) == 1:
            record = records[0]
            detail = (
                f"路径：{record.path}\n阶段：{record.stage}\n类别：{record.category.value}\n"
                f"站点：{record.site or '—'}\n可重试：{'是' if record.retryable else '否'}\n\n"
                f"原因：{record.message}"
            )
            has_debug = bool(record.debug_detail and record.debug_detail != record.message)
            self.show_debug.setVisible(has_debug)
            if has_debug and self.show_debug.isChecked():
                detail += f"\n\n调试信息：\n{record.debug_detail}"
            self.detail.setPlainText(detail)
        elif records:
            self.detail.setPlainText(f"当前分组包含 {len(records)} 条失败记录。")
        else:
            self.detail.clear()
            self.show_debug.setVisible(False)
        self._sync_retry_actions(current)

    def _sync_retry_actions(self, item: QTreeWidgetItem | None) -> None:
        records = self._records_for_item(item)
        is_leaf = len(records) == 1 and isinstance(item.data(0, FAILURE_RECORD_ROLE), FailureRecord) if item else False
        self.retry_one.setVisible(is_leaf and records[0].retryable)
        self.retry_group.setVisible(bool(records) and not is_leaf and any(record.retryable for record in records))

    def _retry(self, records: list[FailureRecord]) -> None:
        retryable = [record for record in records if record.retryable]
        if retryable and self._retry_callback is not None:
            accepted = self._retry_callback(retryable)
            if accepted is not False:
                self.set_records(record for record in self._records if record not in retryable)

    def _retry_selected(self) -> None:
        self._retry(self._records_for_item(self.tree.currentItem()))

    def _retry_selected_group(self) -> None:
        self._retry(self._records_for_item(self.tree.currentItem()))
