from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mdcx.config.enums import EmbyAction, FieldRule, MarkType, NfoInclude, OutlineShow, Switch, TagInclude

from .config_binding import CompositeBinding, _resolve


@dataclass(frozen=True)
class FlagListSpec:
    path: str
    choices: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ChoiceGroupSpec:
    choices: tuple[tuple[str, Any], ...]
    default: Any


@dataclass(frozen=True)
class CompositeListSpec:
    """One persisted list made from independent flags and exclusive groups."""

    path: str
    flags: tuple[tuple[str, Any], ...] = ()
    groups: tuple[ChoiceGroupSpec, ...] = ()


@dataclass(frozen=True)
class ScalarChoiceSpec:
    path: str
    choices: tuple[tuple[str, Any], ...]
    default: Any


def _flag_list_binding(spec: FlagListSpec) -> CompositeBinding:
    known = {value for _widget, value in spec.choices}

    def load(ui: object, config: object) -> None:
        owner, name = _resolve(config, spec.path)
        selected = getattr(owner, name)
        for widget, value in spec.choices:
            getattr(ui, widget).setChecked(value in selected)

    def save(ui: object, config: object) -> None:
        owner, name = _resolve(config, spec.path)
        previous = getattr(owner, name)
        values = [value for widget, value in spec.choices if getattr(ui, widget).isChecked()]
        values.extend(value for value in previous if value not in known)
        setattr(owner, name, values)

    return CompositeBinding(spec.path, load, save)


def _composite_list_binding(spec: CompositeListSpec) -> CompositeBinding:
    known = {value for _widget, value in spec.flags}
    known.update(value for group in spec.groups for _widget, value in group.choices)

    def load(ui: object, config: object) -> None:
        owner, name = _resolve(config, spec.path)
        selected = getattr(owner, name)
        for widget, value in spec.flags:
            getattr(ui, widget).setChecked(value in selected)
        for group in spec.groups:
            widget = next((widget for widget, value in group.choices if value in selected), None)
            if widget is None:
                widget = next(widget for widget, value in group.choices if value == group.default)
            getattr(ui, widget).setChecked(True)

    def save(ui: object, config: object) -> None:
        owner, name = _resolve(config, spec.path)
        previous = getattr(owner, name)
        values = [value for widget, value in spec.flags if getattr(ui, widget).isChecked()]
        for group in spec.groups:
            value = next(
                (value for widget, value in group.choices if getattr(ui, widget).isChecked()),
                group.default,
            )
            if value is not None:
                values.append(value)
        values.extend(value for value in previous if value not in known)
        setattr(owner, name, values)

    return CompositeBinding(spec.path, load, save)


def _scalar_choice_binding(spec: ScalarChoiceSpec) -> CompositeBinding:
    def load(ui: object, config: object) -> None:
        owner, name = _resolve(config, spec.path)
        value = getattr(owner, name)
        widget = next((widget for widget, choice in spec.choices if choice == value), None)
        if widget is None:
            widget = next(widget for widget, choice in spec.choices if choice == spec.default)
        getattr(ui, widget).setChecked(True)

    def save(ui: object, config: object) -> None:
        owner, name = _resolve(config, spec.path)
        value = next(
            (choice for widget, choice in spec.choices if getattr(ui, widget).isChecked()),
            spec.default,
        )
        setattr(owner, name, value)

    return CompositeBinding(spec.path, load, save)


