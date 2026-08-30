from __future__ import annotations

import threading
import time
import traceback
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from mdcx.base.file import save_success_list
from mdcx.config.enums import Switch
from mdcx.config.manager import manager
from mdcx.core.scraper import get_remain_list, start_new_scrape
from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt
from mdcx.utils import SCRAPE_TASK_GROUP, executor, get_current_time, get_used_time, kill_a_thread

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

        Flags.stop_requested = True
        signal_qt.stop = True
        executor.run(save_success_list())
        Flags.rest_time_convert_ = Flags.rest_time_convert
        Flags.rest_time_convert = 0
        window.Ui.pushButton_start_cap.setText(" ■ 停止中 ")
        window.Ui.pushButton_start_cap2.setText(" ■ 停止中 ")
        signal_qt.show_scrape_info("⛔️ 刮削停止中...")
        executor.cancel_async(group=SCRAPE_TASK_GROUP)
        if not window.threads_list:
            window.stop_used_time = 0.0
            self.schedule_stop_info()
            return
        window.task_manager.submit_sync("stop-workers", self.kill_workers)

    def show_stop_info(self) -> None:
        window = self.window
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

    def schedule_stop_info(self) -> None:
        self.window.task_manager.submit_sync("show-stop-info", self.show_stop_info)

    def kill_workers(self) -> None:
        window = self.window
        Flags.total_kills = len(window.threads_list)
        Flags.now_kill = 0
        start_time = time.time()
        window.set_label_file_path.emit(
            f"⛔️ 正在停止刮削...\n   正在停止已在运行的任务线程（1/{Flags.total_kills}）..."
        )
        signal_qt.show_log_text(
            f"\n ⛔️ {get_current_time()} 已停止添加新的刮削任务，正在停止已在运行的任务线程（{Flags.total_kills}）..."
        )
        signal_qt.show_traceback_log(f"⛔️ 正在停止正在运行的任务线程 ({Flags.total_kills}) ...")
        for index, each in enumerate(window.threads_list, start=1):
            signal_qt.show_traceback_log(f"正在停止线程: {index}/{Flags.total_kills} {each.name} ...")
        signal_qt.show_traceback_log(
            "线程正在停止中，请稍后...\n 🍯 停止时间与线程数量及线程正在执行的任务有关，"
            "比如正在执行网络请求、文件下载等IO操作时，需要等待其释放资源。。。\n"
        )
        signal_qt.stop = True
        window._thread_stop_event.set()
        alive_threads: list[threading.Thread] = []
        for each in window.threads_list:
            if not kill_a_thread(each):
                alive_threads.append(each)

        window.stop_used_time = get_used_time(start_time)
        stopped_count = Flags.total_kills - len(alive_threads)
        signal_qt.show_log_text(f" 🕷 {get_current_time()} 已停止线程：{stopped_count}/{Flags.total_kills}")
        if alive_threads:
            alive_names = ", ".join(each.name for each in alive_threads)
            signal_qt.show_traceback_log(f"线程仍在完成当前操作，将不再强制终止：{alive_names}")
            signal_qt.show_log_text(f" 🟡 以下线程仍在完成当前操作：{alive_names}")
        else:
            signal_qt.show_traceback_log(f"所有线程已停止！！！({window.stop_used_time}s)\n ⛔️ 刮削已手动停止！\n")
            signal_qt.show_log_text(f" ⛔️ {get_current_time()} 所有线程已停止！({window.stop_used_time}s)")
        self.schedule_stop_info()
