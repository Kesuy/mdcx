from __future__ import annotations

from collections.abc import Callable, Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from mdcx.models.failure import FailureRecord, failure_stage_label

FAILURE_RECORD_ROLE = Qt.ItemDataRole.UserRole.value + 31


class FailureCenterDialog(QDialog):
    """Compact view over failures from the current scrape run."""

    def __init__(
        self,
        parent=None,
        *,
        retry_callback: Callable[[list[FailureRecord]], bool | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("failure_center")
        self.setWindowTitle("失败中心")
        self.resize(920, 600)
        self._retry_callback = retry_callback
        self._records: list[FailureRecord] = []

        layout = QVBoxLayout(self)

        intro = QLabel("这里汇总本轮刮削失败项。先看问题类型和处理建议；网络、图片等临时故障可直接重试。", self)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.summary = QLabel(self)
        layout.addWidget(self.summary)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["文件", "问题类型", "来源", "可重试"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.currentItemChanged.connect(self._show_current)
        layout.addWidget(self.tree, 3)

        self.detail = QTextBrowser(self)
        self.detail.setPlaceholderText("选择一条失败记录查看原因和处理建议")
        layout.addWidget(self.detail, 2)

        actions = QHBoxLayout()
        self.retry_one = QPushButton("重试所选", self)
        self.retry_all = QPushButton("重试全部可重试项", self)
        self.show_debug = QPushButton("显示调试信息", self)
        self.show_debug.setCheckable(True)
        self.show_debug.setVisible(False)
        self.retry_one.clicked.connect(self._retry_selected)
        self.retry_all.clicked.connect(self._retry_all)
        self.show_debug.toggled.connect(lambda _checked: self._show_current(self.tree.currentItem(), None))
        actions.addWidget(self.retry_one)
        actions.addWidget(self.retry_all)
        actions.addWidget(self.show_debug)
        actions.addStretch(1)
        close = QPushButton("关闭", self)
        close.clicked.connect(self.close)
        actions.addWidget(close)
        layout.addLayout(actions)

    def set_records(self, records: Iterable[FailureRecord]) -> None:
        self._records = list(records)
        self.show_debug.setChecked(False)
        self.tree.clear()

        for record in self._records:
            item = QTreeWidgetItem(
                [
                    record.path.name or str(record.path),
                    record.category.label,
                    record.site or "—",
                    "是" if record.retryable else "否",
                ]
            )
            item.setToolTip(0, str(record.path))
            item.setToolTip(1, record.category.description)
            item.setData(0, FAILURE_RECORD_ROLE, record)
            self.tree.addTopLevelItem(item)

        retryable_count = sum(record.retryable for record in self._records)
        if self._records:
            category_count = len({record.category for record in self._records})
            self.summary.setText(
                f"本轮共 {len(self._records)} 条失败 · {category_count} 类问题 · {retryable_count} 条可直接重试"
            )
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self.summary.setText("当前没有失败记录。")
            self.detail.clear()
            self.show_debug.setVisible(False)

        self._sync_retry_actions(self.tree.currentItem())

    @staticmethod
    def _record_for_item(item: QTreeWidgetItem | None) -> FailureRecord | None:
        if item is None:
            return None
        payload = item.data(0, FAILURE_RECORD_ROLE)
        return payload if isinstance(payload, FailureRecord) else None

    def _show_current(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        record = self._record_for_item(current)
        if record is None:
            self.detail.clear()
            self.show_debug.setVisible(False)
            self._sync_retry_actions(current)
            return

        detail = (
            f"文件：{record.path}\n"
            f"问题类型：{record.category.label}\n"
            f"发生阶段：{failure_stage_label(record.stage)}\n"
            f"来源站点：{record.site or '未记录'}\n"
            f"可直接重试：{'是' if record.retryable else '否'}\n\n"
            f"处理建议：{record.category.description}\n\n"
            f"原始原因：{record.message}"
        )
        has_debug = bool(record.debug_detail and record.debug_detail != record.message)
        self.show_debug.setVisible(has_debug)
        if has_debug and self.show_debug.isChecked():
            detail += f"\n\n调试信息：\n{record.debug_detail}"
        self.detail.setPlainText(detail)
        self._sync_retry_actions(current)

    def _sync_retry_actions(self, item: QTreeWidgetItem | None) -> None:
        record = self._record_for_item(item)
        self.retry_one.setEnabled(bool(record and record.retryable))
        self.retry_all.setEnabled(any(record.retryable for record in self._records))

    def _retry(self, records: list[FailureRecord]) -> None:
        retryable = [record for record in records if record.retryable]
        if not retryable or self._retry_callback is None:
            return
        accepted = self._retry_callback(retryable)
        if accepted is not False:
            self.set_records(record for record in self._records if record not in retryable)

    def _retry_selected(self) -> None:
        record = self._record_for_item(self.tree.currentItem())
        self._retry([record] if record is not None else [])

    def _retry_all(self) -> None:
        self._retry(self._records)
