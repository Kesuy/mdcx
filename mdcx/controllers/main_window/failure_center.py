from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mdcx.models.failure import FailureRecord, failure_stage_label

FAILURE_RECORD_ROLE = Qt.ItemDataRole.UserRole.value + 31


class FailureCenterDialog(QDialog):
    """可筛选、可诊断并可安全重试的本轮失败任务中心。"""

    def __init__(
        self,
        parent=None,
        *,
        retry_callback: Callable[[list[FailureRecord]], bool | None] | None = None,
        records_provider: Callable[[], Iterable[FailureRecord]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("failure_center")
        self.setWindowTitle("失败中心")
        self.resize(1080, 700)
        self.setMinimumSize(860, 540)
        self._retry_callback = retry_callback
        self._records_provider = records_provider
        self._records: list[FailureRecord] = []
        self._visible_records: list[FailureRecord] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        intro = QLabel(
            "集中查看本轮失败原因。可按文件、番号、站点或错误内容搜索；"
            "“可直接重试”适合网络等临时故障，“需处理”请先按建议修复后再手动重试。",
            self,
        )
        intro.setWordWrap(True)
        intro.setProperty("semanticRole", "help")
        layout.addWidget(intro)

        overview = QHBoxLayout()
        self.summary = QLabel(self)
        self.summary.setProperty("sectionTitle", True)
        self.category_summary = QLabel(self)
        self.category_summary.setProperty("semanticRole", "help")
        self.category_summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        overview.addWidget(self.summary, 1)
        overview.addWidget(self.category_summary)
        layout.addLayout(overview)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.search = QLineEdit(self)
        self.search.setObjectName("failure_center_search")
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText("搜索文件名 / 番号 / 站点 / 原因")
        self.category_filter = QComboBox(self)
        self.category_filter.setObjectName("failure_center_category_filter")
        self.retry_filter = QComboBox(self)
        self.retry_filter.setObjectName("failure_center_retry_filter")
        self.retry_filter.addItem("全部状态", "all")
        self.retry_filter.addItem("可直接重试", "retryable")
        self.retry_filter.addItem("需处理", "attention")
        self.clear_filter = QPushButton("清除筛选", self)
        self.refresh = QPushButton("刷新", self)
        self.refresh.setVisible(records_provider is not None)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.category_filter)
        filters.addWidget(self.retry_filter)
        filters.addWidget(self.clear_filter)
        filters.addWidget(self.refresh)
        layout.addLayout(filters)

        self.splitter = QSplitter(Qt.Orientation.Vertical, self)

        self.tree = QTreeWidget(self.splitter)
        self.tree.setObjectName("failure_center_tree")
        self.tree.setHeaderLabels(["文件", "番号", "问题类型", "阶段", "来源", "状态", "时间"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3, 4, 5, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

        detail_panel = QWidget(self.splitter)
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(6)
        self.detail = QTextBrowser(detail_panel)
        self.detail.setObjectName("failure_center_detail")
        self.detail.setPlaceholderText("选择一条失败记录查看原因、处理建议和任务上下文")
        self.detail.setProperty("semanticRole", "code")
        detail_layout.addWidget(self.detail, 1)

        detail_actions = QHBoxLayout()
        self.open_folder = QPushButton("打开所在文件夹", detail_panel)
        self.copy_path = QPushButton("复制路径", detail_panel)
        self.copy_diagnostic = QPushButton("复制诊断", detail_panel)
        self.show_debug = QPushButton("显示调试信息", detail_panel)
        self.show_debug.setCheckable(True)
        self.show_debug.setVisible(False)
        detail_actions.addWidget(self.open_folder)
        detail_actions.addWidget(self.copy_path)
        detail_actions.addWidget(self.copy_diagnostic)
        detail_actions.addWidget(self.show_debug)
        detail_actions.addStretch(1)
        detail_layout.addLayout(detail_actions)

        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(detail_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([390, 230])
        layout.addWidget(self.splitter, 1)

        self.feedback = QLabel(self)
        self.feedback.setWordWrap(True)
        self.feedback.setProperty("statusRole", "neutral")
        layout.addWidget(self.feedback)

        actions = QHBoxLayout()
        self.retry_one = QPushButton("直接重试所选", self)
        self.retry_after_fix = QPushButton("处理后重试所选", self)
        self.retry_all = QPushButton("重试当前筛选可重试项", self)
        self.export_report = QPushButton("导出报告…", self)
        self.retry_one.clicked.connect(self._retry_selected)
        self.retry_after_fix.clicked.connect(self._retry_selected_after_fix)
        self.retry_all.clicked.connect(self._retry_all)
        self.export_report.clicked.connect(self._export_report)
        actions.addWidget(self.retry_one)
        actions.addWidget(self.retry_after_fix)
        actions.addWidget(self.retry_all)
        actions.addSpacing(8)
        actions.addWidget(self.export_report)
        actions.addStretch(1)
        close = QPushButton("关闭", self)
        close.clicked.connect(self.close)
        actions.addWidget(close)
        layout.addLayout(actions)

        self.search.textChanged.connect(self._apply_filters)
        self.category_filter.currentIndexChanged.connect(self._apply_filters)
        self.retry_filter.currentIndexChanged.connect(self._apply_filters)
        self.clear_filter.clicked.connect(self._clear_filters)
        self.refresh.clicked.connect(self._refresh_records)
        self.tree.currentItemChanged.connect(self._show_current)
        self.tree.itemSelectionChanged.connect(self._sync_actions)
        self.show_debug.toggled.connect(lambda _checked: self._show_current(self.tree.currentItem(), None))
        self.open_folder.clicked.connect(self._open_current_folder)
        self.copy_path.clicked.connect(self._copy_current_path)
        self.copy_diagnostic.clicked.connect(self._copy_current_diagnostic)

    def set_records(self, records: Iterable[FailureRecord]) -> None:
        self._records = list(records)
        self.show_debug.setChecked(False)
        self.feedback.clear()
        self._rebuild_category_filter()
        self._apply_filters()

    def _rebuild_category_filter(self) -> None:
        previous = self.category_filter.currentData()
        categories = sorted({record.category for record in self._records}, key=lambda item: item.label)
        blocked = self.category_filter.blockSignals(True)
        try:
            self.category_filter.clear()
            self.category_filter.addItem("全部问题", "")
            for category in categories:
                self.category_filter.addItem(category.label, category.value)
            index = self.category_filter.findData(previous)
            self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        finally:
            self.category_filter.blockSignals(blocked)

    @staticmethod
    def _searchable_text(record: FailureRecord) -> str:
        context_text = " ".join(str(value) for value in record.context.values() if value not in (None, ""))
        return " ".join(
            (
                str(record.path),
                record.path.name,
                record.category.label,
                failure_stage_label(record.stage),
                record.site,
                record.message,
                str(record.context.get("number", "")),
                context_text,
            )
        ).casefold()

    def _record_matches(self, record: FailureRecord) -> bool:
        query = self.search.text().strip().casefold()
        if query and query not in self._searchable_text(record):
            return False

        category_value = str(self.category_filter.currentData() or "")
        if category_value and record.category.value != category_value:
            return False

        retry_mode = str(self.retry_filter.currentData() or "all")
        if retry_mode == "retryable" and not record.retryable:
            return False
        if retry_mode == "attention" and record.retryable:
            return False
        return True

    @staticmethod
    def _display_time(record: FailureRecord) -> str:
        try:
            return record.timestamp.astimezone().strftime("%H:%M:%S")
        except Exception:
            return ""

    def _apply_filters(self, *_args) -> None:
        current_record = self._record_for_item(self.tree.currentItem())
        self.tree.clear()
        self._visible_records = [record for record in self._records if self._record_matches(record)]

        current_item: QTreeWidgetItem | None = None
        for record in self._visible_records:
            number = str(record.context.get("number", "") or "—")
            item = QTreeWidgetItem(
                [
                    record.path.name or str(record.path),
                    number,
                    record.category.label,
                    failure_stage_label(record.stage),
                    record.site or "—",
                    "可直接重试" if record.retryable else "需处理",
                    self._display_time(record),
                ]
            )
            item.setToolTip(0, str(record.path))
            item.setToolTip(2, record.category.description)
            item.setToolTip(5, "可直接重新执行" if record.retryable else "建议先按下方处理建议修复后再重试")
            item.setData(0, FAILURE_RECORD_ROLE, record)
            self.tree.addTopLevelItem(item)
            if current_record is record:
                current_item = item

        if current_item is None and self.tree.topLevelItemCount():
            current_item = self.tree.topLevelItem(0)
        if current_item is not None:
            self.tree.setCurrentItem(current_item)
        else:
            self.detail.clear()
            self.show_debug.setVisible(False)

        self._update_summary()
        self._sync_actions()

    def _update_summary(self) -> None:
        total = len(self._records)
        visible = len(self._visible_records)
        retryable = sum(record.retryable for record in self._records)
        attention = total - retryable
        if total:
            suffix = f" · 当前显示 {visible}" if visible != total else ""
            self.summary.setText(f"本轮失败 {total} · 可直接重试 {retryable} · 需处理 {attention}{suffix}")
            counts = Counter(record.category.label for record in self._visible_records)
            self.category_summary.setText(" · ".join(f"{label} {count}" for label, count in counts.most_common(4)))
        else:
            self.summary.setText("当前没有失败记录。")
            self.category_summary.clear()

    def _clear_filters(self) -> None:
        self.search.clear()
        self.category_filter.setCurrentIndex(0)
        self.retry_filter.setCurrentIndex(0)
        self._apply_filters()

    def _refresh_records(self) -> None:
        if self._records_provider is None:
            return
        self.set_records(self._records_provider())
        self.feedback.setText("已刷新失败记录。")

    @staticmethod
    def _record_for_item(item: QTreeWidgetItem | None) -> FailureRecord | None:
        if item is None:
            return None
        payload = item.data(0, FAILURE_RECORD_ROLE)
        return payload if isinstance(payload, FailureRecord) else None

    def _selected_records(self) -> list[FailureRecord]:
        records: list[FailureRecord] = []
        seen: set[int] = set()
        for item in self.tree.selectedItems():
            record = self._record_for_item(item)
            if record is not None and id(record) not in seen:
                seen.add(id(record))
                records.append(record)
        return records

    @staticmethod
    def _context_lines(record: FailureRecord) -> list[str]:
        labels = {
            "number": "番号",
            "show_name": "任务名称",
            "scrape_like": "刮削模式",
            "selected_site": "指定站点",
        }
        lines: list[str] = []
        for key, value in record.context.items():
            if value in (None, ""):
                continue
            label = labels.get(str(key), str(key))
            lines.append(f"{label}：{value}")
        return lines

    def _detail_text(self, record: FailureRecord, *, include_debug: bool) -> str:
        context_lines = self._context_lines(record)
        parts = [
            f"文件：{record.path}",
            f"问题类型：{record.category.label}",
            f"发生阶段：{failure_stage_label(record.stage)}",
            f"来源站点：{record.site or '未记录 / 多站点'}",
            f"状态：{'可直接重试' if record.retryable else '需先处理'}",
            f"时间：{record.timestamp.astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if context_lines:
            parts.extend(("", "任务上下文：", *context_lines))
        parts.extend(
            (
                "",
                f"处理建议：{record.category.description}",
                "",
                f"原始原因：{record.message}",
            )
        )
        if include_debug and record.debug_detail and record.debug_detail != record.message:
            parts.extend(("", "调试信息：", record.debug_detail))
        return "\n".join(parts)

    def _show_current(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        record = self._record_for_item(current)
        if record is None:
            self.detail.clear()
            self.show_debug.setVisible(False)
            self._sync_actions()
            return

        has_debug = bool(record.debug_detail and record.debug_detail != record.message)
        self.show_debug.setVisible(has_debug)
        self.detail.setPlainText(self._detail_text(record, include_debug=has_debug and self.show_debug.isChecked()))
        self._sync_actions()

    def _sync_actions(self) -> None:
        selected = self._selected_records()
        current = self._record_for_item(self.tree.currentItem())
        self.retry_one.setEnabled(any(record.retryable for record in selected))
        self.retry_after_fix.setEnabled(bool(selected))
        self.retry_all.setEnabled(any(record.retryable for record in self._visible_records))
        self.export_report.setEnabled(bool(self._visible_records))
        self.copy_path.setEnabled(current is not None)
        self.copy_diagnostic.setEnabled(current is not None)
        self.open_folder.setEnabled(bool(current and current.path.parent.exists()))

    def _retry(self, records: list[FailureRecord], *, direct_only: bool) -> None:
        requested = [record for record in records if record.retryable] if direct_only else list(records)
        if not requested or self._retry_callback is None:
            return
        accepted = self._retry_callback(requested)
        if accepted is False:
            self.feedback.setText("当前无法开始重试；请等待正在进行的刮削结束后再试。")
            return
        requested_ids = {id(record) for record in requested}
        self._records = [record for record in self._records if id(record) not in requested_ids]
        self.feedback.setText(f"已提交 {len(requested)} 个任务重新刮削。")
        self._rebuild_category_filter()
        self._apply_filters()

    def _retry_selected(self) -> None:
        self._retry(self._selected_records(), direct_only=True)

    def _retry_selected_after_fix(self) -> None:
        self._retry(self._selected_records(), direct_only=False)

    def _retry_all(self) -> None:
        self._retry(self._visible_records, direct_only=True)

    def _open_current_folder(self) -> None:
        record = self._record_for_item(self.tree.currentItem())
        if record is None:
            return
        folder = record.path.parent
        if folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _copy_current_path(self) -> None:
        record = self._record_for_item(self.tree.currentItem())
        if record is not None:
            QApplication.clipboard().setText(str(record.path))
            self.feedback.setText("已复制文件路径。")

    def _copy_current_diagnostic(self) -> None:
        record = self._record_for_item(self.tree.currentItem())
        if record is None:
            return
        include_debug = self.show_debug.isVisible() and self.show_debug.isChecked()
        QApplication.clipboard().setText(self._detail_text(record, include_debug=include_debug))
        self.feedback.setText("已复制当前诊断信息。")

    def _export_report(self) -> None:
        if not self._visible_records:
            return
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出失败报告",
            "mdcx-failures.csv",
            "CSV 文件 (*.csv);;文本文件 (*.txt)",
        )
        if not filename:
            return
        target = Path(filename)
        try:
            if target.suffix.casefold() == ".txt":
                text = "\n\n" + ("=" * 72) + "\n\n"
                target.write_text(
                    text.join(self._detail_text(record, include_debug=False) for record in self._visible_records),
                    encoding="utf-8",
                )
            else:
                if target.suffix.casefold() != ".csv":
                    target = target.with_suffix(".csv")
                with target.open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(
                        ["文件", "完整路径", "番号", "问题类型", "阶段", "来源", "状态", "时间", "原因", "处理建议"]
                    )
                    for record in self._visible_records:
                        writer.writerow(
                            [
                                record.path.name,
                                str(record.path),
                                record.context.get("number", ""),
                                record.category.label,
                                failure_stage_label(record.stage),
                                record.site,
                                "可直接重试" if record.retryable else "需处理",
                                record.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                                record.message,
                                record.category.description,
                            ]
                        )
        except OSError as error:
            self.feedback.setText(f"导出失败：{error}")
            return
        self.feedback.setText(f"已导出 {len(self._visible_records)} 条记录：{target}")
