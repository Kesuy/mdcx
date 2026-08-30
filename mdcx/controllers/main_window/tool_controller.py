from __future__ import annotations

import shutil
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from mdcx.base.file import check_and_clean_files, movie_lists, newtdisk_creat_symlink
from mdcx.base.image import add_del_extrafanart_copy
from mdcx.base.video import add_del_extras, add_del_theme_videos
from mdcx.config.enums import Switch
from mdcx.config.extend import get_movie_path_setting
from mdcx.config.manager import manager
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt
from mdcx.tools.emby_actor_image import update_emby_actor_photo
from mdcx.tools.emby_actor_info import creat_kodi_actors, show_emby_actor_list, update_emby_actor_info
from mdcx.tools.missing import check_missing_number
from mdcx.tools.subtitle import add_sub_for_all_video
from mdcx.utils import executor

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


class ToolController:
    """Own long-running file utilities shown on the tools/settings pages."""

    def __init__(self, window: MyMAinWindow) -> None:
        self.window = window

    def start_move_files(self) -> None:
        window = self.window
        box = QMessageBox(QMessageBox.Icon.Warning, "移动视频和字幕", "确定要移动视频和字幕吗？", parent=window)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("移动")
        box.button(QMessageBox.StandardButton.No).setText("取消")
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        window.pushButton_show_log_clicked()
        try:
            if window.task_manager.is_running("move-media-files"):
                signal_qt.show_log_text("上一次移动任务仍在运行，未启动新的移动任务。")
                return
            window._thread_stop_event.clear()
            window.task_manager.submit_sync(
                "move-media-files",
                self.move_files,
                on_error=self.move_failed,
            )
        except Exception:
            error = traceback.format_exc()
            signal_qt.show_traceback_log(error)
            signal_qt.show_log_text(error)

    @staticmethod
    def move_failed(error: str) -> None:
        signal_qt.show_traceback_log(error)
        signal_qt.show_log_text("移动视频任务异常终止，请查看错误日志。")
        signal_qt.reset_buttons_status.emit()

    def move_files(self) -> None:
        window = self.window
        signal_qt.change_buttons_status.emit()
        movie_items: list[tuple[Path, Path]] = []
        for movie_path in get_movie_path_setting().movie_paths:
            if not movie_path.exists():
                signal_qt.show_log_text(f" 🔴 Movie folder does not exist: {movie_path}")
                continue
            path_config = get_movie_path_setting(movie_path_override=movie_path)
            ignore_dirs = [*path_config.ignore_dirs, movie_path / "Movie_moved"]
            movie_list = executor.run(
                movie_lists(ignore_dirs, manager.config.media_type + manager.config.sub_type, movie_path)
            )
            movie_items.extend((movie_path, file_path) for file_path in movie_list)

        if not movie_items:
            signal_qt.show_log_text("No movie found!")
            signal_qt.show_log_text("=" * 80)
            signal_qt.reset_buttons_status.emit()
            return

        signal_qt.show_log_text("Start move movies...")
        failures: list[tuple[str, Path, str]] = []
        for movie_path, file_path in movie_items:
            if window._thread_stop_event.is_set() or signal_qt.stop or Flags.stop_requested:
                signal_qt.show_log_text("移动任务已停止；当前文件操作已安全完成。")
                break
            destination = movie_path / "Movie_moved"
            destination.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(file_path, destination)
                kind = "movie" if file_path.suffix.lower() in manager.config.media_type else "sub"
                signal_qt.show_log_text(f"   Move {kind}: {file_path.name} to Movie_moved Success!")
            except Exception as error:
                failures.append((file_path.name, file_path, str(error)))

        if failures:
            signal_qt.show_log_text(f"\n{len(failures)} file(s) did not move!")
            for index, (name, path, error) in enumerate(failures, start=1):
                signal_qt.show_log_text(f"[{index}] {name}\n file path: {path}\n {error}\n")
        signal_qt.show_log_text("Move movies finished!")
        signal_qt.show_log_text("=" * 80)
        signal_qt.reset_buttons_status.emit()

    def clean_files(self) -> None:
        window = self.window
        if not manager.computed.can_clean:
            window.pushButton_save_config_clicked()
        window.pushButton_show_log_clicked()
        try:
            executor.submit(check_and_clean_files())
        except Exception:
            error = traceback.format_exc()
            signal_qt.show_traceback_log(error)
            signal_qt.show_log_text(error)

    def _submit_tool_action(self, coroutine_factory, *, save_config: bool = False) -> None:
        window = self.window
        if save_config:
            window.pushButton_save_config_clicked()
        window.pushButton_show_log_clicked()
        try:
            executor.submit(coroutine_factory())
        except Exception:
            error = traceback.format_exc()
            signal_qt.show_traceback_log(error)
            signal_qt.show_log_text(error)

    def add_subtitles(self) -> None:
        self._submit_tool_action(add_sub_for_all_video)

    def update_extras(self, action: str) -> None:
        self._submit_tool_action(lambda: add_del_extras(action))

    def update_extrafanart_copy(self, action: str) -> None:
        self._submit_tool_action(lambda: add_del_extrafanart_copy(action), save_config=True)

    def update_theme_videos(self, action: str) -> None:
        self._submit_tool_action(lambda: add_del_theme_videos(action))

    def update_actor_info(self) -> None:
        self._submit_tool_action(update_emby_actor_info, save_config=True)

    def update_actor_photos(self) -> None:
        self._submit_tool_action(update_emby_actor_photo, save_config=True)

    def update_kodi_actors(self, create: bool) -> None:
        self._submit_tool_action(lambda: creat_kodi_actors(create), save_config=create)

    def show_actor_list(self) -> None:
        actor_type = self.window.Ui.comboBox_pic_actor.currentIndex()
        self._submit_tool_action(lambda: show_emby_actor_list(actor_type))

    def find_missing_numbers(self, show_dialog: bool) -> None:
        window = self.window
        if not window.Ui.pushButton_find_missing_number.isEnabled():
            return
        actor_changed = window.Ui.lineEdit_actors_name.text() != manager.config.actors_name
        library_changed = window.Ui.lineEdit_local_library_path.text() != ",".join(manager.config.local_library)
        if actor_changed or library_changed:
            window.pushButton_save_config_clicked()
        window.pushButton_show_log_clicked()
        executor.submit(check_missing_number(show_dialog))

    def create_netdisk_symlinks(self) -> None:
        window = self.window
        copy_nfo = window.Ui.checkBox_copy_netdisk_nfo.isChecked()
        if (Switch.COPY_NETDISK_NFO in manager.config.switch_on) != copy_nfo:
            window.pushButton_save_config_clicked()
        window.pushButton_show_log_clicked()
        try:
            executor.submit(newtdisk_creat_symlink(copy_nfo))
        except Exception:
            error = traceback.format_exc()
            signal_qt.show_traceback_log(error)
            signal_qt.show_log_text(error)
