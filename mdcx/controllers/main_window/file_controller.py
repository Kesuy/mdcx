from __future__ import annotations

import re
import shutil
import traceback
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from mdcx.base.file import save_success_list
from mdcx.config.extend import get_movie_path_setting
from mdcx.config.manager import manager
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt
from mdcx.utils import executor, get_current_time
from mdcx.utils.file import (
    create_hardlink_sync,
    create_symlink_sync,
    delete_file_sync,
    resolve_link_source_sync,
    resolve_success_record_source_sync,
)

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


LINK_DIR_INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
WINDOWS_RESERVED_DIR_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
DEFAULT_LINK_DIR_NAME = "unnamed"


class FileOperationKind(StrEnum):
    DELETE_FILES = "删除文件"
    DELETE_FOLDERS = "删除文件夹"
    CREATE_SYMLINKS = "创建软链接"
    CREATE_HARDLINKS = "创建硬链接"


class FileFailureCategory(StrEnum):
    PERMISSION = "权限不足"
    MISSING = "文件不存在"
    CONFLICT = "目标冲突"
    CROSS_DEVICE = "跨磁盘限制"
    BUSY = "文件占用"
    INVALID_NAME = "名称无效"
    UNKNOWN = "其他错误"


@dataclass(frozen=True, slots=True)
class FileOperationPlan:
    kind: FileOperationKind
    targets: tuple[Path, ...]
    source_count: int

    @property
    def target_count(self) -> int:
        return len(self.targets)

    def preview(self, limit: int = 8) -> str:
        preview = "\n".join(str(path) for path in self.targets[:limit])
        if len(self.targets) > limit:
            preview += f"\n... 其余 {len(self.targets) - limit} 项省略"
        return preview

    def confirmation_text(self) -> str:
        source_info = ""
        if self.source_count != self.target_count:
            source_info = f"（来源于 {self.source_count} 个选中项）"
        return (
            "操作预演（尚未修改文件）\n\n"
            f"动作：{self.kind.value}\n"
            f"目标：{self.target_count} 项{source_info}\n\n"
            f"{self.preview()}\n\n"
            "请核对以上路径。继续后将立即执行，且无法通过软件撤销。"
        )


@dataclass(frozen=True, slots=True)
class FileFailure:
    category: FileFailureCategory
    reason: str
    retryable: bool
    suggestion: str


def _clean_error_lines(error_text: str) -> tuple[list[str], str]:
    lines = [line.strip() for line in str(error_text).splitlines() if line.strip()]
    return lines, "\n".join(lines).lower()


def classify_file_failure(error_text: str) -> FileFailure:
    if not error_text:
        return FileFailure(FileFailureCategory.UNKNOWN, "未知错误", True, "请重试并查看日志")

    lines, full_text = _clean_error_lines(error_text)
    if "symbolic link privilege not held" in full_text or "winerror 1314" in full_text:
        return FileFailure(
            FileFailureCategory.PERMISSION,
            "当前没有创建软链接权限，请尝试以管理员身份运行或开启开发者模式",
            True,
            "开启 Windows 开发者模式，或以管理员身份重新运行",
        )
    if (
        "winerror 17" in full_text
        or "different disk drive" in full_text
        or "cross-device link" in full_text
        or "not same device" in full_text
    ):
        return FileFailure(
            FileFailureCategory.CROSS_DEVICE,
            "硬链接要求源文件与目标路径位于同一磁盘，请改用软链接",
            False,
            "改用软链接，或选择与源文件相同的磁盘",
        )
    if "目标已存在:" in str(error_text):
        reason = next((line for line in lines if "目标已存在:" in line), lines[-1])
        return FileFailure(FileFailureCategory.CONFLICT, reason, True, "更换目标位置或删除冲突项后重试")
    if "permissionerror:" in full_text or "access is denied" in full_text or "拒绝访问" in full_text:
        reason = next(
            (line.split("PermissionError:", 1)[-1].strip() for line in lines if "PermissionError:" in line),
            lines[-1],
        )
        return FileFailure(FileFailureCategory.PERMISSION, reason, True, "关闭占用程序并检查目录权限后重试")
    if "filenotfounderror:" in full_text or "no such file" in full_text or "找不到" in full_text:
        reason = next(
            (line.split("FileNotFoundError:", 1)[-1].strip() for line in lines if "FileNotFoundError:" in line),
            lines[-1],
        )
        return FileFailure(FileFailureCategory.MISSING, reason, False, "刷新结果列表，移除已失效项目")
    if "being used by another process" in full_text or "文件被占用" in full_text or "sharing violation" in full_text:
        return FileFailure(FileFailureCategory.BUSY, lines[-1], True, "关闭播放器、媒体服务器或资源管理器预览后重试")
    if "invalid name" in full_text or "filename syntax" in full_text or "文件名、目录名或卷标语法不正确" in full_text:
        return FileFailure(FileFailureCategory.INVALID_NAME, lines[-1], False, "修改文件名或目标目录名称")

    for line in lines:
        if line.startswith("错误:"):
            return FileFailure(
                FileFailureCategory.UNKNOWN, line.removeprefix("错误:").strip(), True, "请重试并查看日志"
            )
    for line in reversed(lines):
        if "OSError:" in line:
            return FileFailure(
                FileFailureCategory.UNKNOWN,
                line.split("OSError:", 1)[1].strip(),
                True,
                "请重试并查看日志",
            )
    return FileFailure(FileFailureCategory.UNKNOWN, lines[-1], True, "请重试并查看日志")


