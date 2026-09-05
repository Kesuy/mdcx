from __future__ import annotations

import copy
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from mdcx.base.file import save_success_list
from mdcx.config.enums import NfoInclude
from mdcx.config.extend import get_movie_path_setting
from mdcx.config.manager import manager
from mdcx.core.media_reorganization import (
    MediaReorganizationError,
    reorganize_scraped_media,
    update_runtime_paths_after_reorganization,
)
from mdcx.core.nfo import write_nfo
from mdcx.models.flags import Flags
from mdcx.models.types import CrawlersResult, ShowData
from mdcx.signals import signal_qt
from mdcx.utils import executor, get_current_time

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


NFO_EDITOR_WIDGETS: dict[str, tuple[str, bool]] = {
    "number": ("lineEdit_nfo_number", False),
    "actor": ("lineEdit_nfo_actor", False),
    "year": ("lineEdit_nfo_year", False),
    "title": ("lineEdit_nfo_title", False),
    "originaltitle": ("lineEdit_nfo_originaltitle", False),
    "outline": ("textEdit_nfo_outline", True),
    "originalplot": ("textEdit_nfo_originalplot", True),
    "tag": ("textEdit_nfo_tag", True),
    "release": ("lineEdit_nfo_release", False),
    "runtime": ("lineEdit_nfo_runtime", False),
    "score": ("lineEdit_nfo_score", False),
    "wanted": ("lineEdit_nfo_wanted", False),
    "director": ("lineEdit_nfo_director", False),
    "series": ("lineEdit_nfo_series", False),
    "studio": ("lineEdit_nfo_studio", False),
    "publisher": ("lineEdit_nfo_publisher", False),
    "poster": ("lineEdit_nfo_poster", False),
    "thumb": ("lineEdit_nfo_cover", False),
    "trailer": ("lineEdit_nfo_trailer", False),
}
NFO_MIXED_VALUE_PLACEHOLDER = "（多个值，保持为空则不修改）"
NFO_FIELD_LABELS = {
    "number": "番号",
    "actor": "演员",
    "year": "年份",
    "title": "标题",
    "originaltitle": "原始标题",
    "outline": "简介",
    "originalplot": "原始简介",
    "tag": "标签",
    "release": "发行日期",
    "runtime": "时长",
    "score": "评分",
    "wanted": "收藏",
    "director": "导演",
    "series": "系列",
    "studio": "制作商",
    "publisher": "发行商",
    "poster": "封面地址",
    "thumb": "缩略图地址",
    "trailer": "预告片地址",
}


@dataclass(frozen=True, slots=True)
class NfoFieldChange:
    field: str
    label: str
    old_value: str
    new_value: str


def build_nfo_changes(data: CrawlersResult, patch: dict[str, str]) -> tuple[NfoFieldChange, ...]:
    changes = []
    for field_name, new_value in patch.items():
        old_value = NfoController.data_field_value(data, field_name)
        if old_value == new_value:
            continue
        changes.append(
            NfoFieldChange(
                field_name,
                NFO_FIELD_LABELS.get(field_name, field_name),
                old_value,
                new_value,
            )
        )
    return tuple(changes)


