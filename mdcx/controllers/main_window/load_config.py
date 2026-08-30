import os
import platform
import traceback
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileDialog

from mdcx.config.enums import (
    CDChar,
    EmbyAction,
    FieldRule,
    MarkType,
    NfoInclude,
    OutlineShow,
    Switch,
    TagInclude,
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

        # 简介-显示翻译来源、双语显示
        set_checkboxes(
            manager.config.outline_format,
            (self.Ui.checkBox_show_translate_from, OutlineShow.SHOW_FROM),
        )
        set_radio_buttons(
            "zh_jp"
            if OutlineShow.SHOW_ZH_JP in manager.config.outline_format
            else "jp_zh"
            if OutlineShow.SHOW_JP_ZH in manager.config.outline_format
            else "one",
            (self.Ui.radioButton_trans_show_zh_jp, "zh_jp"),
            (self.Ui.radioButton_trans_show_jp_zh, "jp_zh"),
            (self.Ui.radioButton_trans_show_one, "one"),
            default=self.Ui.radioButton_trans_show_one,
        )
        # 写入标签字段的信息
        # region tag_include
        set_checkboxes(
            manager.config.nfo_tag_include,
            (self.Ui.checkBox_tag_actor, TagInclude.ACTOR),
            (self.Ui.checkBox_tag_letters, TagInclude.LETTERS),
            (self.Ui.checkBox_tag_series, TagInclude.SERIES),
            (self.Ui.checkBox_tag_studio, TagInclude.STUDIO),
            (self.Ui.checkBox_tag_publisher, TagInclude.PUBLISHER),
            (self.Ui.checkBox_tag_cnword, TagInclude.CNWORD),
            (self.Ui.checkBox_tag_mosaic, TagInclude.MOSAIC),
            (self.Ui.checkBox_tag_definition, TagInclude.DEFINITION),
        )
        # endregion

        manager.config.ensure_type_field_configs()
        refresh_site_priority_ui(self)

        # 写入nfo的字段 - 新配置直接使用枚举列表，不需要版本兼容性检查
        nfo_include_new = manager.config.nfo_include_new

        set_checkboxes(
            nfo_include_new,
            (self.Ui.checkBox_nfo_sorttitle, NfoInclude.SORTTITLE),
            (self.Ui.checkBox_nfo_originaltitle, NfoInclude.ORIGINALTITLE),
            (self.Ui.checkBox_nfo_title_cd, NfoInclude.TITLE_CD),
            (self.Ui.checkBox_nfo_outline, NfoInclude.OUTLINE),
            (self.Ui.checkBox_nfo_plot, NfoInclude.PLOT_),
            (self.Ui.checkBox_nfo_originalplot, NfoInclude.ORIGINALPLOT),
            (self.Ui.checkBox_outline_cdata, NfoInclude.OUTLINE_NO_CDATA),
            (self.Ui.checkBox_nfo_release, NfoInclude.RELEASE_),
            (self.Ui.checkBox_nfo_relasedate, NfoInclude.RELEASEDATE),
            (self.Ui.checkBox_nfo_premiered, NfoInclude.PREMIERED),
            (self.Ui.checkBox_nfo_country, NfoInclude.COUNTRY),
            (self.Ui.checkBox_nfo_mpaa, NfoInclude.MPAA),
            (self.Ui.checkBox_nfo_customrating, NfoInclude.CUSTOMRATING),
            (self.Ui.checkBox_nfo_year, NfoInclude.YEAR),
            (self.Ui.checkBox_nfo_runtime, NfoInclude.RUNTIME),
            (self.Ui.checkBox_nfo_wanted, NfoInclude.WANTED),
            (self.Ui.checkBox_nfo_score, NfoInclude.SCORE),
            (self.Ui.checkBox_nfo_criticrating, NfoInclude.CRITICRATING),
            (self.Ui.checkBox_nfo_actor, NfoInclude.ACTOR),
            (self.Ui.checkBox_nfo_all_actor, NfoInclude.ACTOR_ALL),
            (self.Ui.checkBox_nfo_director, NfoInclude.DIRECTOR),
            (self.Ui.checkBox_nfo_series, NfoInclude.SERIES),
            (self.Ui.checkBox_nfo_tag, NfoInclude.TAG),
            (self.Ui.checkBox_nfo_genre, NfoInclude.GENRE),
            (self.Ui.checkBox_nfo_actor_set, NfoInclude.ACTOR_SET),
            (self.Ui.checkBox_nfo_set, NfoInclude.SERIES_SET),
            (self.Ui.checkBox_nfo_studio, NfoInclude.STUDIO),
            (self.Ui.checkBox_nfo_maker, NfoInclude.MAKER),
            (self.Ui.checkBox_nfo_publisher, NfoInclude.PUBLISHER),
            (self.Ui.checkBox_nfo_label, NfoInclude.LABEL),
            (self.Ui.checkBox_nfo_poster, NfoInclude.POSTER),
            (self.Ui.checkBox_nfo_cover, NfoInclude.COVER),
            (self.Ui.checkBox_nfo_trailer, NfoInclude.TRAILER),
            (self.Ui.checkBox_nfo_website, NfoInclude.WEBSITE),
        )
        # endregion

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
        # region fields_rule
        # 字段命名规则

        set_checkboxes(
            manager.config.fields_rule,
            # 去除标题后的演员名
            (self.Ui.checkBox_title_del_actor, FieldRule.DEL_ACTOR),
            # 演员去除括号
            (self.Ui.checkBox_actor_del_char, FieldRule.DEL_CHAR),
            # FC2 演员名
            (self.Ui.checkBox_actor_fc2_seller, FieldRule.FC2_SELLER),
            # 素人番号删除前缀数字
            (self.Ui.checkBox_number_del_num, FieldRule.DEL_NUM),
        )
        # endregion

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

        emby_on = manager.config.emby_on
        # 演员信息语言设置
        if EmbyAction.ACTOR_INFO_ZH_CN in emby_on:
            lang = "zh_cn"
        elif EmbyAction.ACTOR_INFO_ZH_TW in emby_on:
            lang = "zh_tw"
        else:
            lang = "ja"

        set_radio_buttons(
            lang,
            (self.Ui.radioButton_actor_info_zh_cn, "zh_cn"),
            (self.Ui.radioButton_actor_info_zh_tw, "zh_tw"),
            (self.Ui.radioButton_actor_info_ja, "ja"),
            default=self.Ui.radioButton_actor_info_ja,
        )
        set_checkboxes(
            emby_on,
            (self.Ui.checkBox_actor_info_translate, EmbyAction.ACTOR_INFO_TRANSLATE),
            (self.Ui.checkBox_actor_info_photo, EmbyAction.ACTOR_INFO_PHOTO),
            (self.Ui.checkBox_actor_photo_ne_backdrop, EmbyAction.GRAPHIS_BACKDROP),
            (self.Ui.checkBox_actor_photo_ne_face, EmbyAction.GRAPHIS_FACE),
            (self.Ui.checkBox_actor_photo_ne_new, EmbyAction.GRAPHIS_NEW),
            (self.Ui.checkBox_actor_photo_auto, EmbyAction.ACTOR_PHOTO_AUTO),
            (self.Ui.checkBox_actor_pic_replace, EmbyAction.ACTOR_REPLACE),
        )
        # 演员信息刮削模式
        info_mode = "all" if EmbyAction.ACTOR_INFO_ALL in emby_on else "miss"
        set_radio_buttons(
            info_mode,
            (self.Ui.radioButton_actor_info_all, "all"),
            (self.Ui.radioButton_actor_info_miss, "miss"),
            default=self.Ui.radioButton_actor_info_miss,
        )
        # 演员照片来源
        photo_source = "local" if EmbyAction.ACTOR_PHOTO_LOCAL in emby_on else "net"
        set_radio_buttons(
            photo_source,
            (self.Ui.radioButton_actor_photo_local, "local"),
            (self.Ui.radioButton_actor_photo_net, "net"),
            default=self.Ui.radioButton_actor_photo_net,
        )
        # 演员照片刮削模式
        photo_mode = "all" if EmbyAction.ACTOR_PHOTO_ALL in emby_on else "miss"
        set_radio_buttons(
            photo_mode,
            (self.Ui.radioButton_actor_photo_all, "all"),
            (self.Ui.radioButton_actor_photo_miss, "miss"),
            default=self.Ui.radioButton_actor_photo_miss,
        )

        # 网络头像库 gfriends 项目地址
        self.Ui.lineEdit_net_actor_photo.setText(str(manager.config.gfriends_github))
        # endregion

        # region mark
        # 水印设置
        # 封面图加水印
        self.Ui.checkBox_poster_mark.setChecked(manager.config.poster_mark != 0)
        # 缩略图加水印
        self.Ui.checkBox_thumb_mark.setChecked(manager.config.thumb_mark != 0)
        # 艺术图加水印
        self.Ui.checkBox_fanart_mark.setChecked(manager.config.fanart_mark != 0)
        # 水印大小
        self.Ui.horizontalSlider_mark_size.setValue(int(manager.config.mark_size))
        self.Ui.lcdNumber_mark_size.display(int(manager.config.mark_size))

        # 启用的水印类型
        set_checkboxes(
            manager.config.mark_type,
            (self.Ui.checkBox_sub, MarkType.SUB),
            (self.Ui.checkBox_censored, MarkType.YOUMA),
            (self.Ui.checkBox_umr, MarkType.UMR),
            (self.Ui.checkBox_leak, MarkType.LEAK),
            (self.Ui.checkBox_uncensored, MarkType.UNCENSORED),
            (self.Ui.checkBox_hd, MarkType.HD),
        )
        # 水印位置是否固定
        set_radio_buttons(
            manager.config.mark_fixed,
            (self.Ui.radioButton_not_fixed_position, "not_fixed"),
            (self.Ui.radioButton_fixed_corner, "corner"),
            (self.Ui.radioButton_fixed_position, "fixed"),
            default=self.Ui.radioButton_fixed_position,
        )
        # 首个水印位置
        set_radio_buttons(
            manager.config.mark_pos,
            (self.Ui.radioButton_top_left, "top_left"),
            (self.Ui.radioButton_top_right, "top_right"),
            (self.Ui.radioButton_bottom_left, "bottom_left"),
            (self.Ui.radioButton_bottom_right, "bottom_right"),
            default=self.Ui.radioButton_top_left,
        )
        # 固定一个位置
        set_radio_buttons(
            manager.config.mark_pos_corner,
            (self.Ui.radioButton_top_left_corner, "top_left"),
            (self.Ui.radioButton_top_right_corner, "top_right"),
            (self.Ui.radioButton_bottom_left_corner, "bottom_left"),
            (self.Ui.radioButton_bottom_right_corner, "bottom_right"),
            default=self.Ui.radioButton_top_left_corner,
        )
        # 高清水印位置
        set_radio_buttons(
            manager.config.mark_pos_hd,
            (self.Ui.radioButton_top_left_hd, "top_left"),
            (self.Ui.radioButton_top_right_hd, "top_right"),
            (self.Ui.radioButton_bottom_left_hd, "bottom_left"),
            (self.Ui.radioButton_bottom_right_hd, "bottom_right"),
            default=self.Ui.radioButton_bottom_right_hd,
        )
        # 字幕水印位置
        set_radio_buttons(
            manager.config.mark_pos_sub,
            (self.Ui.radioButton_top_left_sub, "top_left"),
            (self.Ui.radioButton_top_right_sub, "top_right"),
            (self.Ui.radioButton_bottom_left_sub, "bottom_left"),
            (self.Ui.radioButton_bottom_right_sub, "bottom_right"),
            default=self.Ui.radioButton_top_left_sub,
        )
        # 马赛克水印位置
        set_radio_buttons(
            manager.config.mark_pos_mosaic,
            (self.Ui.radioButton_top_left_mosaic, "top_left"),
            (self.Ui.radioButton_top_right_mosaic, "top_right"),
            (self.Ui.radioButton_bottom_left_mosaic, "bottom_left"),
            (self.Ui.radioButton_bottom_right_mosaic, "bottom_right"),
            default=self.Ui.radioButton_top_right_mosaic,
        )
        # endregion

        # region network
        # Refresh dependent controls only after all schema-backed values have
        # reached the UI; otherwise their enabled state can reflect stale data.
        self.settings_controller.binder.load(manager.config)
        self.update_field_priority_try_all_images_state()
        self.update_amazon_strict_pic_verify_state()
        self.Ui.lcdNumber_timeout.display(int(manager.config.timeout))
        self.Ui.lcdNumber_retry.display(int(manager.config.retry))

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
        # 版本兼容性检查已简化，新配置直接使用枚举列表

        # 基础开关设置
        set_checkboxes(
            switch_on,
            (self.Ui.checkBox_auto_start, Switch.AUTO_START),
            (self.Ui.checkBox_auto_exit, Switch.AUTO_EXIT),
            (self.Ui.checkBox_rest_scrape, Switch.REST_SCRAPE),
            (self.Ui.checkBox_remain_task, Switch.REMAIN_TASK),
            (self.Ui.checkBox_show_dialog_exit, Switch.SHOW_DIALOG_EXIT),
            (self.Ui.checkBox_show_dialog_stop_scrape, Switch.SHOW_DIALOG_STOP_SCRAPE),
            (self.Ui.checkBox_dark_mode, Switch.DARK_MODE),
            (self.Ui.checkBox_copy_netdisk_nfo, Switch.COPY_NETDISK_NFO),
            (self.Ui.checkBox_theporndb_hash, Switch.THEPORNDB_NO_HASH),
            (self.Ui.checkBox_sortmode_delpic, Switch.SORT_DEL),
        )

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

        # 隐藏窗口设置
        if Switch.HIDE_CLOSE in switch_on:
            hide_mode = "close"
        elif Switch.HIDE_MINI in switch_on:
            hide_mode = "mini"
        else:
            hide_mode = "none"

        set_radio_buttons(
            hide_mode,
            (self.Ui.radioButton_hide_close, "close"),
            (self.Ui.radioButton_hide_mini, "mini"),
            (self.Ui.radioButton_hide_none, "none"),
            default=self.Ui.radioButton_hide_none,
        )

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
    else:  # ini不存在，重新创建
        signal_qt.show_log_text(f"Create config file: {config_path} ")
        self.pushButton_init_config_clicked()
