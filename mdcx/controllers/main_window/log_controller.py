from __future__ import annotations

import os
import time
import traceback
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from mdcx.base.file import get_success_list, save_success_list
from mdcx.config.extend import get_movie_path_setting
from mdcx.config.manager import manager
from mdcx.config.resources import resources
from mdcx.core.scraper import start_new_scrape
from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt
from mdcx.utils import add_html, add_html_plain_text, executor

from .failure_center import FailureCenterDialog
from .responsive_layout import show_responsive_overlay


class LogControllerMixin:
    def update_failure_count(self, text: str) -> None:
        self.Ui.pushButton_view_failed_list.setText(text)
        count_text = "".join(character for character in text if character.isdigit())
        navigation_text = f"日志  • {count_text}" if count_text and count_text != "0" else "日志"
        self.Ui.pushButton_log.setProperty("mdcxFullButtonText", navigation_text)
        self.Ui.pushButton_log.setToolTip(f"{navigation_text} 条失败" if count_text else "")
        if getattr(self, "_responsive_mode", "standard") != "narrow":
            self.Ui.pushButton_log.setText(navigation_text)

    def show_scrape_info(self, before_info=""):
        try:
            if Flags.file_mode == FileMode.Single:
                scrape_info = f"💡 单文件刮削\n💠 {Flags.main_mode_text} · {self.Ui.comboBox_website_all.currentText()}"
            else:
                scrape_info = f"💠 {Flags.main_mode_text} · {Flags.scrape_like_text}"
                if manager.config.scrape_like == "single":
                    scrape_info = f"💡 {manager.config.selected_site} 刮削\n" + scrape_info
            if manager.config.soft_link == 1:
                scrape_info = "🍯 软链接 · 开\n" + scrape_info
            elif manager.config.soft_link == 2:
                scrape_info = "🍯 硬链接 · 开\n" + scrape_info
            after_info = f"\n{scrape_info}\n🛠 {manager.file}\n🐰 MDCx {self.localversion}"
            self.label_show_version.emit(before_info + after_info + self.new_version)
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())

    def pushButton_success_list_save_clicked(self):
        box = QMessageBox(QMessageBox.Icon.Warning, "保存成功列表", "确定要将当前列表保存为已刮削成功文件列表吗？")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("保存")
        box.button(QMessageBox.StandardButton.No).setText("取消")
        box.setDefaultButton(QMessageBox.StandardButton.No)
        reply = box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            success_text = self.Ui.textBrowser_show_success_list.toPlainText().replace("暂无成功刮削的文件", "").strip()
            Flags.success_list = {
                p for path in success_text.splitlines() if (line := path.strip()) and (p := Path(line)).suffix
            }
            executor.run(save_success_list())
            get_success_list()
            self.Ui.widget_show_success.hide()

    def pushButton_success_list_clear_clicked(self):
        box = QMessageBox(QMessageBox.Icon.Warning, "清空成功列表", "确定要清空当前已刮削成功文件列表吗？")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("清空")
        box.button(QMessageBox.StandardButton.No).setText("取消")
        box.setDefaultButton(QMessageBox.StandardButton.No)
        reply = box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            Flags.success_list.clear()
            executor.run(save_success_list())
            self.Ui.widget_show_success.hide()

    def pushButton_view_success_file_clicked(self):
        show_responsive_overlay(self, self.Ui.widget_show_success)
        info = "暂无成功刮削的文件"
        if len(Flags.success_list):
            info = "\n".join(sorted(str(p) for p in Flags.success_list))
        self.Ui.textBrowser_show_success_list.setText(info)

    def pushButton_show_hide_logs_clicked(self):
        if self.Ui.textBrowser_log_main_2.isHidden():
            self.show_hide_logs(True)
        else:
            self.show_hide_logs(False)

    def show_hide_logs(self, show):
        if show:
            self.Ui.pushButton_show_hide_logs.setIcon(QIcon(resources.hide_logs_icon))
            self.Ui.textBrowser_log_main_2.show()
            if not hasattr(self, "_log_splitter"):
                self.Ui.textBrowser_log_main.resize(790, 418)
            self.Ui.textBrowser_log_main.verticalScrollBar().setValue(
                self.Ui.textBrowser_log_main.verticalScrollBar().maximum()
            )
            self.Ui.textBrowser_log_main_2.verticalScrollBar().setValue(
                self.Ui.textBrowser_log_main_2.verticalScrollBar().maximum()
            )

        else:
            self.Ui.pushButton_show_hide_logs.setIcon(QIcon(resources.show_logs_icon))
            self.Ui.textBrowser_log_main_2.hide()
            if not hasattr(self, "_log_splitter"):
                self.Ui.textBrowser_log_main.resize(790, 689)
            self.Ui.textBrowser_log_main.verticalScrollBar().setValue(
                self.Ui.textBrowser_log_main.verticalScrollBar().maximum()
            )

    def pushButton_show_hide_failed_list_clicked(self):
        if Flags.failed_records:
            self.show_failure_center()
            return
        if self.Ui.textBrowser_log_main_3.isHidden():
            self.show_hide_failed_list(True)
        else:
            self.show_hide_failed_list(False)

    def show_hide_failed_list(self, show):
        if show:
            self.Ui.textBrowser_log_main_3.show()
            has_retryable = not Flags.failed_records or any(record.retryable for record in Flags.failed_records)
            self.Ui.pushButton_scraper_failed_list.setVisible(has_retryable)
            self.Ui.pushButton_save_failed_list.show()
            self.Ui.textBrowser_log_main_3.raise_()
            self.Ui.pushButton_scraper_failed_list.raise_()
            self.Ui.pushButton_save_failed_list.raise_()
            self.Ui.textBrowser_log_main_3.verticalScrollBar().setValue(
                self.Ui.textBrowser_log_main_3.verticalScrollBar().maximum()
            )

        else:
            self.Ui.pushButton_save_failed_list.hide()
            self.Ui.textBrowser_log_main_3.hide()
            self.Ui.pushButton_scraper_failed_list.hide()

    def show_failure_center(self) -> None:
        dialog = getattr(self, "_failure_center", None)
        if dialog is None:
            dialog = FailureCenterDialog(self, retry_callback=self._retry_failure_records)
            self._failure_center = dialog
        dialog.set_records(Flags.failed_records)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _retry_failure_records(self, records) -> bool:
        if self.Ui.pushButton_start_cap.text() != "开始":
            return False
        paths = list(dict.fromkeys(record.path for record in records if record.retryable))
        if not paths:
            return False
        Flags.failed_records[:] = [record for record in Flags.failed_records if record not in records]
        remaining_paths = {record.path for record in Flags.failed_records}
        Flags.failed_list[:] = [item for item in Flags.failed_list if item[0] in remaining_paths]
        start_new_scrape(FileMode.Default, movie_list=paths)
        return True

    def pushButton_scraper_failed_list_clicked(self):
        if len(Flags.failed_list) and self.Ui.pushButton_start_cap.text() == "开始":
            if Flags.failed_records:
                retry_paths = [record.path for record in Flags.failed_records if record.retryable]
            else:
                retry_paths = [item[0] for item in Flags.failed_list]
            if not retry_paths:
                return
            start_new_scrape(FileMode.Default, movie_list=list(dict.fromkeys(retry_paths)))
            self.show_hide_failed_list(False)

    def pushButton_save_failed_list_clicked(self):
        if len(Flags.failed_list):
            log_name = "failed_" + time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + ".txt"
            log_name = get_movie_path_setting().movie_path / log_name
            filename, filetype = QFileDialog.getSaveFileName(
                self, "保存失败文件列表", log_name.as_posix(), "Text Files (*.txt)", options=self.options
            )
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.Ui.textBrowser_log_main_3.toPlainText().strip())

    def _write_main_logs_to_file(self, logs: list[str]):
        if not logs:
            return
        text = "\n".join(logs) + "\n"
        try:
            Flags.log_txt.write(text.encode("utf-8"))
        except Exception:
            log_folder = manager.data_folder / "Log"
            if not os.path.exists(log_folder):
                os.makedirs(log_folder, exist_ok=True)
            log_name = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + ".txt"
            log_name = log_folder / log_name
            try:
                Flags.log_txt = open(log_name, "wb", buffering=0)
                Flags.log_txt.write(text.encode("utf-8"))
                self.main_log_queue.appendleft(f"创建日志文件: {log_name}")
            except Exception:
                signal_qt.show_traceback_log(traceback.format_exc())

    def _flush_main_log_queue(self):
        if not self.main_log_queue:
            return
        logs: list[str] = []
        while self.main_log_queue and len(logs) < self.main_log_batch_size:
            logs.append(self.main_log_queue.popleft())
        if manager.config.save_log:
            self._write_main_logs_to_file(logs)
        try:
            self.logs_counts += len(logs)
            if self.logs_counts >= self.main_log_max_count:
                self.logs_counts = len(logs)
                self.main_logs_clear.emit("")
                self.main_logs_show.emit(add_html(" 🗑️ 日志过多，已清屏！"))
            self.main_logs_show.emit(add_html("\n".join(logs)))
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
            self.Ui.textBrowser_log_main.append(traceback.format_exc())

    def show_detail_log(self):
        text = signal_qt.get_log()
        if text and manager.config.show_web_log:
            self.main_req_logs_show.emit(add_html_plain_text(text))
            if self.req_logs_counts < 10000:
                self.req_logs_counts += 1
            else:
                self.req_logs_counts = 0
                self.req_logs_clear.emit("")
                self.main_req_logs_show.emit(add_html_plain_text(" 🗑️ 日志过多，已清屏！"))

    def show_log_text(self, text):
        if not text:
            return
        self.main_log_queue.append(str(text))