class NfoController:
    """Own the NFO editor state, persistence and post-save reorganization workflow."""

    def __init__(self, window: MyMAinWindow) -> None:
        self.window = window

    def connect_dirty_signals(self) -> None:
        for field_name, (widget_name, is_plain_text) in NFO_EDITOR_WIDGETS.items():
            widget = getattr(self.window.Ui, widget_name)
            changed_signal = widget.textChanged if is_plain_text else widget.textEdited
            changed_signal.connect(lambda *_args, current_field=field_name: self.mark_field_dirty(current_field))

    def mark_field_dirty(self, field_name: str) -> None:
        window = self.window
        if not window._nfo_editor_loading and window._nfo_batch_show_names:
            window._nfo_dirty_fields.add(field_name)

    def read_field(self, field_name: str) -> str:
        widget_name, is_plain_text = NFO_EDITOR_WIDGETS[field_name]
        widget = getattr(self.window.Ui, widget_name)
        return widget.toPlainText() if is_plain_text else widget.text()

    def set_field(self, field_name: str, value: str, *, mixed: bool = False) -> None:
        widget_name, is_plain_text = NFO_EDITOR_WIDGETS[field_name]
        widget = getattr(self.window.Ui, widget_name)
        widget.setPlaceholderText(NFO_MIXED_VALUE_PLACEHOLDER if mixed else "")
        if is_plain_text:
            widget.setPlainText(value)
        else:
            widget.setText(value)

    @staticmethod
    def data_field_value(data: CrawlersResult, field_name: str) -> str:
        if field_name == "actor" and data.all_actor and NfoInclude.ACTOR_ALL in manager.config.nfo_include_new:
            return data.all_actor
        return str(getattr(data, field_name))

    @staticmethod
    def apply_patch(data: CrawlersResult, patch: dict[str, str]) -> None:
        for field_name, value in patch.items():
            if field_name == "actor" and NfoInclude.ACTOR_ALL in manager.config.nfo_include_new:
                data.all_actor = value
            setattr(data, field_name, value)

    @staticmethod
    def _short_value(value: str, limit: int = 120) -> str:
        value = value.replace("\r", " ").replace("\n", " ").strip() or "（空）"
        return value if len(value) <= limit else value[: limit - 1] + "…"

    def confirm_changes(self, changes: tuple[NfoFieldChange, ...], *, item_count: int = 1) -> bool:
        if not changes:
            self.window.Ui.label_save_tips.setText(f"没有检测到内容变化! {get_current_time()}")
            return False
        if not vars(self.window).get("_nfo_diff_confirmation_enabled", False):
            return True

        preview = "\n".join(
            f"{change.label}：{self._short_value(change.old_value)} → {self._short_value(change.new_value)}"
            for change in changes[:8]
        )
        if len(changes) > 8:
            preview += f"\n... 其余 {len(changes) - 8} 个字段请展开详情"
        details = "\n\n".join(
            f"{change.label}\n旧值：{change.old_value or '（空）'}\n新值：{change.new_value or '（空）'}"
            for change in changes
        )
        title = "批量保存 NFO" if item_count > 1 else "保存 NFO"
        box = QMessageBox(QMessageBox.Icon.Question, title, f"保存前差异预览（{item_count} 项）", parent=self.window)
        box.setInformativeText(preview)
        box.setDetailedText(details)
        box.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
        box.button(QMessageBox.StandardButton.Save).setText("确认保存")
        box.button(QMessageBox.StandardButton.Cancel).setText("返回修改")
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return box.exec() == QMessageBox.StandardButton.Save

    def show(self, selected_show_data: list[ShowData] | None = None) -> None:
        window = self.window
        try:
            if selected_show_data is None:
                if not window.show_name:
                    return
                selected_show_data = [window.json_array[window.show_name]]
            if not selected_show_data:
                return

            window._nfo_editor_loading = True
            window._nfo_dirty_fields.clear()
            is_batch = len(selected_show_data) > 1
            window._nfo_batch_show_names = [entry.show_name for entry in selected_show_data] if is_batch else []
            window.now_show_name = None if is_batch else selected_show_data[0].show_name
            if is_batch:
                window.Ui.label_nfo.setText(
                    f"已选择 {len(selected_show_data)} 项 · 仅保存修改字段 · 保存后按当前规则自动整理"
                )
            else:
                window.Ui.label_nfo.setText(str(selected_show_data[0].file_info.file_path))

            for field_name in NFO_EDITOR_WIDGETS:
                values = [self.data_field_value(entry.data, field_name) for entry in selected_show_data]
                has_mixed_values = any(value != values[0] for value in values[1:])
                self.set_field(field_name, "" if has_mixed_values else values[0], mixed=has_mixed_values)

            window.Ui.comboBox_nfo.setEnabled(not is_batch)
            window.Ui.comboBox_nfo.setToolTip("批量模式下国家由各项目番号和类型保留" if is_batch else "")
            json_data = selected_show_data[0].data
            all_items = [window.Ui.comboBox_nfo.itemText(i) for i in range(window.Ui.comboBox_nfo.count())]
            if json_data.country in all_items:
                window.Ui.comboBox_nfo.setCurrentIndex(all_items.index(json_data.country))
        except Exception:
            if not signal_qt.stop:
                signal_qt.show_traceback_log(traceback.format_exc())
        finally:
            window._nfo_editor_loading = False

    def save_batch(self) -> None:
        window = self.window
        show_entries = [window.json_array[name] for name in window._nfo_batch_show_names if name in window.json_array]
        if len(show_entries) != len(window._nfo_batch_show_names):
            window.Ui.label_save_tips.setText(f"保存失败，部分所选项目已失效! {get_current_time()}")
            return
        if not window._nfo_dirty_fields:
            window.Ui.label_save_tips.setText(f"没有修改任何字段! {get_current_time()}")
            return

        patch = {field_name: self.read_field(field_name) for field_name in window._nfo_dirty_fields}
        preview_changes = tuple(
            NfoFieldChange(
                field_name,
                NFO_FIELD_LABELS.get(field_name, field_name),
                "（各项目当前值）",
                value,
            )
            for field_name, value in patch.items()
        )
        if not self.confirm_changes(preview_changes, item_count=len(show_entries)):
            return
        selected_ids = {id(entry) for entry in show_entries}
        processed_ids: set[int] = set()
        success_count = 0
        failure_count = 0
        for entry in show_entries:
            if id(entry) in processed_ids:
                continue
            original_data = copy.deepcopy(entry.data)
            self.apply_patch(entry.data, patch)
            try:
                saved, affected_entries = self.save_entry(entry, original_data)
            except Exception:
                saved = False
                affected_entries = [entry]
                if not signal_qt.stop:
                    signal_qt.show_traceback_log(traceback.format_exc())
            affected_selected_ids = {id(item) for item in affected_entries} & selected_ids
            processed_ids.update(affected_selected_ids)
            if saved:
                success_count += len(affected_selected_ids)
            else:
                failure_count += len(affected_selected_ids)

        changed_fields = "、".join(window._nfo_dirty_fields)
        window._nfo_dirty_fields.clear()
        window.Ui.label_nfo.setText(
            f"批量编辑完成 · 成功 {success_count} 项 · 失败 {failure_count} 项 · 已按当前规则自动整理"
        )
        window.Ui.label_save_tips.setText(
            f"批量保存完成：成功 {success_count}，失败 {failure_count}! {get_current_time()}"
        )
        signal_qt.show_log_text(
            f"\n 🍀 批量更新 NFO 完成：成功 {success_count}，失败 {failure_count}\n    修改字段：{changed_fields}"
        )

    def find_related_cd_entries(self, show_data: ShowData, old_number: str) -> list[ShowData]:
        file_info = show_data.file_info
        if not file_info.cd_part:
            return []
        current_cd_part = str(file_info.cd_part)
        current_base = file_info.file_path.stem
        if current_base.casefold().endswith(current_cd_part.casefold()):
            current_base = current_base[: -len(current_cd_part)]

        def is_same_cd_group(entry: ShowData) -> bool:
            entry_cd_part = str(entry.file_info.cd_part or "")
            entry_base = entry.file_info.file_path.stem
            if entry_cd_part and entry_base.casefold().endswith(entry_cd_part.casefold()):
                entry_base = entry_base[: -len(entry_cd_part)]
            return entry_base.casefold() == current_base.casefold()

        return [
            entry
            for entry in self.window.json_array.values()
            if entry is not show_data
            and entry.file_info.cd_part
            and entry.file_info.file_path.parent == file_info.file_path.parent
            and entry.data.number == old_number
            and is_same_cd_group(entry)
        ]

    def save_entry(
        self,
        show_data: ShowData,
        original_current_data: CrawlersResult,
    ) -> tuple[bool, list[ShowData]]:
        window = self.window
        json_data = show_data.data
        file_info = show_data.file_info
        old_number = original_current_data.number
        nfo_path = file_info.file_path.with_suffix(".nfo")
        nfo_folder = nfo_path.parent
        related_cd_entries = self.find_related_cd_entries(show_data, old_number)
        affected_entries = [show_data, *related_cd_entries]
        data_backups = [(show_data, original_current_data)] + [
            (entry, copy.deepcopy(entry.data)) for entry in related_cd_entries
        ]
        nfo_paths = [nfo_path] + [entry.file_info.file_path.with_suffix(".nfo") for entry in related_cd_entries]
        nfo_backups = {path: (path.exists(), path.read_bytes() if path.exists() else b"") for path in nfo_paths}
        nfo_saved = executor.run(write_nfo(file_info, json_data, nfo_path, nfo_folder, update=True))
        if nfo_saved:
            for related_entry in related_cd_entries:
                related_entry.data = copy.deepcopy(json_data)
                related_nfo_path = related_entry.file_info.file_path.with_suffix(".nfo")
                if not executor.run(
                    write_nfo(
                        related_entry.file_info,
                        related_entry.data,
                        related_nfo_path,
                        related_nfo_path.parent,
                        update=True,
                    )
                ):
                    nfo_saved = False
                    break
        if not nfo_saved:
            for path, (existed, content) in nfo_backups.items():
                if existed:
                    path.write_bytes(content)
                elif path.exists():
                    path.unlink()
            for entry, data_backup in data_backups:
                entry.data = data_backup
            window.Ui.label_save_tips.setText(f"保存失败，已恢复原信息! {get_current_time()}")
            return False, affected_entries

        old_file_path = file_info.file_path
        Flags.file_done_dic.pop(old_number, None)
        Flags.file_done_dic.pop(json_data.number, None)
        try:
            success_folder = get_movie_path_setting(old_file_path).success_folder
            reorganized = executor.run(reorganize_scraped_media(file_info, json_data, show_data.other, success_folder))
            if reorganized.moved:
                path_mapping = dict(reorganized.path_mapping) or {old_file_path: reorganized.new_file_path}
                for related_show_data in window.json_array.values():
                    related_old_path = related_show_data.file_info.file_path
                    related_new_path = path_mapping.get(related_old_path)
                    if related_new_path is None or related_show_data is show_data:
                        continue
                    update_runtime_paths_after_reorganization(
                        related_show_data.file_info,
                        related_show_data.other,
                        related_old_path,
                        related_new_path,
                    )
                for source_path, target_path in path_mapping.items():
                    original_sources = Flags.file_new_path_dic.pop(source_path, None)
                    if original_sources is not None:
                        Flags.file_new_path_dic[target_path] = original_sources
                    if source_path in Flags.success_list:
                        Flags.success_list.discard(source_path)
                        Flags.success_list.add(target_path)
                executor.run(save_success_list())
                window.Ui.label_nfo.setText(str(reorganized.new_file_path))
                window.Ui.label_save_tips.setText(f"已保存并整理! {get_current_time()}")
                signal_qt.show_log_text(
                    f"\n 🍀 编辑信息后自动整理完成\n    原路径: {old_file_path}\n    新路径: {reorganized.new_file_path}"
                )
            else:
                window.Ui.label_save_tips.setText(f"已保存! {get_current_time()}")
        except MediaReorganizationError as error:
            incomplete_mapping = dict(error.path_mapping)
            for related_show_data in window.json_array.values():
                related_old_path = related_show_data.file_info.file_path
                related_actual_path = incomplete_mapping.get(related_old_path)
                if related_actual_path is None or related_show_data is show_data:
                    continue
                update_runtime_paths_after_reorganization(
                    related_show_data.file_info,
                    related_show_data.other,
                    related_old_path,
                    related_actual_path,
                )
            for source_path, actual_path in incomplete_mapping.items():
                original_sources = Flags.file_new_path_dic.pop(source_path, None)
                if original_sources is not None:
                    Flags.file_new_path_dic[actual_path] = original_sources
                if source_path in Flags.success_list:
                    Flags.success_list.discard(source_path)
                    Flags.success_list.add(actual_path)
            actual_file_path = file_info.file_path
            if actual_file_path != old_file_path and old_file_path not in incomplete_mapping:
                original_sources = Flags.file_new_path_dic.pop(old_file_path, None)
                if original_sources is not None:
                    Flags.file_new_path_dic[actual_file_path] = original_sources
                if old_file_path in Flags.success_list:
                    Flags.success_list.discard(old_file_path)
                    Flags.success_list.add(actual_file_path)
            if incomplete_mapping or actual_file_path != old_file_path:
                executor.run(save_success_list())
                window.Ui.label_nfo.setText(str(actual_file_path))
            window.Ui.label_save_tips.setText(f"信息已保存，自动整理失败! {get_current_time()}")
            signal_qt.show_log_text(f"\n 🟡 信息已保存，但无法按当前设置自动整理：{error}")
        window.set_main_info(show_data)
        return True, affected_entries

    def save(self) -> bool:
        window = self.window
        try:
            if vars(window).get("_nfo_batch_show_names", []):
                self.save_batch()
                return True
            if window.now_show_name is None:
                return False
            show_data = window.json_array[window.now_show_name]
            json_data = show_data.data
            original_current_data = copy.deepcopy(json_data)
            patch = {field_name: self.read_field(field_name) for field_name in NFO_EDITOR_WIDGETS}
            changes = build_nfo_changes(json_data, patch)
            if not changes:
                self.window.Ui.label_save_tips.setText(f"没有检测到内容变化! {get_current_time()}")
                return False
            self.apply_patch(json_data, patch)
            saved, _affected_entries = self.save_entry(show_data, original_current_data)
            return saved
        except Exception:
            if not signal_qt.stop:
                signal_qt.show_traceback_log(traceback.format_exc())
            return False
