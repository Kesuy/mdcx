import platform
import re
import traceback
from contextlib import suppress
from typing import TYPE_CHECKING

from pydantic import HttpUrl, ValidationError
from PyQt6.QtCore import Qt

from mdcx.config.enums import (
    CDChar,
    FixedScrapingType,
    SuffixSort,
    Translator,
    Website,
    website_from_display_name,
)
from mdcx.config.extend import get_movie_path_setting
from mdcx.config.manager import manager
from mdcx.config.models import SiteConfig, str_to_list
from mdcx.models.flags import Flags
from mdcx.signals import signal_qt
from mdcx.tools.actress_db import ActressDB

from .bind_utils import get_checkbox, get_checkboxes, get_radio_buttons
from .site_priority_dialog import refresh_site_priority_ui

if TYPE_CHECKING:
    from .main_window import MyMAinWindow


def save_config(self: "MyMAinWindow"):
    """
    从 UI 获取配置并保存到 config 对象中, 并更新配置文件
    """
    # Save all schema-backed fields first so specialized normalization below
    # always reads the latest validated UI values.
    self.settings_controller.binder.save(manager.config)

    # region media & escape
    # endregion

    # region clean
    # endregion

    # region website
    # 网站相关字段需要转换为枚举或列表
    website_single_text = self.Ui.comboBox_website_all.currentText()
    try:
        manager.config.selected_site = website_from_display_name(website_single_text)
    except ValueError:
        manager.config.selected_site = Website.AIRAV_CC  # 默认值
    if manager.config.selected_site == Website.AIRAV:
        manager.config.selected_site = Website.AIRAV_CC

    def get_sites(text: str) -> list[Website]:
        return list(
            dict.fromkeys(
                website_from_display_name(site) for site in str_to_list(text, ",") if site != Website.AIRAV.value
            )
        )

    manager.config.website_youma = get_sites(self.Ui.lineEdit_website_youma.text())
    manager.config.website_wuma = get_sites(self.Ui.lineEdit_website_wuma.text())
    manager.config.website_suren = get_sites(self.Ui.lineEdit_website_suren.text())
    manager.config.website_fc2 = get_sites(self.Ui.lineEdit_website_fc2.text())
    manager.config.website_oumei = get_sites(self.Ui.lineEdit_website_oumei.text())
    manager.config.website_guochan = get_sites(self.Ui.lineEdit_website_guochan.text())
    _type_values = ["auto", "youma", "wuma", "suren", "fc2", "oumei", "guochan"]
    _fixed_idx = self.Ui.comboBox_fixed_scraping_type.currentIndex()
    manager.config.fixed_scraping_type = FixedScrapingType(_type_values[_fixed_idx])

    manager.config.fill_missing_type_field_configs()
    refresh_site_priority_ui(self)

    # 注意：whole_fields 和 none_fields 已弃用，不再设置这些字段
    # 它们的功能已经通过新的字段配置API来实现

    manager.config.translate_config.translate_by = get_checkboxes(
        (self.Ui.checkBox_google, Translator.GOOGLE),
        (self.Ui.checkBox_baidu, Translator.BAIDU),
        (self.Ui.checkBox_deepl, Translator.DEEPL),
        (self.Ui.checkBox_deeplx, Translator.DEEPLX),
        (self.Ui.checkBox_llm, Translator.LLM),
    )
    llm_url_text = self.Ui.lineEdit_llm_url.text()
    if llm_url_text:
        manager.config.translate_config.llm_url = HttpUrl(llm_url_text)
    # endregion

    # region common
    # 主模式设置
    manager.config.main_mode = get_radio_buttons(
        (self.Ui.radioButton_mode_common, 1),
        (self.Ui.radioButton_mode_sort, 2),
        (self.Ui.radioButton_mode_update, 3),
        (self.Ui.radioButton_mode_read, 4),
        default=1,
    )

    # update 模式设置
    if self.Ui.radioButton_update_c.isChecked():
        manager.config.update_mode = "c"
    elif self.Ui.radioButton_update_b_c.isChecked():
        manager.config.update_mode = "abc" if self.Ui.checkBox_update_a.isChecked() else "bc"
    elif self.Ui.radioButton_update_d_c.isChecked():
        manager.config.update_mode = "d"
    else:
        manager.config.update_mode = "c"
    # 链接模式设置
    if self.Ui.radioButton_soft_on.isChecked():  # 软链接开
        manager.config.soft_link = 1
    elif self.Ui.radioButton_hard_on.isChecked():  # 硬链接开
        manager.config.soft_link = 2
    else:  # 软链接关
        manager.config.soft_link = 0

    # endregion

    # region download
    manager.config.amazon_skip_poster_size_precheck = (
        self.Ui.checkBox_amazon_big_pic.isChecked() and self.Ui.checkBox_amazon_skip_poster_size_precheck.isChecked()
    )
    manager.config.amazon_strict_pic_verify = (
        self.Ui.checkBox_amazon_big_pic.isChecked() and self.Ui.checkBox_amazon_strict_pic_verify.isChecked()
    )
    # endregion

    # region name

    suffix_sort_text = self.Ui.lineEdit_suffix_sort.text()
    suffix_sort_list = []
    for item in str_to_list(suffix_sort_text):
        if item == "moword":
            suffix_sort_list.append(SuffixSort.MOWORD)
        elif item == "cnword":
            suffix_sort_list.append(SuffixSort.CNWORD)
        elif item == "definition":
            suffix_sort_list.append(SuffixSort.DEFINITION)
    manager.config.suffix_sort = suffix_sort_list

    release_rule = manager.config.release_rule
    manager.config.release_rule = re.sub(r'[\\/:*?"<>|\r\n]+', "-", release_rule).strip()

    # 分集命名规则
    manager.config.cd_name = get_radio_buttons(
        (self.Ui.radioButton_cd_part_lower, 0),
        (self.Ui.radioButton_cd_part_upper, 1),
        default=2,
    )

    manager.config.cd_char = get_checkboxes(
        (self.Ui.checkBox_cd_part_a, CDChar.LETTER),
        (self.Ui.checkBox_cd_part_c, CDChar.ENDC),
        (self.Ui.checkBox_cd_part_01, CDChar.DIGITAL),
        (self.Ui.checkBox_cd_part_1_xxx, CDChar.MIDDLE_NUMBER),
        (self.Ui.checkBox_cd_part_underline, CDChar.UNDERLINE),
        (self.Ui.checkBox_cd_part_space, CDChar.SPACE),
        (self.Ui.checkBox_cd_part_point, CDChar.POINT),
    )

    # 图片和预告片命名规则
    manager.config.pic_simple_name = not self.Ui.radioButton_pic_with_filename.isChecked()
    manager.config.trailer_simple_name = not self.Ui.radioButton_trailer_with_filename.isChecked()
    manager.config.hd_name = "height" if self.Ui.radioButton_definition_height.isChecked() else "hd"

    # 分辨率获取方式
    manager.config.hd_get = get_radio_buttons(
        (self.Ui.radioButton_videosize_video, "video"),
        (self.Ui.radioButton_videosize_path, "path"),
        default="none",
    )
    # endregion

    # region subtitle
    cnword_char_text = self.Ui.lineEdit_cnword_char.text()
    manager.config.cnword_char = str_to_list(cnword_char_text)
    manager.config.cnword_style = self.Ui.lineEdit_cnword_style.text()  # 中文字幕字符样式
    manager.config.folder_cnword = get_checkbox(self.Ui.checkBox_foldername)
    manager.config.file_cnword = get_checkbox(self.Ui.checkBox_filename)
    manager.config.subtitle_add = get_checkbox(self.Ui.radioButton_add_sub_on)
    # endregion

    # region emby
    emby_url = self.Ui.lineEdit_emby_url.text()  # emby地址
    emby_url = emby_url.replace("：", ":").strip("/ ")
    if emby_url and "://" not in emby_url:
        emby_url = "http://" + emby_url
    if emby_url:
        manager.config.emby_url = HttpUrl(emby_url)
    gfriends_github = self.Ui.lineEdit_net_actor_photo.text().strip(" /")  # gfriends github 项目地址
    if not gfriends_github:
        gfriends_github = "https://github.com/gfriends/gfriends"
    elif "://" not in gfriends_github:
        gfriends_github = "https://" + gfriends_github
    manager.config.gfriends_github = HttpUrl(gfriends_github)
    if manager.config.use_database:
        ActressDB.init_db()

    # region network
    site = self.Ui.comboBox_custom_website.currentText()
    if site in Website and site != Website.AIRAV.value:
        site = Website(site)
        url = self.Ui.lineEdit_site_custom_url.text().strip("/ ")
        if url:
            with suppress(ValidationError):
                manager.config.site_configs.setdefault(site, SiteConfig()).custom_url = HttpUrl(url)
        elif site in manager.config.site_configs:
            manager.config.site_configs[site].custom_url = None

    if manager.config.javdb:
        manager.config.javdb = manager.config.javdb.replace("locale=en", "locale=zh")
    # endregion

    # 保存
    manager.save()

    # 根据配置更新界面显示
    scrape_like = manager.config.scrape_like
    if "speed" == scrape_like:
        Flags.scrape_like_text = "速度优先"
    elif "single" == scrape_like:
        Flags.scrape_like_text = "指定网站"
    else:
        Flags.scrape_like_text = "字段优先"

    main_mode = int(manager.config.main_mode)  # 刮削模式
    mode_mapping = {
        1: ("common", "正常模式"),
        2: ("sort", "整理模式"),
        3: ("update", "更新模式"),
        4: ("read", "读取模式"),
    }

    mode_key, mode_text = mode_mapping.get(main_mode, ("common", "正常模式"))
    Flags.main_mode_text = mode_text

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
            f" 🛠 当前配置：{manager.path} 保存完成！\n "
            f"📂 程序目录：{manager.data_folder} \n "
            f"📂 刮削目录：{movie_path_text} \n "
            f"💠 刮削模式：{Flags.main_mode_text} · {scrape_like_text} \n "
            f"🖥️ 系统信息：{platform.platform()} \n "
            f"🐰 软件版本：{self.localversion} \n"
        )
    except Exception:
        signal_qt.show_traceback_log(traceback.format_exc())
    self.settings_controller.mark_clean()
    try:
        self._windows_auto_adjust()  # 界面自动调整
    except Exception:
        signal_qt.show_traceback_log(traceback.format_exc())
    self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)  # type: ignore
    self.activateWindow()
    try:
        movie_path_text = ";".join(str(path) for path in get_movie_path_setting().movie_paths)
        self.set_label_file_path.emit(f"🎈 当前刮削路径: \n {movie_path_text}")  # 主界面右上角显示提示信息
    except Exception:
        signal_qt.show_traceback_log(traceback.format_exc())
