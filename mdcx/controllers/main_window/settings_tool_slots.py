from __future__ import annotations

import os
import re
import time
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

from mdcx.config.enums import Switch, Website
from mdcx.config.extend import deal_url, parse_media_paths
from mdcx.config.manager import manager
from mdcx.consts import IS_WINDOWS
from mdcx.core.scraper import start_new_scrape
from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt
from mdcx.utils import add_html_plain_text, get_current_time

from .style import build_action_button_style


class SettingsToolSlotsMixin:
    def label_local_number_clicked(self, _event):
        self._get_tool_controller().find_missing_numbers(False)

    def pushButton_select_local_library_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_local_library_path)
        if media_folder_path:
            self.Ui.lineEdit_local_library_path.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_netdisk_path_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_netdisk_path)
        if media_folder_path:
            self.Ui.lineEdit_netdisk_path.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_localdisk_path_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_localdisk_path)
        if media_folder_path:
            self.Ui.lineEdit_localdisk_path.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_media_folder_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_movie_path)
        if media_folder_path:
            self.Ui.lineEdit_movie_path.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_creat_symlink_clicked(self):
        """
        工具点一键创建软链接
        """
        self._get_tool_controller().create_netdisk_symlinks()

    def pushButton_find_missing_number_clicked(self):
        """
        工具点检查缺失番号
        """
        self._get_tool_controller().find_missing_numbers(True)

    def pushButton_select_file_clicked(self):
        media_path = self.Ui.lineEdit_movie_path.text()  # 获取待刮削目录作为打开目录
        if not media_path:
            media_path = manager.data_folder
        else:
            media_path = parse_media_paths(media_path)[0]
        file_path, filetype = QFileDialog.getOpenFileName(
            self,
            "选取视频文件",
            media_path.as_posix(),
            "Movie Files(*.mp4 "
            "*.avi *.rmvb *.wmv "
            "*.mov *.mkv *.flv *.ts "
            "*.webm *.MP4 *.AVI "
            "*.RMVB *.WMV *.MOV "
            "*.MKV *.FLV *.TS "
            "*.WEBM);;All Files(*)",
            options=self.options,
        )
        if file_path:
            self.Ui.lineEdit_single_file_path.setText(file_path)

    def pushButton_start_single_file_clicked(self):  # 点刮削
        Flags.single_file_path = Path(self.Ui.lineEdit_single_file_path.text().strip())
        if not Flags.single_file_path:
            signal_qt.show_scrape_info("💡 请选择文件！")
            return

        if not os.path.isfile(Flags.single_file_path):
            signal_qt.show_scrape_info("💡 文件不存在！")  # 主界面左下角显示信息
            return

        if not self.Ui.lineEdit_appoint_url.text():
            signal_qt.show_scrape_info("💡 请填写番号网址！")  # 主界面左下角显示信息
            return

        self.pushButton_show_log_clicked()  # 点击刮削按钮后跳转到日志页面
        Flags.appoint_url = self.Ui.lineEdit_appoint_url.text().strip()
        # 单文件刮削从用户输入的网址中识别网址名，复用现成的逻辑=>主页面输入网址刮削
        website, url = deal_url(Flags.appoint_url)
        if website:
            Flags.website_name = website
        else:
            signal_qt.show_scrape_info(f"💡 不支持的网站！{get_current_time()}")
            return
        start_new_scrape(FileMode.Single)

    def pushButton_select_file_clear_info_clicked(self):  # 点清空信息
        self.Ui.lineEdit_single_file_path.setText("")
        self.Ui.lineEdit_appoint_url.setText("")

    def pushButton_select_thumb_clicked(self):
        path = self.Ui.lineEdit_movie_path.text()
        if not path:
            path = manager.data_folder.as_posix()
        else:
            path = parse_media_paths(path)[0].as_posix()
        file_path, fileType = QFileDialog.getOpenFileName(
            self, "选取缩略图", path, "Picture Files(*.jpg *.png);;All Files(*)", options=self.options
        )
        if file_path:
            cutwindow = self._get_cutwindow()
            cutwindow.showimage(Path(file_path))
            cutwindow.show()

    def pushButton_move_mp4_clicked(self):
        self._get_tool_controller().start_move_files()

    def _move_file_failed(self, error: str) -> None:
        self._get_tool_controller().move_failed(error)

    def _move_file_thread(self):
        self._get_tool_controller().move_files()

    def pushButton_select_softlink_folder_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_movie_softlink_path)
        if media_folder_path:
            self.Ui.lineEdit_movie_softlink_path.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_sucess_folder_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_success)
        if media_folder_path:
            self.Ui.lineEdit_success.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_failed_folder_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_fail)
        if media_folder_path:
            self.Ui.lineEdit_fail.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_subtitle_folder_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_sub_folder)
        if media_folder_path:
            self.Ui.lineEdit_sub_folder.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_actor_photo_folder_clicked(self):
        media_folder_path = self._get_select_folder_path(self.Ui.lineEdit_actor_photo_folder)
        if media_folder_path:
            self.Ui.lineEdit_actor_photo_folder.setText(media_folder_path)
            self.pushButton_save_config_clicked()

    def pushButton_select_config_folder_clicked(self):
        p = self._get_select_folder_path(self.Ui.lineEdit_config_folder)
        if not p:
            return
        p = Path(p)
        if p.is_dir() and p != manager.data_folder:
            manager.list_configs()
            config_path = p / "config.json"
            manager.path = config_path
            if config_path.is_file():
                temp_dark = self.dark_mode
                temp_window_radius = self.window_radius
                self.load_config()
                if temp_dark != self.dark_mode and temp_window_radius == self.window_radius:
                    self.show_flag = True
                    self._windows_auto_adjust()
            else:
                self.Ui.lineEdit_config_folder.setText(str(p))
                self.pushButton_save_config_clicked()
            signal_qt.show_scrape_info(f"💡 目录已切换！{get_current_time()}")

    def pushButton_select_actor_info_db_clicked(self):
        database_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据库文件", manager.data_folder.as_posix(), options=self.options
        )
        if database_path:
            self.Ui.lineEdit_actor_db_path.setText(database_path)
            self.pushButton_save_config_clicked()

    def pushButton_check_and_clean_files_clicked(self):
        self._get_tool_controller().clean_files()

    def pushButton_add_sub_for_all_video_clicked(self):
        self._get_tool_controller().add_subtitles()

    def pushButton_add_all_extras_clicked(self):
        self._get_tool_controller().update_extras("add")

    def pushButton_del_all_extras_clicked(self):
        self._get_tool_controller().update_extras("del")

    def pushButton_add_all_extrafanart_copy_clicked(self):
        self._get_tool_controller().update_extrafanart_copy("add")

    def pushButton_del_all_extrafanart_copy_clicked(self):
        self._get_tool_controller().update_extrafanart_copy("del")

    def pushButton_add_all_theme_videos_clicked(self):
        self._get_tool_controller().update_theme_videos("add")

    def pushButton_del_all_theme_videos_clicked(self):
        self._get_tool_controller().update_theme_videos("del")

    def pushButton_add_actor_info_clicked(self):
        self._get_tool_controller().update_actor_info()

    def pushButton_add_actor_pic_clicked(self):
        self._get_tool_controller().update_actor_photos()

    def pushButton_add_actor_pic_kodi_clicked(self):
        self._get_tool_controller().update_kodi_actors(True)

    def pushButton_del_actor_folder_clicked(self):
        self._get_tool_controller().update_kodi_actors(False)

    def pushButton_show_pic_actor_clicked(self):
        self._get_tool_controller().show_actor_list()

    def lcdNumber_thread_change(self):
        thread_number = self.Ui.horizontalSlider_thread.value()
        self.Ui.lcdNumber_thread.display(thread_number)

    def lcdNumber_javdb_time_change(self):
        javdb_time = self.Ui.horizontalSlider_javdb_time.value()
        self.Ui.lcdNumber_javdb_time.display(javdb_time)

    def lcdNumber_thread_time_change(self):
        thread_time = self.Ui.horizontalSlider_thread_time.value()
        self.Ui.lcdNumber_thread_time.display(thread_time)

    def lcdNumber_timeout_change(self):
        timeout = self.Ui.horizontalSlider_timeout.value()
        self.Ui.lcdNumber_timeout.display(timeout)

    def lcdNumber_retry_change(self):
        retry = self.Ui.horizontalSlider_retry.value()
        self.Ui.lcdNumber_retry.display(retry)

    def lcdNumber_mark_size_change(self):
        mark_size = self.Ui.horizontalSlider_mark_size.value()
        self.Ui.lcdNumber_mark_size.display(mark_size)

    def switch_custom_website_change(self, site):
        if site not in Website:
            return
        site = Website(site)
        self.Ui.lineEdit_site_custom_url.setText(manager.config.get_site_url(site))

    def config_file_change(self, new_config_file: str):
        if new_config_file != manager.file:
            new_config_path = manager.data_folder / new_config_file
            signal_qt.show_log_text(
                f"\n================================================================================\n切换配置：{new_config_path}"
            )
            manager.path = new_config_path
            temp_dark = self.dark_mode
            temp_window_radius = self.window_radius
            self.load_config()
            if temp_dark != self.dark_mode and temp_window_radius == self.window_radius:
                self.show_flag = True
                self._windows_auto_adjust()
            signal_qt.show_scrape_info(f"💡 配置已切换！{get_current_time()}")

    def pushButton_init_config_clicked(self):
        self.Ui.pushButton_init_config.setEnabled(False)
        manager.reset()
        temp_dark = self.dark_mode
        temp_window_radius = self.window_radius
        self.load_config()
        if temp_dark and temp_window_radius:
            self.show_flag = True
            self._windows_auto_adjust()
        self.Ui.pushButton_init_config.setEnabled(True)
        signal_qt.show_scrape_info(f"💡 配置已重置！{get_current_time()}")

    def checkBox_cd_part_a_clicked(self):
        if self.Ui.checkBox_cd_part_a.isChecked():
            self.Ui.checkBox_cd_part_c.setEnabled(True)
        else:
            self.Ui.checkBox_cd_part_c.setEnabled(False)

    def checkBox_i_agree_clean_clicked(self):
        if self.Ui.checkBox_i_understand_clean.isChecked() and self.Ui.checkBox_i_agree_clean.isChecked():
            self.Ui.pushButton_check_and_clean_files.setEnabled(True)
            self.Ui.checkBox_auto_clean.setEnabled(True)
        else:
            self.Ui.pushButton_check_and_clean_files.setEnabled(False)
            self.Ui.checkBox_auto_clean.setEnabled(False)

    def _check_mac_config_folder(self):
        if self.check_mac and not IS_WINDOWS and ".app/Contents/Resources" in manager.data_folder.as_posix():
            self.check_mac = False
            box = QMessageBox(
                QMessageBox.Icon.Warning,
                "选择配置文件目录",
                f"检测到当前配置文件目录为：\n {manager.data_folder}\n\n由于 MacOS 平台在每次更新 APP 版本时会覆盖该目录的配置，因此请选择其他的配置目录！\n这样下次更新 APP 时，选择相同的配置目录即可读取你之前的配置！！！",
            )
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.button(QMessageBox.StandardButton.Yes).setText("选择目录")
            box.button(QMessageBox.StandardButton.No).setText("取消")
            box.setDefaultButton(QMessageBox.StandardButton.Yes)
            reply = box.exec()
            if reply == QMessageBox.StandardButton.Yes:
                self.pushButton_select_config_folder_clicked()

    def pushButton_save_config_clicked(self):
        invalid = self.settings_controller.validate()
        if invalid:
            message = self.settings_controller.reveal_validation_error(invalid[0])
            QMessageBox.warning(self, "设置输入无效", f"{message}\n\n已自动定位并标红第一个无效设置。")
            return
        self.save_config()
        self.load_config()  # 确保界面显示和实际配置一致
        signal_qt.show_scrape_info(f"💡 配置已保存！{get_current_time()}")

    def pushButton_save_new_config_clicked(self):
        new_config_name, ok = QInputDialog.getText(self, "另存为新配置", "请输入新配置的文件名")
        if ok and new_config_name:
            new_config_name = new_config_name.replace("/", "").replace("\\", "")
            new_config_name = re.sub(r'[\\:*?"<>|\r\n]+', "", new_config_name)
            if os.path.splitext(new_config_name)[1] != ".json":
                new_config_name += ".json"
            if new_config_name != manager.file:
                manager.path = manager.data_folder / new_config_name
                self.pushButton_save_config_clicked()

    def save_config(self): ...

    def pushButton_check_net_clicked(self):
        self.network_controller.toggle_network_check()

    def show_net_info(self, text):
        try:
            self.net_logs_show.emit(add_html_plain_text(text))
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
            self.Ui.textBrowser_net_main.append(traceback.format_exc())

    def pushButton_check_javdb_cookie_clicked(self):
        self.network_controller.check_javdb_cookie()

    def pushButton_check_fc2ppvdb_cookie_clicked(self):
        self.network_controller.check_fc2ppvdb_cookie()

    def pushButton_check_javbus_cookie_clicked(self):
        self.network_controller.check_javbus_cookie()

    def _get_select_folder_path(self, default_source: QLineEdit | str | Path | None = None):
        media_path = self._get_select_folder_default_path(default_source).as_posix()
        media_folder_path = QFileDialog.getExistingDirectory(
            self, "选择目录", media_path, options=self.options | QFileDialog.Option.ShowDirsOnly
        )
        return media_folder_path

    def _get_select_folder_default_path(self, default_source: QLineEdit | str | Path | None = None) -> Path:
        if isinstance(default_source, QLineEdit):
            default_text = default_source.text()
        elif default_source is None:
            default_text = ""
        else:
            default_text = str(default_source)

        for path in self._iter_select_folder_candidates(default_text):
            if path.is_dir():
                return path

        for path in self._iter_select_folder_candidates(self.Ui.lineEdit_movie_path.text()):
            if path.is_dir():
                return path

        if manager.data_folder.is_dir():
            return manager.data_folder
        return Path.home()

    def _iter_select_folder_candidates(self, path_text: str):
        movie_roots = [path for path in parse_media_paths(self.Ui.lineEdit_movie_path.text()) if path.is_dir()]
        for item in re.split(r"[;；,，]", path_text):
            item = item.strip().strip("\"'")
            if not item:
                continue
            path = Path(item)
            if path.is_absolute():
                yield path
                continue
            for movie_root in movie_roots:
                yield movie_root / path
            yield path

    def recover_windowflags(self):
        return

    def change_buttons_status(self):
        Flags.stop_other = True
        self.Ui.pushButton_start_cap.setText("■ 停止")
        self.Ui.pushButton_start_cap2.setText("■ 停止")
        self.Ui.pushButton_select_media_folder.setVisible(False)
        self.Ui.pushButton_start_single_file.setEnabled(False)
        self.Ui.pushButton_start_single_file.setText("正在刮削中...")
        self.Ui.pushButton_add_sub_for_all_video.setEnabled(False)
        self.Ui.pushButton_add_sub_for_all_video.setText("正在刮削中...")
        self.Ui.pushButton_show_pic_actor.setEnabled(False)
        self.Ui.pushButton_show_pic_actor.setText("刮削中...")
        self.Ui.pushButton_add_actor_info.setEnabled(False)
        self.Ui.pushButton_add_actor_info.setText("正在刮削中...")
        self.Ui.pushButton_add_actor_pic.setEnabled(False)
        self.Ui.pushButton_add_actor_pic.setText("正在刮削中...")
        self.Ui.pushButton_add_actor_pic_kodi.setEnabled(False)
        self.Ui.pushButton_add_actor_pic_kodi.setText("正在刮削中...")
        self.Ui.pushButton_del_actor_folder.setEnabled(False)
        self.Ui.pushButton_del_actor_folder.setText("正在刮削中...")
        # self.Ui.pushButton_check_and_clean_files.setEnabled(False)
        self.Ui.pushButton_check_and_clean_files.setText("正在刮削中...")
        self.Ui.pushButton_move_mp4.setEnabled(False)
        self.Ui.pushButton_move_mp4.setText("正在刮削中...")
        self.Ui.pushButton_find_missing_number.setEnabled(False)
        self.Ui.pushButton_find_missing_number.setText("正在刮削中...")
        self.Ui.pushButton_start_cap.setStyleSheet(
            build_action_button_style("pushButton_start_cap", self.dark_mode, danger=True)
        )
        self.Ui.pushButton_start_cap2.setStyleSheet(
            build_action_button_style("pushButton_start_cap2", self.dark_mode, danger=True)
        )

    def reset_buttons_status(self):
        self.Ui.pushButton_start_cap.setEnabled(True)
        self.Ui.pushButton_start_cap2.setEnabled(True)
        self.pushButton_start_cap.emit("开始")
        self.pushButton_start_cap2.emit("开始")
        self.Ui.pushButton_select_media_folder.setVisible(True)
        self.Ui.pushButton_start_single_file.setEnabled(True)
        self.pushButton_start_single_file.emit("刮削")
        self.Ui.pushButton_add_sub_for_all_video.setEnabled(True)
        self.pushButton_add_sub_for_all_video.emit("点击检查所有视频的字幕情况并为无字幕视频添加字幕")

        self.Ui.pushButton_show_pic_actor.setEnabled(True)
        self.pushButton_show_pic_actor.emit("查看")
        self.Ui.pushButton_add_actor_info.setEnabled(True)
        self.pushButton_add_actor_info.emit("开始补全")
        self.Ui.pushButton_add_actor_pic.setEnabled(True)
        self.pushButton_add_actor_pic.emit("开始补全")
        self.Ui.pushButton_add_actor_pic_kodi.setEnabled(True)
        self.pushButton_add_actor_pic_kodi.emit("开始补全")
        self.Ui.pushButton_del_actor_folder.setEnabled(True)
        self.pushButton_del_actor_folder.emit("清除所有.actors文件夹")
        self.Ui.pushButton_check_and_clean_files.setEnabled(True)
        self.pushButton_check_and_clean_files.emit("点击检查待刮削目录并清理文件")
        self.Ui.pushButton_move_mp4.setEnabled(True)
        self.pushButton_move_mp4.emit("开始移动")
        self.Ui.pushButton_find_missing_number.setEnabled(True)
        self.pushButton_find_missing_number.emit("检查缺失番号")

        self.Ui.pushButton_start_cap.setStyleSheet(build_action_button_style("pushButton_start_cap", self.dark_mode))
        self.Ui.pushButton_start_cap2.setStyleSheet(build_action_button_style("pushButton_start_cap2", self.dark_mode))
        Flags.file_mode = FileMode.Default
        self.threads_list = [thread for thread in self.threads_list if thread.is_alive()]
        if len(Flags.failed_list):
            self.Ui.pushButton_scraper_failed_list.setText(f"一键重新刮削当前 {len(Flags.failed_list)} 个失败文件")
        else:
            self.Ui.pushButton_scraper_failed_list.setText("当有失败任务时，点击可以一键刮削当前失败列表")

    def auto_scrape(self):
        if Switch.TIMED_SCRAPE in manager.config.switch_on and self.Ui.pushButton_start_cap.text() == "开始":
            time.sleep(0.1)
            timed_interval = manager.config.timed_interval
            self.atuo_scrape_count += 1
            signal_qt.show_log_text(
                f"\n\n 🍔 已启用「循环刮削」！间隔时间：{timed_interval}！即将开始第 {self.atuo_scrape_count} 次循环刮削！"
            )
            if Flags.scrape_start_time:
                signal_qt.show_log_text(
                    " ⏰ 上次刮削时间: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(Flags.scrape_start_time))
                )
            start_new_scrape(FileMode.Default)

    def auto_start(self):
        if Switch.AUTO_START in manager.config.switch_on:
            signal_qt.show_log_text("\n\n 🍔 已启用「软件启动后自动刮削」！即将开始自动刮削！")
            self.pushButton_start_scrape_clicked()
