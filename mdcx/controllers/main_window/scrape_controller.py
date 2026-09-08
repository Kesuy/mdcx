from __future__ import annotations

import asyncio
import time
import traceback
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from mdcx.config.enums import Switch
from mdcx.config.manager import manager
from mdcx.core.scraper import get_remain_list, start_new_scrape, stop_active_scrape
from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


class ScrapeController:
    """Coordinate scrape start/stop and cooperative worker shutdown."""

    def __init__(self, window: MyMAinWindow) -> None:
        self.window = window

    def toggle(self) -> None:
        window = self.window
        if window.Ui.pushButton_start_cap.text() == "开始":
            if not get_remain_list():
                start_new_scrape(FileMode.Default)
        elif window.Ui.pushButton_start_cap.text() == "■ 停止":
            self.stop()

    def stop(self) -> None:
        window = self.window
        if Switch.SHOW_DIALOG_STOP_SCRAPE in manager.config.switch_on:
            box = QMessageBox(QMessageBox.Icon.Warning, "停止刮削", "确定要停止刮削吗？", parent=window)
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.button(QMessageBox.StandardButton.Yes).setText("停止刮削")
            box.button(QMessageBox.StandardButton.No).setText("取消")
            box.setDefaultButton(QMessageBox.StandardButton.No)
            if box.exec() != QMessageBox.StandardButton.Yes:
                return
        if window.Ui.pushButton_start_cap.text() != "■ 停止":
            return

        Flags.request_cancel()
        signal_qt.stop = True
        window._thread_stop_event.set()
        self._stop_started_at = time.monotonic()
        Flags.rest_time_convert_ = Flags.rest_time_convert
        Flags.rest_time_convert = 0
        window.Ui.pushButton_start_cap.setText(" ■ 停止中 ")
        window.Ui.pushButton_start_cap2.setText(" ■ 停止中 ")
        signal_qt.show_scrape_info("⛔️ 刮削停止中...")
        window.task_manager.submit(
            "stop-scrape",
            self._wait_for_stop(),
            on_success=lambda _: self.show_stop_info(),
            on_error=self.stop_failed,
        )

    async def _wait_for_stop(self) -> None:
        await stop_active_scrape()
        # The same stop button also controls cooperative file-moving tools.
        while self.window.task_manager.is_running("move-media-files"):
            await asyncio.sleep(0.05)

    def stop_failed(self, error: str) -> None:
        signal_qt.show_traceback_log(error)
        signal_qt.show_log_text("停止刮削收尾失败，请查看错误日志。")

    def show_stop_info(self) -> None:
        window = self.window
        window.stop_used_time = round(time.monotonic() - self._stop_started_at, 2)
        signal_qt.reset_buttons_status.emit()
        try:
            Flags.rest_time_convert = Flags.rest_time_convert_
            if Flags.stop_other:
                signal_qt.show_scrape_info("⛔️ 已手动停止！")
                signal_qt.show_log_text(
                    "⛔️ 已手动停止！\n================================================================================"
                )
                window.set_label_file_path.emit("⛔️ 已手动停止！")
                return
            signal_qt.exec_set_processbar.emit(0)
            end_time = time.time()
            used_time = str(round((end_time - Flags.start_time), 2))
            average_time = (
                str(round((end_time - Flags.start_time) / Flags.scrape_done, 2)) if Flags.scrape_done else used_time
            )
            signal_qt.show_scrape_info("⛔️ 刮削已手动停止！")
            window.set_label_file_path.emit(
                f"⛔️ 刮削已手动停止！\n   已刮削 {Flags.scrape_done} 个视频, "
                f"还剩余 {Flags.total_count - Flags.scrape_done} 个! 刮削用时 {used_time} 秒"
            )
            signal_qt.show_log_text(
                f"\n ⛔️ 刮削已手动停止！\n 😊 已刮削 {Flags.scrape_done} 个视频, "
                f"还剩余 {Flags.total_count - Flags.scrape_done} 个! 刮削用时 {used_time} 秒, "
                f"停止用时 {window.stop_used_time} 秒"
            )
            signal_qt.show_log_text("================================================================================")
            signal_qt.show_log_text(
                " ⏰ Start time".ljust(13) + ": " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(Flags.start_time))
            )
            signal_qt.show_log_text(
                " 🏁 End time".ljust(13) + ": " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
            )
            signal_qt.show_log_text(f"{' ⏱ Used time'.ljust(13)}: {used_time}S")
            signal_qt.show_log_text(f"{' 🍕 Per time'.ljust(13)}: {average_time}S")
            signal_qt.show_log_text("================================================================================")
            Flags.again_dic.clear()
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
            signal_qt.show_log_text(traceback.format_exc())
        finally:
            signal_qt.stop = False
