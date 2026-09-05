import os
import platform
import traceback
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileDialog

from mdcx.config.enums import (
    CDChar,
    Switch,
    Translator,
    Website,
    website_display_name,
)
from mdcx.config.extend import get_movie_path_setting
from mdcx.config.manager import manager
from mdcx.config.resources import resources
from mdcx.consts import GITHUB_ISSUES_URL, IS_WINDOWS, MAIN_PATH
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt

from .bind_utils import set_checkboxes, set_radio_buttons
from .site_priority_dialog import apply_site_priority_theme, refresh_site_priority_ui

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


def configure_native_file_dialogs(window: "MyMAinWindow", switch_on: list[Switch]) -> None:
    """Use the operating system picker while preserving the retired setting value."""
    legacy_qt_dialog_enabled = Switch.QT_DIALOG in switch_on
    window.Ui.checkBox_dialog_qt.setChecked(legacy_qt_dialog_enabled)
    window.Ui.checkBox_dialog_qt.setToolTip("文件和文件夹选择现已统一使用系统自带对话框")
    window.Ui.checkBox_dialog_qt.hide()
    window.options = QFileDialog.Option(0)


def load_config(self: "MyMAinWindow"):
    """
    读取配置文件并绑定到 UI 组件
    """
    errors = manager.load()
    v1_msgs = [e for e in errors if e.startswith("[V1]")]
    if v1_msgs:
        signal_qt.show_log_text(f"\n\t{'\n\t'.join(v1_msgs)}\n\n")
        errors = [e for e in errors if not e.startswith("[V1]")]
    if errors:
        signal_qt.show_log_text(
            f"⚠️ 读取配置文件出错:\n\t{'\n\t'.join(errors)}\n\n"
            "为避免破坏配置文件, 已自动切换为 _failed.json\n"
            f'这是非预期错误, 请提交 <a href="{GITHUB_ISSUES_URL}">GitHub Issue</a>\n'
        )
        manager.path = manager.data_folder / "_failed.json"
        return
    config_folder = manager.data_folder
    config_file = manager.file
    config_path = manager.path

    # 检测配置目录权限
    mdcx_config = True
    if not os.access(config_folder, os.W_OK) or not os.access(config_folder, os.R_OK):
        mdcx_config = False

    if os.path.exists(config_path):
        # ======================================================================================获取配置文件夹中的配置文件列表
        all_config_files = manager.list_configs()
        all_config_files.sort()
        self.Ui.comboBox_change_config.clear()
        self.Ui.comboBox_change_config.addItems(all_config_files)
        if config_file in all_config_files:
            self.Ui.comboBox_change_config.setCurrentIndex(all_config_files.index(config_file))
        else:
            self.Ui.comboBox_change_config.setCurrentIndex(all_config_files.index("config.json"))

        # region escape
        # 排除目录-工具页面
        self.Ui.lineEdit_escape_dir_move.setText(",".join(manager.config.folders))
        # endregion

        # region clean
        # endregion

        # region website
        AllItems = [self.Ui.comboBox_website_all.itemText(i) for i in range(self.Ui.comboBox_website_all.count())]
        # 指定单个刮削网站
        website_single_value = website_display_name(manager.config.selected_site)
        if website_single_value in AllItems:
            self.Ui.comboBox_website_all.setCurrentIndex(AllItems.index(website_single_value))
        else:
            self.Ui.comboBox_website_all.setCurrentIndex(0)
            signal_qt.show_log_text(
                f"⚠️ 指定网站 '{website_single_value}' 不在 UI 网站列表中，已回退为 {self.Ui.comboBox_website_all.itemText(0)}\n"
            )
        # 有码番号刮削网站
        self.Ui.lineEdit_website_youma.setText(
            ",".join(website_display_name(site) for site in manager.config.website_youma)
        )
        # 无码番号刮削网站
        self.Ui.lineEdit_website_wuma.setText(
            ",".join(website_display_name(site) for site in manager.config.website_wuma)
        )
        # 素人番号刮削网站
        self.Ui.lineEdit_website_suren.setText(
            ",".join(website_display_name(site) for site in manager.config.website_suren)
        )
        # FC2番号刮削网站
        self.Ui.lineEdit_website_fc2.setText(
            ",".join(website_display_name(site) for site in manager.config.website_fc2)
        )
        # 欧美番号刮削网站
        self.Ui.lineEdit_website_oumei.setText(
            ",".join(website_display_name(site) for site in manager.config.website_oumei)
        )
        # 国产番号刮削网站
        self.Ui.lineEdit_website_guochan.setText(
            ",".join(website_display_name(site) for site in manager.config.website_guochan)
        )
        # 锁定刮削类型
        _type_labels = ["自动判断", "有码", "无码", "素人", "FC2", "欧美", "国产"]
        _type_values = ["auto", "youma", "wuma", "suren", "fc2", "oumei", "guochan"]
        _fixed_value = manager.config.fixed_scraping_type.value
        _idx = _type_values.index(_fixed_value) if _fixed_value in _type_values else 0
        self.Ui.comboBox_fixed_scraping_type.setCurrentIndex(_idx)
        manager.config.ensure_type_field_configs()

        # 刮削偏好
        scrape_like = manager.config.scrape_like
        if "speed" == scrape_like:
            Flags.scrape_like_text = "速度优先"
        elif "single" == scrape_like:
            Flags.scrape_like_text = "指定网站"
        else:
            Flags.scrape_like_text = "字段优先"

        manager.config.ensure_type_field_configs()
        refresh_site_priority_ui(self)

        # 翻译引擎
        set_checkboxes(
            manager.config.translate_config.translate_by,
            (self.Ui.checkBox_google, Translator.GOOGLE),
            (self.Ui.checkBox_baidu, Translator.BAIDU),
            (self.Ui.checkBox_deepl, Translator.DEEPL),
            (self.Ui.checkBox_deeplx, Translator.DEEPLX),
            (self.Ui.checkBox_llm, Translator.LLM),
        )

        # llm config
        self.Ui.lineEdit_llm_url.setText(str(manager.config.translate_config.llm_url))
        # endregion

        # region common
        # 线程数量
        self.Ui.lcdNumber_thread.display(manager.config.thread_number)
        # 线程延时
        self.Ui.lcdNumber_thread_time.display(manager.config.thread_time)
        # javdb 延时
        self.Ui.lcdNumber_javdb_time.display(manager.config.javdb_time)

        # 刮削模式
        main_mode = manager.config.main_mode
        mode_mapping = {
            1: ("common", "正常模式"),
            2: ("sort", "整理模式"),
            3: ("update", "更新模式"),
            4: ("read", "读取模式"),
        }
        mode_key, mode_text = mode_mapping.get(main_mode, ("common", "正常模式"))
        Flags.main_mode_text = mode_text
        set_radio_buttons(
            mode_key,
            (self.Ui.radioButton_mode_common, "common"),
            (self.Ui.radioButton_mode_sort, "sort"),
            (self.Ui.radioButton_mode_update, "update"),
            (self.Ui.radioButton_mode_read, "read"),
            default=self.Ui.radioButton_mode_common,
        )

        # 有nfo，是否执行更新模式
        # region read_mode
        # endregion

        # 更新模式
        self.Ui.checkBox_update_a.setChecked(False)
        update_mode = manager.config.update_mode

        # 处理 abc 模式的特殊情况
        if update_mode == "abc":
            self.Ui.radioButton_update_b_c.setChecked(True)
            self.Ui.checkBox_update_a.setChecked(True)
        else:
            set_radio_buttons(
                update_mode,
                (self.Ui.radioButton_update_c, "c"),
                (self.Ui.radioButton_update_b_c, "bc"),
                (self.Ui.radioButton_update_d_c, "d"),
                default=self.Ui.radioButton_update_c,
            )

        # 软链接
        set_radio_buttons(
            manager.config.soft_link,
            (self.Ui.radioButton_soft_on, 1),
            (self.Ui.radioButton_hard_on, 2),
            (self.Ui.radioButton_soft_off, 0),
            default=self.Ui.radioButton_soft_off,
        )

        # endregion

        # region file_download
        # endregion

        # region Name_Rule
        # 后缀排序
        self.Ui.lineEdit_suffix_sort.setText(",".join([s.value for s in manager.config.suffix_sort]))
        # 分集命名规则
        set_radio_buttons(
            manager.config.cd_name,
            (self.Ui.radioButton_cd_part_lower, 0),
            (self.Ui.radioButton_cd_part_upper, 1),
            default=self.Ui.radioButton_cd_part_digital,
        )

        cd_char = manager.config.cd_char
        # region cd_char
        # 版本兼容性检查已简化，新配置直接使用枚举列表

        set_checkboxes(
            cd_char,
            # 允许分集识别字母
            (self.Ui.checkBox_cd_part_a, CDChar.LETTER),
            # 允许分集识别字母（重复）
            (self.Ui.checkBox_cd_part_c, CDChar.LETTER),
            # 允许分集识别数字
            (self.Ui.checkBox_cd_part_01, CDChar.DIGITAL),
            (self.Ui.checkBox_cd_part_1_xxx, CDChar.MIDDLE_NUMBER),
            # 下划线分隔符
            (self.Ui.checkBox_cd_part_underline, CDChar.UNDERLINE),
            (self.Ui.checkBox_cd_part_space, CDChar.SPACE),
            (self.Ui.checkBox_cd_part_point, CDChar.POINT),
        )
        # 特殊处理 endc
        self.Ui.checkBox_cd_part_c.setChecked(CDChar.ENDC in cd_char)
        # endregion

        # 图片命名是否包含视频名
        set_radio_buttons(
            manager.config.pic_simple_name,
            (self.Ui.radioButton_pic_with_filename, False),
            default=self.Ui.radioButton_pic_no_filename,
        )
        # 预告片命名是否包含视频名
        set_radio_buttons(
            manager.config.trailer_simple_name,
            (self.Ui.radioButton_trailer_with_filename, False),
            default=self.Ui.radioButton_trailer_no_filename,
        )
        # 画质命名规则
        set_radio_buttons(
            manager.config.hd_name,
            (self.Ui.radioButton_definition_height, "height"),
            default=self.Ui.radioButton_definition_hd,
        )
        # 分辨率获取方式
        set_radio_buttons(
            manager.config.hd_get,
            (self.Ui.radioButton_videosize_video, "video"),
            (self.Ui.radioButton_videosize_path, "path"),
            default=self.Ui.radioButton_videosize_none,
        )
        # endregion

        # region 字幕
        # 中文字幕判断字符
        self.Ui.lineEdit_cnword_char.setText(",".join(manager.config.cnword_char))
        # 中文字幕字符样式
        self.Ui.lineEdit_cnword_style.setText(manager.config.cnword_style.strip("^"))
        # 显示中文字幕字符-视频目录名
        self.Ui.checkBox_foldername.setChecked(manager.config.folder_cnword)
        # 显示中文字幕字符-视频文件名
        self.Ui.checkBox_filename.setChecked(manager.config.file_cnword)
        # 自动添加字幕
        set_radio_buttons(
            manager.config.subtitle_add,
            (self.Ui.radioButton_add_sub_on, True),
            default=self.Ui.radioButton_add_sub_off,
        )
        # endregion

        # region emby
        # emby地址
        self.Ui.lineEdit_emby_url.setText(str(manager.config.emby_url))

        # 网络头像库 gfriends 项目地址
        self.Ui.lineEdit_net_actor_photo.setText(str(manager.config.gfriends_github))
        # endregion

        # region network
        # Refresh dependent controls only after all schema-backed values have
        # reached the UI; otherwise their enabled state can reflect stale data.
        self.settings_controller.binder.load(manager.config)
        self.update_field_priority_try_all_images_state()
        self.update_amazon_strict_pic_verify_state()
        self.Ui.lcdNumber_timeout.display(int(manager.config.timeout))
        self.Ui.lcdNumber_retry.display(int(manager.config.retry))
        self.Ui.lcdNumber_mark_size.display(int(manager.config.mark_size))

        # site config
        site = self.Ui.comboBox_custom_website.currentText()
        if site in Website:
            self.Ui.lineEdit_site_custom_url.setText(manager.config.get_site_url(Website(site)))

        # javdb cookie
        self.set_javdb_cookie.emit(manager.config.javdb)
        # fc2cmadb Cookie
        self.set_fc2ppvdb_cookie.emit(manager.config.fc2ppvdb)
        # javbus cookie
        self.set_javbus_cookie.emit(manager.config.javbus)
        # endregion

        # region other
        # 配置文件目录
        self.Ui.lineEdit_config_folder.setText(str(manager.data_folder))

        rest_time = manager.config.rest_time
        # 换算（秒）
        Flags.rest_time_convert = int(rest_time.total_seconds())

        timed_interval = manager.config.timed_interval
        # 换算（毫秒）
        timed_interval_convert = timed_interval.total_seconds() * 1000
        self.timer_scrape.stop()

        # endregion

        # region switch_on
        switch_on = manager.config.switch_on
        # 定时刮削设置
        if Switch.TIMED_SCRAPE in switch_on:
            self.Ui.checkBox_timed_scrape.setChecked(True)
            self.timer_scrape.start(int(timed_interval_convert))
        else:
            self.Ui.checkBox_timed_scrape.setChecked(False)

        # 其他设置
        self.dark_mode = Switch.DARK_MODE in switch_on
        apply_site_priority_theme(self)
        self.show_hide_logs(Switch.SHOW_LOGS in switch_on)

        # 文件和目录选择统一使用系统原生对话框。旧 qt_dialog 值保留在隐藏控件中，保存配置时不会丢失。
        configure_native_file_dialogs(self, switch_on)
        if IS_WINDOWS:
            self.Ui.checkBox_hide_dock_icon.setEnabled(False)
            self.Ui.checkBox_hide_menu_icon.setEnabled(False)
            try:
                self.tray_icon.show()
            except Exception:
                self.Init_QSystemTrayIcon()
                if not mdcx_config:
                    self.tray_icon.showMessage(
                        f"MDCx {self.localversion}",
                        "配置写入失败！所在目录没有读写权限！",
                        QIcon(resources.icon_ico),
                        3000,
                    )
            if Switch.PASSTHROUGH in switch_on:
                self.Ui.checkBox_highdpi_passthrough.setChecked(True)
            else:
                self.Ui.checkBox_highdpi_passthrough.setChecked(False)
            # Qt 6 的 DPI 舍入策略已在 main.py 启动时直接设置。
            # 保留旧开关用于配置兼容，但不再创建无实际用途的空标记文件。
            legacy_dpi_marker = MAIN_PATH / "highdpi_passthrough"
            try:
                if legacy_dpi_marker.is_file() and legacy_dpi_marker.stat().st_size == 0:
                    legacy_dpi_marker.unlink()
            except OSError:
                pass
        else:
            self.Ui.checkBox_highdpi_passthrough.setEnabled(False)
            if Switch.HIDE_MENU in switch_on:
                self.Ui.checkBox_hide_menu_icon.setChecked(True)
                try:
                    if hasattr(self, "tray_icon"):
                        self.tray_icon.hide()
                except Exception:
                    signal_qt.show_traceback_log(traceback.format_exc())
            else:
                self.Ui.checkBox_hide_menu_icon.setChecked(False)
                try:
                    self.tray_icon.show()
                except Exception:
                    self.Init_QSystemTrayIcon()
                    if not mdcx_config:
                        self.tray_icon.showMessage(
                            f"MDCx {self.localversion}",
                            "配置写入失败！所在目录没有读写权限！",
                            QIcon(resources.icon_ico),
                            3000,
                        )
        # endregion

        # ======================================================================================END
        # 根据是否同意改变清理按钮状态
        self.checkBox_i_agree_clean_clicked()
        try:
            scrape_like_text = Flags.scrape_like_text
            if manager.config.scrape_like == "single":
                scrape_like_text += f" · {manager.config.selected_site.value}"
            if manager.config.soft_link == 1:
                scrape_like_text += " · 软连接开"
            elif manager.config.soft_link == 2:
                scrape_like_text += " · 硬连接开"
            movie_path_text = ";".join(str(path) for path in get_movie_path_setting().movie_paths)
            signal_qt.show_log_text(
                f" 🛠 当前配置：{manager.path} 加载完成！\n "
                f"📂 程序目录：{manager.data_folder} \n "
                f"📂 刮削目录：{movie_path_text} \n "
                f"💠 刮削模式：{Flags.main_mode_text} · {scrape_like_text} \n "
                f"🖥️ 系统信息：{platform.platform()} \n "
                f"🐰 软件版本：{self.localversion} \n"
            )
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
        try:
            # 界面自动调整
            self._windows_auto_adjust()
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)  # type: ignore
        self.activateWindow()
        try:
            # 主界面右上角显示提示信息
            movie_path_text = ";".join(str(path) for path in get_movie_path_setting().movie_paths)
            self.set_label_file_path.emit(f"🎈 当前刮削路径: \n {movie_path_text}")
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
        self.settings_controller.mark_clean()
    else:  # ini不存在，重新创建
        signal_qt.show_log_text(f"Create config file: {config_path} ")
        self.pushButton_init_config_clicked()
