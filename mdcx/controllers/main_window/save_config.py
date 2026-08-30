import platform
import re
import traceback
from contextlib import suppress
from typing import TYPE_CHECKING

from pydantic import HttpUrl, ValidationError
from PyQt6.QtCore import Qt

from mdcx.config.enums import (
    CDChar,
    CleanAction,
    DownloadableFile,
    EmbyAction,
    FieldRule,
    FixedScrapingType,
    HDPicSource,
    KeepableFile,
    Language,
    MarkType,
    NfoInclude,
    NoEscape,
    OutlineShow,
    ReadMode,
    SuffixSort,
    Switch,
    TagInclude,
    Translator,
    Website,
    website_from_display_name,
)
from mdcx.config.extend import get_movie_path_setting
from mdcx.config.manager import manager
from mdcx.config.models import SiteConfig, str_to_list
from mdcx.gen.field_enums import CrawlerResultFields
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
    field_mapping = {
        "title": CrawlerResultFields.TITLE,
        "outline": CrawlerResultFields.OUTLINE,
        "actor": CrawlerResultFields.ACTORS,
        "tag": CrawlerResultFields.TAGS,
        "series": CrawlerResultFields.SERIES,
        "studio": CrawlerResultFields.STUDIO,
        "publisher": CrawlerResultFields.PUBLISHER,
        "director": CrawlerResultFields.DIRECTORS,
        "poster": CrawlerResultFields.POSTER,
        "thumb": CrawlerResultFields.THUMB,
        "extrafanart": CrawlerResultFields.EXTRAFANART,
        "score": CrawlerResultFields.SCORE,
        "release": CrawlerResultFields.RELEASE,
        "runtime": CrawlerResultFields.RUNTIME,
        "trailer": CrawlerResultFields.TRAILER,
        "wanted": CrawlerResultFields.WANTED,
    }

    # Save all schema-backed fields first so specialized normalization below
    # always reads the latest validated UI values.
    self.settings_controller.binder.save(manager.config)

    # region media & escape
    manager.config.no_escape = get_checkboxes(
        (self.Ui.checkBox_no_escape_file, NoEscape.NO_SKIP_SMALL_FILE),
        (self.Ui.checkBox_no_escape_dir, NoEscape.FOLDER),
        (self.Ui.checkBox_skip_success_file, NoEscape.SKIP_SUCCESS_FILE),
        (self.Ui.checkBox_record_success_file, NoEscape.RECORD_SUCCESS_FILE),
        (self.Ui.checkBox_check_symlink, NoEscape.CHECK_SYMLINK),
        (self.Ui.checkBox_check_symlink_definition, NoEscape.SYMLINK_DEFINITION),
    )
    # endregion

    # region clean
    manager.config.clean_enable = get_checkboxes(
        (self.Ui.checkBox_clean_file_ext, CleanAction.CLEAN_EXT),
        (self.Ui.checkBox_clean_file_name, CleanAction.CLEAN_NAME),
        (self.Ui.checkBox_clean_file_contains, CleanAction.CLEAN_CONTAINS),
        (self.Ui.checkBox_clean_file_size, CleanAction.CLEAN_SIZE),
        (self.Ui.checkBox_clean_excluded_file_ext, CleanAction.CLEAN_IGNORE_EXT),
        (self.Ui.checkBox_clean_excluded_file_contains, CleanAction.CLEAN_IGNORE_CONTAINS),
        (self.Ui.checkBox_i_understand_clean, CleanAction.I_KNOW),
        (self.Ui.checkBox_i_agree_clean, CleanAction.I_AGREE),
        (self.Ui.checkBox_auto_clean, CleanAction.AUTO_CLEAN),
    )
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

    manager.config.scrape_like = get_radio_buttons(
        (self.Ui.radioButton_scrape_speed, "speed"), (self.Ui.radioButton_scrape_info, "info"), default="single"
    )
    manager.config.field_priority_try_all_images = get_checkbox(self.Ui.checkBox_field_priority_try_all_images)

    # 标题字段配置
    title_language = get_radio_buttons(
        (self.Ui.radioButton_title_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_title_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["title"], title_language)
    manager.config.set_field_translate(field_mapping["title"], get_checkbox(self.Ui.checkBox_title_translate))

    # 简介字段配置
    outline_language = get_radio_buttons(
        (self.Ui.radioButton_outline_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_outline_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["outline"], outline_language)
    manager.config.set_field_translate(field_mapping["outline"], get_checkbox(self.Ui.checkBox_outline_translate))
    manager.config.outline_format = get_checkboxes(
        (self.Ui.checkBox_show_translate_from, OutlineShow.SHOW_FROM),
        (self.Ui.radioButton_trans_show_zh_jp, OutlineShow.SHOW_ZH_JP),
        (self.Ui.radioButton_trans_show_jp_zh, OutlineShow.SHOW_JP_ZH),
    )

    # 演员字段配置
    actor_language = get_radio_buttons(
        (self.Ui.radioButton_actor_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_actor_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["actor"], actor_language)
    manager.config.set_field_translate(field_mapping["actor"], get_checkbox(self.Ui.checkBox_actor_translate))
    # all_actors
    manager.config.set_field_language(CrawlerResultFields.ALL_ACTORS, actor_language)
    manager.config.set_field_translate(CrawlerResultFields.ALL_ACTORS, get_checkbox(self.Ui.checkBox_actor_translate))

    # 标签字段配置
    tag_language = get_radio_buttons(
        (self.Ui.radioButton_tag_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_tag_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["tag"], tag_language)
    manager.config.set_field_translate(field_mapping["tag"], get_checkbox(self.Ui.checkBox_tag_translate))

    manager.config.nfo_tag_include = get_checkboxes(
        (self.Ui.checkBox_tag_actor, TagInclude.ACTOR),
        (self.Ui.checkBox_tag_letters, TagInclude.LETTERS),
        (self.Ui.checkBox_tag_series, TagInclude.SERIES),
        (self.Ui.checkBox_tag_studio, TagInclude.STUDIO),
        (self.Ui.checkBox_tag_publisher, TagInclude.PUBLISHER),
        (self.Ui.checkBox_tag_cnword, TagInclude.CNWORD),
        (self.Ui.checkBox_tag_mosaic, TagInclude.MOSAIC),
        (self.Ui.checkBox_tag_definition, TagInclude.DEFINITION),
    )

    # 系列字段配置
    series_language = get_radio_buttons(
        (self.Ui.radioButton_series_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_series_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["series"], series_language)
    manager.config.set_field_translate(field_mapping["series"], get_checkbox(self.Ui.checkBox_series_translate))

    # 工作室字段配置
    studio_language = get_radio_buttons(
        (self.Ui.radioButton_studio_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_studio_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["studio"], studio_language)
    manager.config.set_field_translate(field_mapping["studio"], get_checkbox(self.Ui.checkBox_studio_translate))

    # 发行商字段配置
    publisher_language = get_radio_buttons(
        (self.Ui.radioButton_publisher_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_publisher_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["publisher"], publisher_language)
    manager.config.set_field_translate(field_mapping["publisher"], get_checkbox(self.Ui.checkBox_publisher_translate))

    # 导演字段配置
    director_language = get_radio_buttons(
        (self.Ui.radioButton_director_zh_cn, Language.ZH_CN),
        (self.Ui.radioButton_director_zh_tw, Language.ZH_TW),
        default=Language.JP,
    )
    manager.config.set_field_language(field_mapping["director"], director_language)
    manager.config.set_field_translate(field_mapping["director"], get_checkbox(self.Ui.checkBox_director_translate))

    manager.config.fill_missing_type_field_configs()
    refresh_site_priority_ui(self)

    # 注意：whole_fields 和 none_fields 已弃用，不再设置这些字段
    # 它们的功能已经通过新的字段配置API来实现

    # region nfo
    manager.config.nfo_include_new = get_checkboxes(
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

    manager.config.read_mode = get_checkboxes(
        (self.Ui.checkBox_read_has_nfo_update, ReadMode.HAS_NFO_UPDATE),
        (self.Ui.checkBox_read_no_nfo_scrape, ReadMode.NO_NFO_SCRAPE),
        (self.Ui.checkBox_read_download_file_again, ReadMode.READ_DOWNLOAD_AGAIN),
        (self.Ui.checkBox_read_update_nfo, ReadMode.READ_UPDATE_NFO),
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
    manager.config.download_files = get_checkboxes(
        (self.Ui.checkBox_download_poster, DownloadableFile.POSTER),
        (self.Ui.checkBox_download_thumb, DownloadableFile.THUMB),
        (self.Ui.checkBox_download_fanart, DownloadableFile.FANART),
        (self.Ui.checkBox_download_extrafanart, DownloadableFile.EXTRAFANART),
        (self.Ui.checkBox_download_trailer, DownloadableFile.TRAILER),
        (self.Ui.checkBox_download_nfo, DownloadableFile.NFO),
        (self.Ui.checkBox_extras, DownloadableFile.EXTRAFANART_EXTRAS),
        (self.Ui.checkBox_download_extrafanart_copy, DownloadableFile.EXTRAFANART_COPY),
        (self.Ui.checkBox_theme_videos, DownloadableFile.THEME_VIDEOS),
        (self.Ui.checkBox_ignore_pic_fail, DownloadableFile.IGNORE_PIC_FAIL),
        (self.Ui.checkBox_ignore_youma, DownloadableFile.IGNORE_YOUMA),
        (self.Ui.checkBox_poster_auto_best, DownloadableFile.POSTER_AUTO_BEST),
        (self.Ui.checkBox_ignore_wuma, DownloadableFile.IGNORE_WUMA),
        (self.Ui.checkBox_ignore_oumei, DownloadableFile.IGNORE_OUMEI),
        (self.Ui.checkBox_ignore_fc2, DownloadableFile.IGNORE_FC2),
        (self.Ui.checkBox_ignore_guochan, DownloadableFile.IGNORE_GUOCHAN),
        (self.Ui.checkBox_ignore_size, DownloadableFile.IGNORE_SIZE),
    )

    manager.config.keep_files = get_checkboxes(
        (self.Ui.checkBox_old_poster, KeepableFile.POSTER),
        (self.Ui.checkBox_old_thumb, KeepableFile.THUMB),
        (self.Ui.checkBox_old_fanart, KeepableFile.FANART),
        (self.Ui.checkBox_old_extrafanart, KeepableFile.EXTRAFANART),
        (self.Ui.checkBox_old_trailer, KeepableFile.TRAILER),
        (self.Ui.checkBox_old_nfo, KeepableFile.NFO),
        (self.Ui.checkBox_old_extrafanart_copy, KeepableFile.EXTRAFANART_COPY),
        (self.Ui.checkBox_old_theme_videos, KeepableFile.THEME_VIDEOS),
    )

    manager.config.download_hd_pics = get_checkboxes(
        (self.Ui.checkBox_amazon_big_pic, HDPicSource.AMAZON),
    )
    manager.config.amazon_skip_poster_size_precheck = (
        self.Ui.checkBox_amazon_big_pic.isChecked() and self.Ui.checkBox_amazon_skip_poster_size_precheck.isChecked()
    )
    manager.config.amazon_strict_pic_verify = (
        self.Ui.checkBox_amazon_big_pic.isChecked() and self.Ui.checkBox_amazon_strict_pic_verify.isChecked()
    )
    # endregion

    # region name

    manager.config.fields_rule = get_checkboxes(
        (self.Ui.checkBox_title_del_actor, FieldRule.DEL_ACTOR),
        (self.Ui.checkBox_actor_del_char, FieldRule.DEL_CHAR),
        (self.Ui.checkBox_actor_fc2_seller, FieldRule.FC2_SELLER),
        (self.Ui.checkBox_number_del_num, FieldRule.DEL_NUM),
    )

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

    # 构建 emby_on 配置
    actor_info_lang = get_radio_buttons(
        (self.Ui.radioButton_actor_info_zh_cn, EmbyAction.ACTOR_INFO_ZH_CN),
        (self.Ui.radioButton_actor_info_zh_tw, EmbyAction.ACTOR_INFO_ZH_TW),
        default=EmbyAction.ACTOR_INFO_JA,
    )
    actor_info_mode = get_radio_buttons(
        (self.Ui.radioButton_actor_info_all, EmbyAction.ACTOR_INFO_ALL), default=EmbyAction.ACTOR_INFO_MISS
    )
    actor_photo_source = get_radio_buttons(
        (self.Ui.radioButton_actor_photo_net, EmbyAction.ACTOR_PHOTO_NET), default=EmbyAction.ACTOR_PHOTO_LOCAL
    )
    actor_photo_mode = get_radio_buttons(
        (self.Ui.radioButton_actor_photo_all, EmbyAction.ACTOR_PHOTO_ALL), default=EmbyAction.ACTOR_PHOTO_MISS
    )
    emby_actions = [actor_info_lang, actor_info_mode, actor_photo_source, actor_photo_mode]

    # 添加其他emby选项
    emby_actions.extend(
        get_checkboxes(
            (self.Ui.checkBox_actor_info_translate, EmbyAction.ACTOR_INFO_TRANSLATE),
            (self.Ui.checkBox_actor_info_photo, EmbyAction.ACTOR_INFO_PHOTO),
            (self.Ui.checkBox_actor_photo_ne_backdrop, EmbyAction.GRAPHIS_BACKDROP),
            (self.Ui.checkBox_actor_photo_ne_face, EmbyAction.GRAPHIS_FACE),
            (self.Ui.checkBox_actor_photo_ne_new, EmbyAction.GRAPHIS_NEW),
            (self.Ui.checkBox_actor_photo_auto, EmbyAction.ACTOR_PHOTO_AUTO),
            (self.Ui.checkBox_actor_pic_replace, EmbyAction.ACTOR_REPLACE),
        )
    )

    manager.config.emby_on = emby_actions
    # endregion

    # region mark
    manager.config.poster_mark = 1 if self.Ui.checkBox_poster_mark.isChecked() else 0
    manager.config.thumb_mark = 1 if self.Ui.checkBox_thumb_mark.isChecked() else 0
    manager.config.fanart_mark = 1 if self.Ui.checkBox_fanart_mark.isChecked() else 0
    manager.config.mark_size = self.Ui.horizontalSlider_mark_size.value()  # 水印大小

    manager.config.mark_type = get_checkboxes(
        (self.Ui.checkBox_sub, MarkType.SUB),
        (self.Ui.checkBox_censored, MarkType.YOUMA),
        (self.Ui.checkBox_umr, MarkType.UMR),
        (self.Ui.checkBox_leak, MarkType.LEAK),
        (self.Ui.checkBox_uncensored, MarkType.UNCENSORED),
        (self.Ui.checkBox_hd, MarkType.HD),
    )

    # 水印位置设置
    manager.config.mark_fixed = get_radio_buttons(
        (self.Ui.radioButton_not_fixed_position, "not_fixed"),
        (self.Ui.radioButton_fixed_corner, "corner"),
        default="fixed",
    )
    manager.config.mark_pos = get_radio_buttons(
        (self.Ui.radioButton_top_left, "top_left"),
        (self.Ui.radioButton_top_right, "top_right"),
        (self.Ui.radioButton_bottom_left, "bottom_left"),
        (self.Ui.radioButton_bottom_right, "bottom_right"),
        default="top_left",
    )
    manager.config.mark_pos_corner = get_radio_buttons(
        (self.Ui.radioButton_top_left_corner, "top_left"),
        (self.Ui.radioButton_top_right_corner, "top_right"),
        (self.Ui.radioButton_bottom_left_corner, "bottom_left"),
        (self.Ui.radioButton_bottom_right_corner, "bottom_right"),
        default="top_left",
    )
    manager.config.mark_pos_hd = get_radio_buttons(
        (self.Ui.radioButton_top_left_hd, "top_left"),
        (self.Ui.radioButton_top_right_hd, "top_right"),
        (self.Ui.radioButton_bottom_left_hd, "bottom_left"),
        (self.Ui.radioButton_bottom_right_hd, "bottom_right"),
        default="top_left",
    )
    manager.config.mark_pos_sub = get_radio_buttons(
        (self.Ui.radioButton_top_left_sub, "top_left"),
        (self.Ui.radioButton_top_right_sub, "top_right"),
        (self.Ui.radioButton_bottom_left_sub, "bottom_left"),
        (self.Ui.radioButton_bottom_right_sub, "bottom_right"),
        default="top_left",
    )
    manager.config.mark_pos_mosaic = get_radio_buttons(
        (self.Ui.radioButton_top_left_mosaic, "top_left"),
        (self.Ui.radioButton_top_right_mosaic, "top_right"),
        (self.Ui.radioButton_bottom_left_mosaic, "bottom_left"),
        (self.Ui.radioButton_bottom_right_mosaic, "bottom_right"),
        default="top_left",
    )
    # endregion

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

    # region other
    # 开关汇总和其他设置
    show_logs_value = not self.Ui.textBrowser_log_main_2.isHidden()
    switch_actions = get_checkboxes(
        (self.Ui.checkBox_auto_start, Switch.AUTO_START),
        (self.Ui.checkBox_auto_exit, Switch.AUTO_EXIT),
        (self.Ui.checkBox_rest_scrape, Switch.REST_SCRAPE),
        (self.Ui.checkBox_timed_scrape, Switch.TIMED_SCRAPE),
        (self.Ui.checkBox_remain_task, Switch.REMAIN_TASK),
        (self.Ui.checkBox_show_dialog_exit, Switch.SHOW_DIALOG_EXIT),
        (self.Ui.checkBox_show_dialog_stop_scrape, Switch.SHOW_DIALOG_STOP_SCRAPE),
        (self.Ui.checkBox_sortmode_delpic, Switch.SORT_DEL),
        (self.Ui.checkBox_dialog_qt, Switch.QT_DIALOG),
        (self.Ui.checkBox_theporndb_hash, Switch.THEPORNDB_NO_HASH),
        (self.Ui.checkBox_hide_dock_icon, Switch.HIDE_DOCK),
        (self.Ui.checkBox_highdpi_passthrough, Switch.PASSTHROUGH),
        (self.Ui.checkBox_hide_menu_icon, Switch.HIDE_MENU),
        (self.Ui.checkBox_dark_mode, Switch.DARK_MODE),
        (self.Ui.checkBox_copy_netdisk_nfo, Switch.COPY_NETDISK_NFO),
    )

    # 手动添加 show_logs 设置
    if show_logs_value:
        switch_actions.append(Switch.SHOW_LOGS)

    # 添加隐藏设置
    switch_actions.append(
        get_radio_buttons(
            (self.Ui.radioButton_hide_close, Switch.HIDE_CLOSE),
            (self.Ui.radioButton_hide_mini, Switch.HIDE_MINI),
            default=Switch.HIDE_NONE,
        )
    )

    manager.config.switch_on = switch_actions

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