class FileController:
    """Build and present side-effect-free plans before file mutations."""

    def __init__(self, window: MyMAinWindow) -> None:
        self.window = window

    @staticmethod
    def build_plan(
        kind: FileOperationKind,
        paths: Iterable[Path],
        *,
        source_count: int | None = None,
        deduplicate: bool = False,
    ) -> FileOperationPlan:
        path_list = [Path(path) for path in paths]
        original_count = len(path_list) if source_count is None else source_count
        if deduplicate:
            path_list = list(dict.fromkeys(path_list))
        return FileOperationPlan(kind, tuple(path_list), original_count)

    def confirm_plan(self, plan: FileOperationPlan, *, accept_text: str) -> bool:
        box = QMessageBox(QMessageBox.Icon.Warning, plan.kind.value, plan.confirmation_text(), parent=self.window)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText(accept_text)
        box.button(QMessageBox.StandardButton.No).setText("取消")
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes

    def select_link_output_dir(self, link_name: str) -> Path | None:
        window = self.window
        selected_dir = QFileDialog.getExistingDirectory(
            window,
            f"选择{link_name}目标目录",
            str(get_movie_path_setting().softlink_path),
            options=window.options | QFileDialog.Option.ShowDirsOnly,
        )
        return Path(selected_dir) if selected_dir else None

    def confirm_record_link_paths(self, link_name: str) -> bool | None:
        box = QMessageBox(
            QMessageBox.Icon.Question,
            f"创建{link_name}",
            f"是否将本次成功创建的{link_name}路径写入程序的刮削成功列表？",
            parent=self.window,
        )
        box.setInformativeText("已存在的同源链接会自动去重；取消则中止本次创建。")
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        box.button(QMessageBox.StandardButton.Yes).setText("写入并继续")
        box.button(QMessageBox.StandardButton.No).setText("仅创建")
        box.button(QMessageBox.StandardButton.Cancel).setText("取消")
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        reply = box.exec()
        if reply == QMessageBox.StandardButton.Cancel:
            return None
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def get_link_dir_name_max() -> int:
        folder_name_max = int(manager.config.folder_name_max)
        return folder_name_max if 0 < folder_name_max <= 255 else 60

    def fit_link_dir_name_length(self, dir_name: str, suffix: str = "") -> str:
        max_length = self.get_link_dir_name_max()
        if len(dir_name) + len(suffix) <= max_length:
            return dir_name + suffix
        base_length = max(max_length - len(suffix), 1)
        trimmed = dir_name[:base_length].rstrip(". ").rstrip()
        if not trimmed:
            trimmed = DEFAULT_LINK_DIR_NAME[:base_length].rstrip(". ").rstrip() or DEFAULT_LINK_DIR_NAME[:1]
        return trimmed + suffix

    @staticmethod
    def is_windows_reserved_dir_name(dir_name: str) -> bool:
        return dir_name.rstrip(". ").upper() in WINDOWS_RESERVED_DIR_NAMES

    def sanitize_link_dir_name(self, raw_name: str) -> tuple[str, list[str]]:
        sanitized = LINK_DIR_INVALID_CHARS_RE.sub("_", raw_name)
        sanitized = re.sub(r"\s+", " ", sanitized)
        sanitized = re.sub(r"_+", "_", sanitized)
        sanitized = sanitized.strip().strip(". ").rstrip(". ").strip()
        notes: list[str] = []
        if not sanitized or not sanitized.strip("._- "):
            sanitized = DEFAULT_LINK_DIR_NAME
            notes.append(f"链接目录名清洗后为空，已回退为默认目录名: {raw_name} -> {sanitized}")
        elif sanitized != raw_name:
            notes.append(f"链接目录名已清洗: {raw_name} -> {sanitized}")
        if self.is_windows_reserved_dir_name(sanitized):
            original_name = sanitized
            sanitized = f"{sanitized}_"
            notes.append(f"链接目录名命中 Windows 保留名，已自动调整: {original_name} -> {sanitized}")
        fitted_name = self.fit_link_dir_name_length(sanitized)
        if fitted_name != sanitized:
            notes.append(f"链接目录名过长，已按最大长度截断: {sanitized} -> {fitted_name}")
        return fitted_name, notes

    @staticmethod
    def can_reuse_link_target_dir(target_dir: Path, file_name: str) -> bool:
        if not target_dir.exists():
            return True
        if not target_dir.is_dir():
            return False
        target_file = target_dir / file_name
        if target_file.exists() or target_file.is_symlink():
            return True
        try:
            return not any(target_dir.iterdir())
        except Exception:
            return False

    def get_available_link_target_dir(self, output_dir: Path, dir_name: str, file_name: str) -> tuple[Path, str]:
        candidate_dir = output_dir / dir_name
        if self.can_reuse_link_target_dir(candidate_dir, file_name):
            return candidate_dir, ""
        suffix_index = 2
        while True:
            candidate_name = self.fit_link_dir_name_length(dir_name, f"_{suffix_index}")
            candidate_dir = output_dir / candidate_name
            if self.can_reuse_link_target_dir(candidate_dir, file_name):
                return candidate_dir, candidate_name
            suffix_index += 1

    def build_link_target_path(
        self,
        source_path: Path,
        output_dir: Path,
        display_path: Path | None = None,
        group_in_named_dir: bool = False,
    ) -> tuple[Path, list[str]]:
        file_name = display_path.name if display_path is not None else source_path.name
        if not group_in_named_dir:
            return output_dir / file_name, []
        raw_dir_name = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        dir_name, notes = self.sanitize_link_dir_name(raw_dir_name or file_name)
        target_dir, collision_note = self.get_available_link_target_dir(output_dir, dir_name, file_name)
        if collision_note:
            notes.append(f"链接目录名已自动避让冲突: {dir_name} -> {target_dir.name}")
        return target_dir / file_name, notes

    @staticmethod
    def prepare_link_target_dir(target_path: Path, group_in_named_dir: bool) -> tuple[bool, str, bool]:
        if not group_in_named_dir:
            return True, "", False
        target_dir = target_path.parent
        if target_dir == target_path:
            return False, "目标目录无效", False
        if target_dir.exists():
            if target_dir.is_dir():
                return True, "", False
            return False, f"目标目录已存在同名文件: {target_dir}", False
        try:
            target_dir.mkdir(parents=True, exist_ok=False)
            return True, "", True
        except Exception:
            return False, traceback.format_exc(), False

    @staticmethod
    def cleanup_empty_link_target_dir(target_path: Path, created_dir: bool) -> None:
        if not created_dir:
            return
        target_dir = target_path.parent
        try:
            if target_dir.exists() and target_dir.is_dir() and not any(target_dir.iterdir()):
                target_dir.rmdir()
                signal_qt.show_log_text(f" ↩ 创建失败，已回滚空目录: {target_dir}")
        except Exception:
            failure = classify_file_failure(traceback.format_exc())
            signal_qt.show_log_text(f" ⚠ 回滚空目录失败: {target_dir}\n    原因: {failure.reason}")

    def create_links(
        self,
        link_type: Literal["soft", "hard"],
        group_in_named_dir: bool = False,
        *,
        link_targets: list[tuple[str, Path]] | None = None,
        output_dir: Path | None = None,
        should_record_success: bool | None = None,
        show_plan: bool = True,
    ) -> None:
        window = self.window
        if link_targets is None:
            selected_entries = window._get_selected_entries()
            if selected_entries:
                link_targets = [(show_name, file_path) for _, show_name, _, file_path in selected_entries]
            else:
                if not window._check_main_file_path():
                    return
                link_targets = [(window.show_name or "", window.file_main_open_path)]
        if not link_targets:
            return

        link_name = "软链接" if link_type == "soft" else "硬链接"
        if group_in_named_dir:
            link_name = f"{link_name}（按文件名建目录）"
        if output_dir is None:
            output_dir = self.select_link_output_dir(link_name)
        if output_dir is None:
            return

        if show_plan:
            planned_paths = [
                self.build_link_target_path(path, output_dir, path, group_in_named_dir)[0]
                for _show_name, path in link_targets
            ]
            kind = FileOperationKind.CREATE_SYMLINKS if link_type == "soft" else FileOperationKind.CREATE_HARDLINKS
            plan = self.build_plan(kind, planned_paths, source_count=len(link_targets))
            if not self.confirm_plan(plan, accept_text=f"确认创建{link_name}"):
                return
        if should_record_success is None:
            should_record_success = self.confirm_record_link_paths(link_name)
        if should_record_success is None:
            return

        signal_qt.show_log_text(f" 🔗 开始创建{link_name}")
        signal_qt.show_log_text(f" 📁 目标目录: {output_dir}")
        signal_qt.show_log_text(f" 📝 成功列表写入: {'是' if should_record_success else '否'}")

        success_count = 0
        skipped_count = 0
        success_paths_to_record: set[Path] = set()
        failure_details: list[tuple[Path, str]] = []
        failed_targets: list[tuple[str, Path]] = []
        for show_name, file_path in link_targets:
            success, source_path, error_info = resolve_link_source_sync(file_path)
            if not success:
                failure = classify_file_failure(error_info)
                failure_details.append((file_path, error_info))
                failed_targets.append((show_name, file_path))
                signal_qt.show_log_text(
                    f" ❌ {link_name}失败: {file_path}\n"
                    f"    类别: {failure.category.value}\n"
                    f"    原因: {failure.reason}\n"
                    f"    建议: {failure.suggestion}"
                )
                continue

            target_path, target_notes = self.build_link_target_path(
                source_path, output_dir, file_path, group_in_named_dir
            )
            for note in target_notes:
                signal_qt.show_log_text(f" ℹ {note}")
            ok, dir_error, created_dir = self.prepare_link_target_dir(target_path, group_in_named_dir)
            if not ok:
                failure = classify_file_failure(dir_error)
                failure_details.append((target_path, dir_error))
                failed_targets.append((show_name, file_path))
                signal_qt.show_log_text(
                    f" ❌ {link_name}失败: {target_path}\n"
                    f"    源文件: {source_path}\n"
                    f"    类别: {failure.category.value}\n"
                    f"    原因: {failure.reason}"
                )
                continue

            create_link = create_symlink_sync if link_type == "soft" else create_hardlink_sync
            result, info = create_link(source_path, target_path)
            if not result:
                self.cleanup_empty_link_target_dir(target_path, created_dir)
                failure = classify_file_failure(info)
                failure_details.append((target_path, info))
                failed_targets.append((show_name, file_path))
                signal_qt.show_log_text(
                    f" ❌ {link_name}失败: {target_path}\n"
                    f"    源文件: {source_path}\n"
                    f"    类别: {failure.category.value}\n"
                    f"    原因: {failure.reason}\n"
                    f"    建议: {failure.suggestion}"
                )
                continue

            record_success, success_record_path, record_info = resolve_success_record_source_sync(file_path)
            if not record_success:
                success_record_path = file_path
                record_info = f"解析成功列表源路径失败，已回退记录当前路径: {classify_file_failure(record_info).reason}"
            if should_record_success:
                success_paths_to_record.add(success_record_path)
            if record_info:
                signal_qt.show_log_text(f" ℹ 成功列表记录路径: {success_record_path}\n    说明: {record_info}")
            if "已存在同源" in info:
                skipped_count += 1
                signal_qt.show_log_text(f" ⏭ 已跳过{link_name}: {target_path}\n    原因: {info}")
            else:
                success_count += 1
                signal_qt.show_log_text(f" ✅ 已创建{link_name}: {target_path}\n    源文件: {source_path}")

        if should_record_success and success_paths_to_record:
            Flags.success_list.update(success_paths_to_record)
            executor.run(save_success_list())
            signal_qt.show_log_text(f" 💾 已写入成功列表 {len(success_paths_to_record)} 项")

        fail_count = len(failure_details)
        signal_qt.show_log_text(
            f" 🎉 创建{link_name}完成：成功 {success_count} 个，跳过 {skipped_count} 个，失败 {fail_count} 个"
        )
        if fail_count:
            signal_qt.show_scrape_info(
                f"💡 创建{link_name}完成，成功 {success_count} 个，跳过 {skipped_count} 个，"
                f"失败 {fail_count} 个！{get_current_time()}"
            )
            window._show_action_failure_feedback(
                f"创建{link_name}",
                success_count,
                failure_details,
                skipped_count,
                retry_callback=lambda: self.create_links(
                    link_type,
                    group_in_named_dir,
                    link_targets=failed_targets,
                    output_dir=output_dir,
                    should_record_success=should_record_success,
                    show_plan=False,
                ),
            )
        elif skipped_count and not success_count:
            signal_qt.show_scrape_info(
                f"💡 所选文件的{link_name}已存在，已跳过 {skipped_count} 个！{get_current_time()}"
            )
        elif skipped_count:
            signal_qt.show_scrape_info(
                f"💡 创建{link_name}完成，成功 {success_count} 个，跳过 {skipped_count} 个！{get_current_time()}"
            )
        elif success_count == 1:
            signal_qt.show_scrape_info(f"💡 已创建{link_name}！{get_current_time()}")
        else:
            signal_qt.show_scrape_info(f"💡 已创建 {success_count} 个{link_name}！{get_current_time()}")

    @staticmethod
    def delete_files(
        targets: list[tuple[str, Path]],
    ) -> tuple[list[str], list[tuple[Path, str]], list[tuple[str, Path]]]:
        success_show_names: list[str] = []
        failure_details: list[tuple[Path, str]] = []
        failed_targets: list[tuple[str, Path]] = []
        for show_name, file_path in targets:
            result, error_info = delete_file_sync(file_path)
            if result:
                if show_name:
                    success_show_names.append(show_name)
                signal_qt.show_log_text(f" ✅ 已删除文件: {file_path}")
                continue

            failure = classify_file_failure(error_info)
            failure_details.append((file_path, error_info))
            failed_targets.append((show_name, file_path))
            signal_qt.show_log_text(
                f" ❌ 删除文件失败: {file_path}\n"
                f"    类别: {failure.category.value}\n"
                f"    原因: {failure.reason}\n"
                f"    建议: {failure.suggestion}"
            )
        return success_show_names, failure_details, failed_targets

    @staticmethod
    def delete_folders(
        folder_to_show_names: dict[Path, list[str]],
    ) -> tuple[int, list[str], list[tuple[Path, str]], dict[Path, list[str]]]:
        success_count = 0
        success_show_names: list[str] = []
        failure_details: list[tuple[Path, str]] = []
        failed_targets: dict[Path, list[str]] = {}
        for folder_path, show_names in folder_to_show_names.items():
            try:
                shutil.rmtree(folder_path)
                success_count += 1
                success_show_names.extend(show_names)
                signal_qt.show_log_text(f" ✅ 已删除文件夹: {folder_path}")
            except FileNotFoundError:
                success_count += 1
                success_show_names.extend(show_names)
                signal_qt.show_log_text(f" ✅ 文件夹不存在，按已删除处理: {folder_path}")
            except Exception:
                error_info = traceback.format_exc()
                failure = classify_file_failure(error_info)
                failure_details.append((folder_path, error_info))
                failed_targets[folder_path] = show_names
                signal_qt.show_log_text(
                    f" ❌ 删除文件夹失败: {folder_path}\n"
                    f"    类别: {failure.category.value}\n"
                    f"    原因: {failure.reason}\n"
                    f"    建议: {failure.suggestion}"
                )
        return success_count, success_show_names, failure_details, failed_targets

    def retry_delete_files(self, failed_targets: list[tuple[str, Path]]) -> None:
        if not failed_targets:
            return

        signal_qt.show_log_text(f" 🔄 一键重试删除 {len(failed_targets)} 个失败文件")
        success_show_names, failure_details, remaining_targets = self.delete_files(failed_targets)
        self.window._remove_deleted_result_items(success_show_names)
        success_count = len(failed_targets) - len(failure_details)
        signal_qt.show_scrape_info(
            f"💡 重试完成，成功 {success_count} 个，仍失败 {len(failure_details)} 个！{get_current_time()}"
        )
        if failure_details:
            self.window._show_action_failure_feedback(
                "重试删除文件",
                success_count,
                failure_details,
                retry_callback=lambda: self.retry_delete_files(remaining_targets),
            )

    def retry_delete_folders(self, failed_targets: dict[Path, list[str]]) -> None:
        if not failed_targets:
            return

        signal_qt.show_log_text(f" 🔄 一键重试删除 {len(failed_targets)} 个失败文件夹")
        success_count, success_show_names, failure_details, remaining_targets = self.delete_folders(failed_targets)
        self.window._remove_deleted_result_items(success_show_names)
        signal_qt.show_scrape_info(
            f"💡 重试完成，成功 {success_count} 个，仍失败 {len(failure_details)} 个！{get_current_time()}"
        )
        if failure_details:
            self.window._show_action_failure_feedback(
                "重试删除文件夹",
                success_count,
                failure_details,
                retry_callback=lambda: self.retry_delete_folders(remaining_targets),
            )
