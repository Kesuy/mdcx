from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QCheckBox, QInputDialog

from ...config.extend import deal_url
from ...config.manager import manager
from ...core.scraper import again_search
from ...models.flags import Flags
from ...signals import signal_qt
from ...utils import get_current_time, split_path


_PREFERENCE_KEY = "scrape/local_nfo_inplace_reorganize"


def _preference_store() -> QSettings:
    return QSettings(str(manager.data_folder / "ui_preferences.ini"), QSettings.Format.IniFormat)


def local_nfo_inplace_enabled() -> bool:
    return bool(_preference_store().value(_PREFERENCE_KEY, False, type=bool))


def _save_local_nfo_inplace_enabled(enabled: bool) -> None:
    settings = _preference_store()
    settings.setValue(_PREFERENCE_KEY, bool(enabled))
    settings.sync()


def setup_local_nfo_inplace_setting(window) -> QCheckBox:
    """Add the opt-in switch beside the normal success-folder move setting."""

    ui = window.Ui
    existing = getattr(ui, "checkBox_local_nfo_inplace_reorganize", None)
    if existing is not None:
        return existing

    parent = getattr(ui, "gridLayoutWidget_6", None) or window
    checkbox = QCheckBox("原地整理（仅主界面打开本地 NFO 后重刮）", parent=parent)
    checkbox.setObjectName("checkBox_local_nfo_inplace_reorganize")
    checkbox.setToolTip(
        "默认关闭。开启后，仅主界面“打开本地 NFO”后发起的重新刮削/指定网站刮削，"
        "会在当前影片父目录内原地整理；普通结果列表右键重刮仍按原设置输出。"
    )
    checkbox.setChecked(local_nfo_inplace_enabled())
    checkbox.toggled.connect(_save_local_nfo_inplace_enabled)

    layout = getattr(ui, "gridLayout_6", None)
    if layout is not None:
        layout.addWidget(checkbox, 2, 0, 1, 2)
    else:
        checkbox.setParent(window)

    ui.checkBox_local_nfo_inplace_reorganize = checkbox
    return checkbox


class LocalNfoInplaceMixin:
    """Mark only rescrapes that originate from a locally opened NFO item."""

    def _is_current_local_nfo_entry(self, file_path: Path) -> bool:
        selected = self._get_single_selected_entry()
        candidates = []
        if selected is not None and selected[3] == file_path:
            candidates.append(selected[2])
        if self.show_data is not None and self.show_data.file_info.file_path == file_path:
            candidates.append(self.show_data)
        return any(str(entry.show_name).startswith("本地.") for entry in candidates)

    def _mark_local_nfo_inplace_request(self, file_path: Path) -> None:
        checkbox = getattr(self.Ui, "checkBox_local_nfo_inplace_reorganize", None)
        enabled = bool(checkbox is not None and checkbox.isChecked())
        if enabled and self._is_current_local_nfo_entry(file_path):
            Flags.again_inplace_paths.add(file_path)
            signal_qt.show_log_text(f"\n 📌 本地 NFO 重刮已启用原地整理：{file_path}")
        else:
            # Explicitly remove a stale pending marker so a later normal result-list
            # rescrape of the same path can never inherit local-NFO behavior.
            Flags.again_inplace_paths.discard(file_path)

    def search_by_number_clicked(self):
        """主界面输入番号重新刮削；本地 NFO 来源可选择原地整理。"""
        if self._check_main_file_path():
            file_path = self.file_main_open_path
            main_file_name = split_path(file_path)[1]
            default_text = os.path.splitext(main_file_name)[0].upper()
            text, ok = QInputDialog.getText(
                self,
                "输入番号重新刮削",
                f"文件名: {main_file_name}\n请输入番号:",
                text=default_text,
            )
            if ok and text:
                self._mark_local_nfo_inplace_request(file_path)
                Flags.again_dic[file_path] = (text, "", "")
                signal_qt.show_scrape_info(f"💡 已添加刮削！{get_current_time()}")
                if self.Ui.pushButton_start_cap.text() == "开始":
                    again_search()

    def search_by_url_clicked(self):
        """主界面输入指定网址重新刮削；本地 NFO 来源可选择原地整理。"""
        if self._check_main_file_path():
            file_path = self.file_main_open_path
            main_file_name = split_path(file_path)[1]
            text, ok = QInputDialog.getText(
                self,
                "输入网址重新刮削",
                f"文件名: {main_file_name}\n支持网站:airav_cc、avsex、avsox、dmm、getchu、fc2"
                f"、fc2club、fc2hub、iqqtv、jav321、javbus、javdb、freejavbt、javlibrary、mdtv"
                f"、madouqu、mgstage、7mmtv、xcity、mywife、giga、faleno、dahlia、fantastica、avbase"
                f"、prestige、hdouban、lulubar、love6、cnmdb、theporndb、kin8\n请输入番号对应的网址（不是网站首页地址！！！是番号页面地址！！！）:",
            )
            if ok and text:
                website, url = deal_url(text)
                if website:
                    self._mark_local_nfo_inplace_request(file_path)
                    Flags.again_dic[file_path] = ("", url, website)
                    signal_qt.show_scrape_info(f"💡 已添加刮削！{get_current_time()}")
                    if self.Ui.pushButton_start_cap.text() == "开始":
                        again_search()
                else:
                    signal_qt.show_scrape_info(f"💡 不支持的网站！{get_current_time()}")
