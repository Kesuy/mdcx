from __future__ import annotations

import shutil
import traceback
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from mdcx.signals import signal_qt
from mdcx.utils import get_current_time
from mdcx.utils.file import delete_file_sync

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


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