def build_settings_composites() -> list[CompositeBinding]:
    """Return the declarative schema for settings spanning multiple widgets."""
    nfo = FlagListSpec(
        "nfo_include_new",
        (
            ("checkBox_nfo_sorttitle", NfoInclude.SORTTITLE),
            ("checkBox_nfo_originaltitle", NfoInclude.ORIGINALTITLE),
            ("checkBox_nfo_title_cd", NfoInclude.TITLE_CD),
            ("checkBox_nfo_outline", NfoInclude.OUTLINE),
            ("checkBox_nfo_plot", NfoInclude.PLOT_),
            ("checkBox_nfo_originalplot", NfoInclude.ORIGINALPLOT),
            ("checkBox_outline_cdata", NfoInclude.OUTLINE_NO_CDATA),
            ("checkBox_nfo_release", NfoInclude.RELEASE_),
            ("checkBox_nfo_relasedate", NfoInclude.RELEASEDATE),
            ("checkBox_nfo_premiered", NfoInclude.PREMIERED),
            ("checkBox_nfo_country", NfoInclude.COUNTRY),
            ("checkBox_nfo_mpaa", NfoInclude.MPAA),
            ("checkBox_nfo_customrating", NfoInclude.CUSTOMRATING),
            ("checkBox_nfo_year", NfoInclude.YEAR),
            ("checkBox_nfo_runtime", NfoInclude.RUNTIME),
            ("checkBox_nfo_wanted", NfoInclude.WANTED),
            ("checkBox_nfo_score", NfoInclude.SCORE),
            ("checkBox_nfo_criticrating", NfoInclude.CRITICRATING),
            ("checkBox_nfo_actor", NfoInclude.ACTOR),
            ("checkBox_nfo_all_actor", NfoInclude.ACTOR_ALL),
            ("checkBox_nfo_director", NfoInclude.DIRECTOR),
            ("checkBox_nfo_series", NfoInclude.SERIES),
            ("checkBox_nfo_tag", NfoInclude.TAG),
            ("checkBox_nfo_genre", NfoInclude.GENRE),
            ("checkBox_nfo_actor_set", NfoInclude.ACTOR_SET),
            ("checkBox_nfo_set", NfoInclude.SERIES_SET),
            ("checkBox_nfo_studio", NfoInclude.STUDIO),
            ("checkBox_nfo_maker", NfoInclude.MAKER),
            ("checkBox_nfo_publisher", NfoInclude.PUBLISHER),
            ("checkBox_nfo_label", NfoInclude.LABEL),
            ("checkBox_nfo_poster", NfoInclude.POSTER),
            ("checkBox_nfo_cover", NfoInclude.COVER),
            ("checkBox_nfo_trailer", NfoInclude.TRAILER),
            ("checkBox_nfo_website", NfoInclude.WEBSITE),
        ),
    )
    tag = FlagListSpec(
        "nfo_tag_include",
        (
            ("checkBox_tag_actor", TagInclude.ACTOR),
            ("checkBox_tag_letters", TagInclude.LETTERS),
            ("checkBox_tag_series", TagInclude.SERIES),
            ("checkBox_tag_studio", TagInclude.STUDIO),
            ("checkBox_tag_publisher", TagInclude.PUBLISHER),
            ("checkBox_tag_cnword", TagInclude.CNWORD),
            ("checkBox_tag_mosaic", TagInclude.MOSAIC),
            ("checkBox_tag_definition", TagInclude.DEFINITION),
        ),
    )
    fields = FlagListSpec(
        "fields_rule",
        (
            ("checkBox_title_del_actor", FieldRule.DEL_ACTOR),
            ("checkBox_actor_del_char", FieldRule.DEL_CHAR),
            ("checkBox_actor_fc2_seller", FieldRule.FC2_SELLER),
            ("checkBox_number_del_num", FieldRule.DEL_NUM),
        ),
    )
    outline = CompositeListSpec(
        "outline_format",
        flags=(("checkBox_show_translate_from", OutlineShow.SHOW_FROM),),
        groups=(
            ChoiceGroupSpec(
                (
                    ("radioButton_trans_show_zh_jp", OutlineShow.SHOW_ZH_JP),
                    ("radioButton_trans_show_jp_zh", OutlineShow.SHOW_JP_ZH),
                    ("radioButton_trans_show_one", None),
                ),
                None,
            ),
        ),
    )
    emby = CompositeListSpec(
        "emby_on",
        flags=(
            ("checkBox_actor_info_translate", EmbyAction.ACTOR_INFO_TRANSLATE),
            ("checkBox_actor_info_photo", EmbyAction.ACTOR_INFO_PHOTO),
            ("checkBox_actor_photo_ne_backdrop", EmbyAction.GRAPHIS_BACKDROP),
            ("checkBox_actor_photo_ne_face", EmbyAction.GRAPHIS_FACE),
            ("checkBox_actor_photo_ne_new", EmbyAction.GRAPHIS_NEW),
            ("checkBox_actor_photo_auto", EmbyAction.ACTOR_PHOTO_AUTO),
            ("checkBox_actor_pic_replace", EmbyAction.ACTOR_REPLACE),
        ),
        groups=(
            ChoiceGroupSpec(
                (
                    ("radioButton_actor_info_zh_cn", EmbyAction.ACTOR_INFO_ZH_CN),
                    ("radioButton_actor_info_zh_tw", EmbyAction.ACTOR_INFO_ZH_TW),
                    ("radioButton_actor_info_ja", EmbyAction.ACTOR_INFO_JA),
                ),
                EmbyAction.ACTOR_INFO_JA,
            ),
            ChoiceGroupSpec(
                (
                    ("radioButton_actor_info_all", EmbyAction.ACTOR_INFO_ALL),
                    ("radioButton_actor_info_miss", EmbyAction.ACTOR_INFO_MISS),
                ),
                EmbyAction.ACTOR_INFO_MISS,
            ),
            ChoiceGroupSpec(
                (
                    ("radioButton_actor_photo_net", EmbyAction.ACTOR_PHOTO_NET),
                    ("radioButton_actor_photo_local", EmbyAction.ACTOR_PHOTO_LOCAL),
                ),
                EmbyAction.ACTOR_PHOTO_LOCAL,
            ),
            ChoiceGroupSpec(
                (
                    ("radioButton_actor_photo_all", EmbyAction.ACTOR_PHOTO_ALL),
                    ("radioButton_actor_photo_miss", EmbyAction.ACTOR_PHOTO_MISS),
                ),
                EmbyAction.ACTOR_PHOTO_MISS,
            ),
        ),
    )
    watermark_types = FlagListSpec(
        "mark_type",
        (
            ("checkBox_sub", MarkType.SUB),
            ("checkBox_censored", MarkType.YOUMA),
            ("checkBox_umr", MarkType.UMR),
            ("checkBox_leak", MarkType.LEAK),
            ("checkBox_uncensored", MarkType.UNCENSORED),
            ("checkBox_hd", MarkType.HD),
        ),
    )
    switches = CompositeListSpec(
        "switch_on",
        flags=(
            ("checkBox_auto_start", Switch.AUTO_START),
            ("checkBox_auto_exit", Switch.AUTO_EXIT),
            ("checkBox_rest_scrape", Switch.REST_SCRAPE),
            ("checkBox_timed_scrape", Switch.TIMED_SCRAPE),
            ("checkBox_remain_task", Switch.REMAIN_TASK),
            ("checkBox_show_dialog_exit", Switch.SHOW_DIALOG_EXIT),
            ("checkBox_show_dialog_stop_scrape", Switch.SHOW_DIALOG_STOP_SCRAPE),
            ("checkBox_sortmode_delpic", Switch.SORT_DEL),
            ("checkBox_dialog_qt", Switch.QT_DIALOG),
            ("checkBox_theporndb_hash", Switch.THEPORNDB_NO_HASH),
            ("checkBox_hide_dock_icon", Switch.HIDE_DOCK),
            ("checkBox_highdpi_passthrough", Switch.PASSTHROUGH),
            ("checkBox_hide_menu_icon", Switch.HIDE_MENU),
            ("checkBox_dark_mode", Switch.DARK_MODE),
            ("checkBox_copy_netdisk_nfo", Switch.COPY_NETDISK_NFO),
        ),
        groups=(
            ChoiceGroupSpec(
                (
                    ("radioButton_hide_close", Switch.HIDE_CLOSE),
                    ("radioButton_hide_mini", Switch.HIDE_MINI),
                    ("radioButton_hide_none", Switch.HIDE_NONE),
                ),
                Switch.HIDE_NONE,
            ),
        ),
    )
    positions = (
        ScalarChoiceSpec(
            "mark_fixed",
            (
                ("radioButton_not_fixed_position", "not_fixed"),
                ("radioButton_fixed_corner", "corner"),
                ("radioButton_fixed_position", "fixed"),
            ),
            "fixed",
        ),
        ScalarChoiceSpec(
            "mark_pos",
            (
                ("radioButton_top_left", "top_left"),
                ("radioButton_top_right", "top_right"),
                ("radioButton_bottom_left", "bottom_left"),
                ("radioButton_bottom_right", "bottom_right"),
            ),
            "top_left",
        ),
        ScalarChoiceSpec(
            "mark_pos_corner",
            (
                ("radioButton_top_left_corner", "top_left"),
                ("radioButton_top_right_corner", "top_right"),
                ("radioButton_bottom_left_corner", "bottom_left"),
                ("radioButton_bottom_right_corner", "bottom_right"),
            ),
            "top_left",
        ),
        ScalarChoiceSpec(
            "mark_pos_hd",
            (
                ("radioButton_top_left_hd", "top_left"),
                ("radioButton_top_right_hd", "top_right"),
                ("radioButton_bottom_left_hd", "bottom_left"),
                ("radioButton_bottom_right_hd", "bottom_right"),
            ),
            "bottom_right",
        ),
        ScalarChoiceSpec(
            "mark_pos_sub",
            (
                ("radioButton_top_left_sub", "top_left"),
                ("radioButton_top_right_sub", "top_right"),
                ("radioButton_bottom_left_sub", "bottom_left"),
                ("radioButton_bottom_right_sub", "bottom_right"),
            ),
            "top_left",
        ),
        ScalarChoiceSpec(
            "mark_pos_mosaic",
            (
                ("radioButton_top_left_mosaic", "top_left"),
                ("radioButton_top_right_mosaic", "top_right"),
                ("radioButton_bottom_left_mosaic", "bottom_left"),
                ("radioButton_bottom_right_mosaic", "bottom_right"),
            ),
            "top_right",
        ),
    )
    switch_binding = _composite_list_binding(switches)

    def save_switches(ui: object, config: object) -> None:
        switch_binding.save(ui, config)
        values = [value for value in config.switch_on if value != Switch.SHOW_LOGS]
        if not ui.textBrowser_log_main_2.isHidden():
            values.append(Switch.SHOW_LOGS)
        config.switch_on = values

    return [
        _composite_list_binding(outline),
        _flag_list_binding(tag),
        _flag_list_binding(nfo),
        _flag_list_binding(fields),
        _composite_list_binding(emby),
        _flag_list_binding(watermark_types),
        *(_scalar_choice_binding(spec) for spec in positions),
        CompositeBinding("switch_on", switch_binding.load, save_switches),
    ]
