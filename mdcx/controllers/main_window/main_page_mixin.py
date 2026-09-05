from __future__ import annotations

import os
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from PyQt6.QtCore import QEvent, QItemSelectionModel, QPointF, Qt, QTimer
from PyQt6.QtGui import QHoverEvent
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox, QPushButton

from mdcx.config.extend import deal_url
from mdcx.config.manager import manager
from mdcx.core.local_nfo_loader import LocalNfoLoadError, load_local_nfo
from mdcx.core.scraper import again_search
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.flags import Flags
from mdcx.models.log_buffer import LogBuffer
from mdcx.models.types import CrawlersResult, ShowData
from mdcx.signals import signal_qt
from mdcx.utils import executor, get_current_time, split_path
from mdcx.utils.file import open_file_thread

from .file_controller import FileOperationKind, classify_file_failure
from .nfo_controller import NfoController
from .responsive_layout import show_responsive_overlay
from .result_model import RESULT_DATA_ROLE, RESULT_NAME_ROLE, ResultItem, ResultTreeItem, create_result_item
from .result_sorting import ResultSortEntry, ResultSortMode, sort_result_entries


def _result_item_name(item: ResultItem) -> str:
    return str(item.data(0, RESULT_NAME_ROLE) or item.text(0))


class MainPageMixin:
    @staticmethod
    def _result_item_name(item: ResultItem) -> str:
        return _result_item_name(item)

    def pushButton_start_scrape_clicked(self):
        self._get_scrape_controller().toggle()

    def pushButton_stop_scrape_clicked(self):
        self._get_scrape_controller().stop()

    def _show_stop_info(self):
        self._get_scrape_controller().show_stop_info()

    def show_stop_info_thread(
        self,
    ):
        self._get_scrape_controller().schedule_stop_info()

    def _kill_threads(self):
        self._get_scrape_controller().kill_workers()

    def set_processbar(self, value):
        self.Ui.progressBar_scrape.setProperty("value", value)

    def _addTreeChild(self, result, filename, show_data: ShowData | None = None):
        parent = self.item_succ if result == "succ" else self.item_fail
        node = create_result_item(parent)
        node.setData(0, RESULT_NAME_ROLE, filename)
        display_text = filename
        if show_data is not None:
            node.setData(0, RESULT_DATA_ROLE, show_data)
            number = show_data.data.number or show_data.file_info.number
            provenance = show_data.data.get_provenance(CrawlerResultFields.TITLE)
            source = (
                provenance.source
                if provenance is not None
                else show_data.data.field_sources.get(CrawlerResultFields.TITLE, "")
            )
            state = "完成" if result == "succ" else "失败"
            icon = "✓" if result == "succ" else "⚠"
            primary = number or filename
            filename_suffix = f" — {filename}" if filename != primary else ""
            display_text = f"{icon} {primary} · {source or '本地'}{filename_suffix}"
            node.setData(
                0,
                Qt.ItemDataRole.ToolTipRole,
                f"状态：{state}\n番号/名称：{number or filename}\n来源：{source or '本地'}\n{filename}"
                + ("\n双击打开失败中心并重试" if result == "fail" else ""),
            )
        node.setText(0, display_text)
        if result == "succ":
            insertion_index = getattr(self, "_result_insertion_index", 0)
            node.setData(0, Qt.ItemDataRole.UserRole, insertion_index)
            self._result_insertion_index = insertion_index + 1
        filter_results = getattr(self, "_filter_results", None)
        if filter_results is not None:
            filter_results()

    def _get_single_selected_entry(self) -> tuple[ResultItem, str, ShowData, Path] | None:
        selected_entries = self._get_selected_entries()
        if len(selected_entries) != 1:
            return None
        return selected_entries[0]

    def _has_single_selected_result_item(self) -> bool:
        return self._get_single_selected_entry() is not None

    def _set_result_item_as_current_selection(self, item: ResultItem) -> None:
        if _result_item_name(item) in {"成功", "失败"}:
            return

        tree = self.Ui.treeWidget_number
        selected_items = tree.selectedItems()
        if item not in selected_items:
            tree.clearSelection()
            item.setSelected(True)
        model_index = tree.indexFromItem(item)
        if model_index.isValid():
            tree.selectionModel().setCurrentIndex(model_index, QItemSelectionModel.SelectionFlag.NoUpdate)

    def show_list_name(self, status: Literal["succ", "fail"], show_data: ShowData, real_number=""):
        # 添加树状节点
        self._addTreeChild(status, show_data.show_name, show_data)

        if not show_data.data.title:
            show_data.data.title = LogBuffer.error().get()
            show_data.data.number = real_number
        self.json_array[show_data.show_name] = show_data
        self._sort_success_results()
        if not self._has_single_selected_result_item():
            self.show_name = show_data.show_name
            self.set_main_info(show_data)

    def _sort_success_results(self, *_args) -> None:
        if not hasattr(self, "item_succ") or not hasattr(self, "result_sort_combo"):
            return
        items = [self.item_succ.child(index) for index in range(self.item_succ.childCount())]
        entries: list[ResultSortEntry] = []
        item_by_insertion: dict[int, ResultItem] = {}
        for item in items:
            show_name = _result_item_name(item)
            show_data = item.data(0, RESULT_DATA_ROLE) or self.json_array.get(show_name)
            insertion_index = int(item.data(0, Qt.ItemDataRole.UserRole) or 0)
            entries.append(
                ResultSortEntry(
                    show_name=show_name,
                    number=show_data.data.number if show_data else "",
                    actor=show_data.data.actor if show_data else "",
                    insertion_index=insertion_index,
                )
            )
            item_by_insertion[insertion_index] = item

        mode = cast("ResultSortMode", self.result_sort_combo.currentText())
        sorted_entries = sort_result_entries(
            entries,
            mode,
            descending=getattr(self, "_result_sort_descending", False),
        )
        ordered_items = [item_by_insertion[entry.insertion_index] for entry in sorted_entries]
        if isinstance(self.item_succ, ResultTreeItem):
            self.item_succ.reorderChildren(ordered_items)
        else:
            self.item_succ.takeChildren()
            self.item_succ.addChildren(ordered_items)

    def _toggle_result_sort_order(self) -> None:
        self._result_sort_descending = not getattr(self, "_result_sort_descending", False)
        self.result_sort_order_button.setText("↓" if self._result_sort_descending else "↑")
        self._sort_success_results()

    def _filter_results(self, *_args) -> None:
        if not hasattr(self, "item_succ") or not hasattr(self, "result_filter_edit"):
            return
        query = self.result_filter_edit.text().strip().casefold()
        status = self.result_status_combo.currentText()
        for root, root_status in ((self.item_succ, "成功"), (self.item_fail, "失败")):
            visible_children = 0
            status_visible = status in {"全部", root_status}
            for index in range(root.childCount()):
                item = root.child(index)
                show_data = item.data(0, RESULT_DATA_ROLE) or self.json_array.get(_result_item_name(item))
                haystack = item.text(0)
                if show_data is not None:
                    haystack += f" {show_data.data.number} {show_data.data.title} {show_data.data.actor}"
                visible = status_visible and (not query or query in haystack.casefold())
                item.setHidden(not visible)
                visible_children += int(visible)
            root.setHidden(not status_visible or (bool(query) and visible_children == 0))

    async def _set_pixmap(
        self,
        poster_path: Path | None,
        thumb_path: Path | None,
        poster_from="",
        cover_from="",
        force_reload: bool = False,
    ):
        self._request_preview_images(poster_path, thumb_path, poster_from, cover_from, force_reload=force_reload)

    def _get_selected_result_items(self) -> list[ResultItem]:
        """
        获取当前树状图中有效的结果项（不包含成功/失败根节点）。
        """
        selected_items = []
        for item in self.Ui.treeWidget_number.selectedItems():
            if not item or _result_item_name(item) in {"成功", "失败"}:
                continue
            if item.data(0, RESULT_DATA_ROLE) is None and _result_item_name(item) not in self.json_array:
                continue
            selected_items.append(item)
        return selected_items

    def _get_selected_entries(self) -> list[tuple[ResultItem, str, ShowData, Path]]:
        result = []
        for item in self._get_selected_result_items():
            show_name = _result_item_name(item)
            show_data = item.data(0, RESULT_DATA_ROLE) or self.json_array.get(show_name)
            if show_data is None or not show_data.file_info.file_path:
                continue
            result.append((item, show_name, show_data, show_data.file_info.file_path))
        return result

    def _build_delete_preview(self, paths: list[Path], limit: int = 8) -> str:
        plan = self._get_file_controller().build_plan(FileOperationKind.DELETE_FILES, paths)
        return plan.preview(limit)

    def _shorten_text(self, text: str, limit: int) -> str:
        text = str(text).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"

    def _normalize_delete_error_reason(self, error_text: str) -> str:
        return classify_file_failure(error_text).reason

    def _build_action_result_text(self, success_count: int, failure_count: int, skipped_count: int = 0) -> str:
        parts = [f"成功 {success_count} 个"]
        if skipped_count:
            parts.append(f"跳过 {skipped_count} 个")
        parts.append(f"失败 {failure_count} 个")
        return "，".join(parts)

    def _show_action_failure_feedback(
        self,
        action_name: str,
        success_count: int,
        failure_details: list[tuple[Path, str]],
        skipped_count: int = 0,
        retry_callback: Callable[[], None] | None = None,
    ) -> None:
        if not failure_details:
            return

        preview_limit = 3
        preview_lines = []
        for path, reason in failure_details[:preview_limit]:
            failure = classify_file_failure(reason)
            preview_lines.append(
                f"- {self._shorten_text(str(path), 90)}\n"
                f"  类别：{failure.category.value}\n"
                f"  原因：{self._shorten_text(failure.reason, 70)}"
            )
        if len(failure_details) > preview_limit:
            preview_lines.append(f"... 其余 {len(failure_details) - preview_limit} 条请展开“显示详情”或查看日志")

        detail_limit = 20
        detail_lines = []
        for index, (path, reason) in enumerate(failure_details[:detail_limit], start=1):
            failure = classify_file_failure(reason)
            detail_lines.append(
                f"{index}. {path}\n"
                f"   类别：{failure.category.value}\n"
                f"   原因：{failure.reason}\n"
                f"   建议：{failure.suggestion}"
            )
        if len(failure_details) > detail_limit:
            detail_lines.append(f"... 其余 {len(failure_details) - detail_limit} 条请查看日志")
        detail_text = "\n\n".join(detail_lines)

        preview_text = "\n".join(preview_lines)
        box = QMessageBox(QMessageBox.Icon.Warning, f"{action_name}结果", f"{action_name}完成")
        box.setInformativeText(
            f"{self._build_action_result_text(success_count, len(failure_details), skipped_count)}\n\n{preview_text}"
        )
        box.setDetailedText(detail_text)
        view_log_button = box.addButton("查看日志", QMessageBox.ButtonRole.ActionRole)
        retry_button = None
        if retry_callback is not None:
            retry_button = box.addButton("重试失败项", QMessageBox.ButtonRole.ActionRole)
        box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
        self._bind_localized_message_box_detail_buttons(box)
        box.exec()

        if box.clickedButton() == view_log_button:
            self.pushButton_show_log_clicked()
            self.show_hide_logs(True)
        elif retry_button is not None and box.clickedButton() == retry_button:
            retry_callback()

    def _localize_message_box_detail_buttons(self, box: QMessageBox) -> None:
        for button in box.findChildren(QPushButton):
            text = button.text().strip()
            if text == "Show Details...":
                button.setText("显示详情")
            elif text == "Hide Details...":
                button.setText("隐藏详情")

    def _bind_localized_message_box_detail_buttons(self, box: QMessageBox) -> None:
        def relocalize() -> None:
            self._localize_message_box_detail_buttons(box)

        relocalize()
        QTimer.singleShot(0, relocalize)
        for button in box.findChildren(QPushButton):
            button.clicked.connect(lambda _checked=False: QTimer.singleShot(0, relocalize))

    def _select_link_output_dir(self, link_name: str) -> Path | None:
        return self._get_file_controller().select_link_output_dir(link_name)

    def _confirm_record_link_paths(self, link_name: str) -> bool | None:
        return self._get_file_controller().confirm_record_link_paths(link_name)

    def _build_link_target_path(
        self,
        source_path: Path,
        output_dir: Path,
        display_path: Path | None = None,
        group_in_named_dir: bool = False,
    ) -> tuple[Path, list[str]]:
        return self._get_file_controller().build_link_target_path(
            source_path, output_dir, display_path, group_in_named_dir
        )

    def _get_link_dir_name_max(self) -> int:
        return self._get_file_controller().get_link_dir_name_max()

    def _fit_link_dir_name_length(self, dir_name: str, suffix: str = "") -> str:
        return self._get_file_controller().fit_link_dir_name_length(dir_name, suffix)

    def _is_windows_reserved_dir_name(self, dir_name: str) -> bool:
        return self._get_file_controller().is_windows_reserved_dir_name(dir_name)

    def _sanitize_link_dir_name(self, raw_name: str) -> tuple[str, list[str]]:
        return self._get_file_controller().sanitize_link_dir_name(raw_name)

    def _can_reuse_link_target_dir(self, target_dir: Path, file_name: str) -> bool:
        return self._get_file_controller().can_reuse_link_target_dir(target_dir, file_name)

    def _get_available_link_target_dir(self, output_dir: Path, dir_name: str, file_name: str) -> tuple[Path, str]:
        return self._get_file_controller().get_available_link_target_dir(output_dir, dir_name, file_name)

    def _prepare_link_target_dir(self, target_path: Path, group_in_named_dir: bool) -> tuple[bool, str, bool]:
        return self._get_file_controller().prepare_link_target_dir(target_path, group_in_named_dir)

    def _cleanup_empty_link_target_dir(self, target_path: Path, created_dir: bool) -> None:
        self._get_file_controller().cleanup_empty_link_target_dir(target_path, created_dir)

    def _create_links_for_selected_files(
        self, link_type: Literal["soft", "hard"], group_in_named_dir: bool = False
    ) -> None:
        self._get_file_controller().create_links(link_type, group_in_named_dir)

    def _find_result_item_by_name(self, show_name: str) -> ResultItem | None:
        for root_item in (self.item_succ, self.item_fail):
            for i in range(root_item.childCount()):
                child = root_item.child(i)
                if _result_item_name(child) == show_name:
                    return child
        return None

    def _clear_main_info_panel(self) -> None:
        self.set_main_info(None)
        self.file_main_open_path = Path()
        self.show_name = None
        self.show_data = None
        if not self.Ui.widget_nfo.isHidden():
            self.Ui.widget_nfo.hide()

    def _remove_deleted_result_items(self, show_names: list[str]) -> None:
        if not show_names:
            return

        current_show_name = self.show_name
        for show_name in show_names:
            self.json_array.pop(show_name, None)

        for show_name in show_names:
            item = self._find_result_item_by_name(show_name)
            if item is None:
                continue
            parent = item.parent()
            if parent is not None:
                parent.removeChild(item)

        self.Ui.treeWidget_number.clearSelection()
        if current_show_name in show_names:
            self._clear_main_info_panel()

    def _show_result_item(self, item: ResultItem | None) -> bool:
        if item is None or _result_item_name(item) in {"成功", "失败"}:
            return False
        show_data = item.data(0, RESULT_DATA_ROLE) or self.json_array.get(_result_item_name(item))
        if show_data is None:
            return False
        self.set_main_info(show_data)
        if not self.Ui.widget_nfo.isHidden():
            self._show_nfo_info()
        return True

    def treeWidget_number_index_clicked(self, index) -> None:
        """Show the node represented by the actual mouse-clicked model index."""

        item_from_index = getattr(self.Ui.treeWidget_number, "itemFromIndex", None)
        item = item_from_index(index) if callable(item_from_index) else None
        try:
            self._show_result_item(item)
        except Exception:
            item_text = item.text(0) if item is not None else "未知条目"
            signal_qt.show_traceback_log(item_text + ": No info!")

    def treeWidget_number_double_clicked(self, index) -> None:
        item_from_index = getattr(self.Ui.treeWidget_number, "itemFromIndex", None)
        item = item_from_index(index) if callable(item_from_index) else None
        if item is not None and item.parent() is self.item_fail and hasattr(self, "show_failure_center"):
            self.show_failure_center()

    def treeWidget_number_clicked(self, *_args):
        selected_items = self._get_selected_result_items()
        if len(selected_items) != 1:
            if len(selected_items) > 1:
                self._clear_main_info_panel()
            return

        item = selected_items[0]
        try:
            self._show_result_item(item)
        except Exception:
            signal_qt.show_traceback_log(item.text(0) + ": No info!")

    def _check_main_file_path(self):
        selected_entries = self._get_selected_entries()
        if len(selected_entries) > 1:
            QMessageBox.about(self, "选择过多", "请只选择一个项目后再使用！！")
            signal_qt.show_scrape_info(f"💡 请只选择一个项目后再使用！{get_current_time()}")
            return False
        if len(selected_entries) == 1:
            _, show_name, show_data, file_path = selected_entries[0]
            self.show_name = show_name
            self.set_main_info(show_data)
            self.file_main_open_path = file_path

        if self.file_main_open_path == Path() or not self.file_main_open_path.is_file():
            QMessageBox.about(self, "没有目标文件", "请刮削后再使用！！")
            signal_qt.show_scrape_info(f"💡 请刮削后使用！{get_current_time()}")
            return False
        return True

    def main_play_click(self):
        """
        主界面点播放
        """
        # 发送hover事件，清除hover状态（因为弹窗后，失去焦点，状态不会变化）
        self.Ui.pushButton_play.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        event = QHoverEvent(QEvent.Type.HoverLeave, QPointF(40, 40), QPointF(0, 0))
        QApplication.sendEvent(self.Ui.pushButton_play, event)
        if self._check_main_file_path():
            # mac需要改为无焦点状态，不然弹窗失去焦点后，再切换回来会有找不到焦点的问题（windows无此问题）
            # if not self.is_windows:
            #     self.setWindowFlags(self.windowFlags() | Qt.WindowDoesNotAcceptFocus)
            #     self.show()
            self.task_manager.submit_sync("open-main-file", open_file_thread, self.file_main_open_path, False)

    def main_open_folder_click(self):
        """
        主界面点打开文件夹
        """
        self.Ui.pushButton_open_folder.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        event = QHoverEvent(QEvent.Type.HoverLeave, QPointF(40, 40), QPointF(0, 0))
        QApplication.sendEvent(self.Ui.pushButton_open_folder, event)
        if self._check_main_file_path():
            # mac需要改为无焦点状态，不然弹窗失去焦点后，再切换回来会有找不到焦点的问题（windows无此问题）
            # if not self.is_windows:
            #     self.setWindowFlags(self.windowFlags() | Qt.WindowDoesNotAcceptFocus)
            #     self.show()
            self.task_manager.submit_sync("open-main-folder", open_file_thread, self.file_main_open_path, True)

    def main_open_nfo_click(self):
        """
        主界面点打开nfo
        """
        self.Ui.pushButton_open_nfo.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        event = QHoverEvent(QEvent.Type.HoverLeave, QPointF(40, 40), QPointF(0, 0))
        QApplication.sendEvent(self.Ui.pushButton_open_nfo, event)
        selected_entries = self._get_selected_entries()
        if len(selected_entries) > 1:
            missing_paths = [str(file_path) for _, _, _, file_path in selected_entries if not file_path.is_file()]
            if missing_paths:
                QMessageBox.warning(
                    self,
                    "无法批量编辑 NFO",
                    f"所选项目中有 {len(missing_paths)} 个媒体文件不存在，请刷新结果后重试。",
                )
                return
            show_responsive_overlay(self, self.Ui.widget_nfo)
            self._show_nfo_info([entry[2] for entry in selected_entries])
            return
        if self._check_main_file_path():
            show_responsive_overlay(self, self.Ui.widget_nfo)
            self._show_nfo_info()

    def main_load_nfo_click(self):
        """选择本地 NFO，并将同目录媒体和图片加载到主界面。"""

        current_path = getattr(self, "file_main_open_path", Path())
        start_folder = current_path.parent if current_path.is_file() else manager.data_folder
        selected_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 NFO 文件",
            start_folder.as_posix(),
            "NFO Files (*.nfo *.NFO);;All Files (*)",
            options=self.options,
        )
        if selected_path:
            self._load_local_nfo_path(Path(selected_path))

    def _load_local_nfo_path(self, nfo_path: Path) -> None:
        try:
            loaded = executor.run(load_local_nfo(nfo_path))
        except LocalNfoLoadError as error:
            QMessageBox.warning(self, "无法加载 NFO", str(error))
            signal_qt.show_log_text(f"\n 🟡 无法加载 NFO：{error}")
            return
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
            QMessageBox.warning(self, "无法加载 NFO", "读取 NFO 时发生错误，请查看日志。")
            return

        loaded_paths = {entry.file_info.file_path for entry in loaded.entries}
        for index in range(self.item_succ.childCount() - 1, -1, -1):
            item = self.item_succ.child(index)
            existing = self.json_array.get(_result_item_name(item))
            if existing is not None and existing.file_info.file_path in loaded_paths:
                self.item_succ.takeChild(index)
                self.json_array.pop(_result_item_name(item), None)

        for entry in loaded.entries:
            self.show_list_name("succ", entry)
            Flags.success_list.add(entry.file_info.file_path)

        self.show_name = loaded.primary.show_name
        self.set_main_info(loaded.primary)
        for index in range(self.item_succ.childCount()):
            item = self.item_succ.child(index)
            if _result_item_name(item) == loaded.primary.show_name:
                self._set_result_item_as_current_selection(item)
                break
        signal_qt.show_log_text(f"\n 📂 已加载本地 NFO：{nfo_path}\n    关联媒体：{len(loaded.entries)} 个")

    def main_open_right_menu(self):
        """
        主界面点打开右键菜单
        """
        # 发送hover事件，清除hover状态（因为弹窗后，失去焦点，状态不会变化）
        self.Ui.pushButton_right_menu.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        event = QHoverEvent(QEvent.Type.HoverLeave, QPointF(40, 40), QPointF(0, 0))
        QApplication.sendEvent(self.Ui.pushButton_right_menu, event)
        self._menu()

    def search_by_number_clicked(self):
        """
        主界面点输入番号
        """
        if self._check_main_file_path():
            file_path = self.file_main_open_path
            main_file_name = split_path(file_path)[1]
            default_text = os.path.splitext(main_file_name)[0].upper()
            text, ok = QInputDialog.getText(
                self, "输入番号重新刮削", f"文件名: {main_file_name}\n请输入番号:", text=default_text
            )
            if ok and text:
                Flags.again_dic[file_path] = (text, "", "")
                signal_qt.show_scrape_info(f"💡 已添加刮削！{get_current_time()}")
                if self.Ui.pushButton_start_cap.text() == "开始":
                    again_search()

    def search_by_url_clicked(self):
        """
        主界面点输入网址
        """
        if self._check_main_file_path():
            file_path = self.file_main_open_path
            main_file_name = split_path(file_path)[1]
            text, ok = QInputDialog.getText(
                self,
                "输入网址重新刮削",
                f"文件名: {main_file_name}\n支持网站:airav_cc、avsex、avsox、dmm、getchu、fc2"
                f"、fc2club、fc2hub、iqqtv、jav321、javbus、javdb、freejavbt、javlibrary、mdtv"
                f"、madouqu、mgstage、7mmtv、xcity、mywife、giga、faleno、dahlia、fantastica、avbase"
                f"、prestige、hdouban、lulubar、love6、cnmdb、theporndb、kin8\n请输入番号对应的网址（不是网站首页地址！！！是番号页面地址！！！）:",
            )
            if ok and text:
                website, url = deal_url(text)
                if website:
                    Flags.again_dic[file_path] = ("", url, website)
                    signal_qt.show_scrape_info(f"💡 已添加刮削！{get_current_time()}")
                    if self.Ui.pushButton_start_cap.text() == "开始":
                        again_search()
                else:
                    signal_qt.show_scrape_info(f"💡 不支持的网站！{get_current_time()}")

    def main_del_file_click(self):
        """
        主界面点删除文件
        """
        selected_entries = self._get_selected_entries()
        if selected_entries:
            delete_targets = [(show_name, file_path) for _, show_name, _, file_path in selected_entries]
        else:
            if not self._check_main_file_path():
                return
            delete_targets = [(self.show_name or "", self.file_main_open_path)]

        if not delete_targets:
            return

        file_paths = [file_path for _, file_path in delete_targets]
        plan = self._get_file_controller().build_plan(FileOperationKind.DELETE_FILES, file_paths)
        if not self._get_file_controller().confirm_plan(plan, accept_text="确认删除文件"):
            return

        signal_qt.show_log_text(" 🗑 开始删除文件")
        signal_qt.show_log_text(f" 📦 本次待删除文件数: {len(file_paths)}")

        success_show_names, failure_details, failed_targets = self._get_file_controller().delete_files(delete_targets)

        self._remove_deleted_result_items(success_show_names)
        fail_count = len(failure_details)
        success_count = len(file_paths) - fail_count
        signal_qt.show_log_text(f" 🎉 删除文件完成：成功 {success_count} 个，失败 {fail_count} 个")
        if fail_count:
            signal_qt.show_scrape_info(
                f"💡 文件删除完成，成功 {success_count} 个，失败 {fail_count} 个！{get_current_time()}"
            )
            self._show_action_failure_feedback(
                "删除文件",
                success_count,
                failure_details,
                retry_callback=lambda: self._get_file_controller().retry_delete_files(failed_targets),
            )
        elif success_count == 1:
            signal_qt.show_scrape_info(f"💡 已删除文件！{get_current_time()}")
        else:
            signal_qt.show_scrape_info(f"💡 已删除 {success_count} 个文件！{get_current_time()}")

    def main_del_folder_click(self):
        """
        主界面点删除文件夹
        """
        selected_entries = self._get_selected_entries()
        if selected_entries:
            delete_targets = [(show_name, file_path) for _, show_name, _, file_path in selected_entries]
        else:
            if not self._check_main_file_path():
                return
            delete_targets = [(self.show_name or "", self.file_main_open_path)]

        if not delete_targets:
            return

        file_paths = [file_path for _, file_path in delete_targets]
        folder_to_show_names: dict[Path, list[str]] = {}
        for show_name, file_path in delete_targets:
            folder_path = Path(split_path(file_path)[0])
            folder_to_show_names.setdefault(folder_path, [])
            if show_name:
                folder_to_show_names[folder_path].append(show_name)

        folder_paths = sorted(folder_to_show_names, key=lambda p: len(p.parts), reverse=True)
        plan = self._get_file_controller().build_plan(
            FileOperationKind.DELETE_FOLDERS,
            folder_paths,
            source_count=len(file_paths),
            deduplicate=True,
        )
        if not self._get_file_controller().confirm_plan(plan, accept_text="确认删除文件和文件夹"):
            return

        signal_qt.show_log_text(" 🗑 开始删除文件夹")
        signal_qt.show_log_text(f" 📦 本次待删除文件夹数: {len(folder_paths)}")

        ordered_targets = {folder_path: folder_to_show_names[folder_path] for folder_path in folder_paths}
        success_folder_count, success_show_names, failure_details, failed_targets = (
            self._get_file_controller().delete_folders(ordered_targets)
        )

        if success_show_names:
            self._remove_deleted_result_items(success_show_names)

        fail_count = len(failure_details)
        signal_qt.show_log_text(f" 🎉 删除文件夹完成：成功 {success_folder_count} 个，失败 {fail_count} 个")
        if fail_count:
            self.show_scrape_info(
                f"💡 文件夹删除完成，成功 {success_folder_count} 个，失败 {fail_count} 个！{get_current_time()}"
            )
            self._show_action_failure_feedback(
                "删除文件夹",
                success_folder_count,
                failure_details,
                retry_callback=lambda: self._get_file_controller().retry_delete_folders(failed_targets),
            )
        elif success_folder_count == 1:
            self.show_scrape_info(f"💡 已删除文件夹！{get_current_time()}")
        else:
            self.show_scrape_info(f"💡 已删除 {success_folder_count} 个文件夹！{get_current_time()}")

    def main_make_symlink_click(self):
        """
        主界面在指定位置创建软链接
        """
        self._create_links_for_selected_files("soft")

    def main_make_symlink_in_dir_click(self):
        """
        主界面在指定位置创建软链接，并按文件名创建目录
        """
        self._create_links_for_selected_files("soft", group_in_named_dir=True)

    def main_make_hardlink_click(self):
        """
        主界面在指定位置创建硬链接
        """
        self._create_links_for_selected_files("hard")

    def main_make_hardlink_in_dir_click(self):
        """
        主界面在指定位置创建硬链接，并按文件名创建目录
        """
        self._create_links_for_selected_files("hard", group_in_named_dir=True)

    def _pic_main_clicked(self):
        """
        主界面点图片
        """
        file_info = None if self.show_data is None else self.show_data.file_info
        cutwindow = self._get_cutwindow()
        cutwindow.showimage(self.img_path, file_info)
        cutwindow.show()

    def checkBox_cover_clicked(self):
        if not self.Ui.checkBox_cover.isChecked():
            self.Ui.label_poster.setText("封面图")
            self.Ui.label_thumb.setText("缩略图")
            self.Ui.label_poster.resize(156, 220)
            self.Ui.label_thumb.resize(328, 220)
            self.Ui.label_poster_size.setText("")
            self.Ui.label_thumb_size.setText("")
        else:
            self.set_main_info(self.show_data)

    def update_amazon_strict_pic_verify_state(self, *_args):
        amazon_enabled = self.Ui.checkBox_amazon_big_pic.isChecked()
        self.Ui.checkBox_amazon_skip_poster_size_precheck.setEnabled(amazon_enabled)
        self.Ui.label_amazon_skip_poster_size_precheck.setEnabled(amazon_enabled)
        self.Ui.checkBox_amazon_strict_pic_verify.setEnabled(amazon_enabled)
        self.Ui.label_amazon_strict_pic_verify.setEnabled(amazon_enabled)
        if not amazon_enabled:
            self.Ui.checkBox_amazon_skip_poster_size_precheck.setChecked(False)
            self.Ui.checkBox_amazon_strict_pic_verify.setChecked(False)

    def update_field_priority_try_all_images_state(self, *_args):
        self.Ui.checkBox_field_priority_try_all_images.setEnabled(self.Ui.radioButton_scrape_info.isChecked())

    def _connect_nfo_editor_dirty_signals(self) -> None:
        self._get_nfo_controller().connect_dirty_signals()

    def _mark_nfo_editor_field_dirty(self, field_name: str) -> None:
        self._get_nfo_controller().mark_field_dirty(field_name)

    def _read_nfo_editor_field(self, field_name: str) -> str:
        return self._get_nfo_controller().read_field(field_name)

    def _set_nfo_editor_field(self, field_name: str, value: str, *, mixed: bool = False) -> None:
        self._get_nfo_controller().set_field(field_name, value, mixed=mixed)

    @staticmethod
    def _nfo_data_field_value(data: CrawlersResult, field_name: str) -> str:
        return NfoController.data_field_value(data, field_name)
