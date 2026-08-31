# ruff: noqa: E402, I001

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

from mdcx.controllers.main_window import main_page_mixin as main_window_module
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.core.local_nfo_loader import LocalNfoLoadResult
from mdcx.models.flags import Flags
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo, ShowData

APP = QApplication.instance() or QApplication([])


def _show_data(path: Path, show_name: str) -> ShowData:
    file_info = FileInfo.empty()
    file_info.file_path = path
    file_info.folder_path = path.parent
    file_info.file_name = path.stem
    data = CrawlersResult.empty()
    data.number = "H4610-ORI696"
    return ShowData(file_info, data, OtherInfo.empty(), show_name)


def test_load_local_nfo_path_populates_success_tree_and_main_panel(monkeypatch, tmp_path: Path):
    cd1 = _show_data(tmp_path / "movie-cd1.mp4", "本地.movie-cd1")
    cd2 = _show_data(tmp_path / "movie-cd2.mp4", "本地.movie-cd2")
    loaded = LocalNfoLoadResult(primary=cd1, entries=(cd1, cd2))

    class Harness:
        _load_local_nfo_path = MyMAinWindow._load_local_nfo_path

    window = Harness()
    window.tree = QTreeWidget()
    window.item_succ = QTreeWidgetItem(window.tree, ["成功"])
    window.json_array = {}
    shown = []
    selected = []

    def show_list_name(_status, entry):
        window.json_array[entry.show_name] = entry
        window.item_succ.addChild(QTreeWidgetItem([entry.show_name]))

    window.show_list_name = show_list_name
    window.set_main_info = shown.append
    window._set_result_item_as_current_selection = selected.append

    monkeypatch.setattr(main_window_module, "load_local_nfo", lambda _path: "awaitable")
    monkeypatch.setattr(main_window_module.executor, "run", lambda _awaitable: loaded)
    monkeypatch.setattr(main_window_module, "signal_qt", SimpleNamespace(show_log_text=lambda _message: None))
    monkeypatch.setattr(Flags, "success_list", set())

    window._load_local_nfo_path(tmp_path / "movie-cd1.nfo")

    assert list(window.json_array) == ["本地.movie-cd1", "本地.movie-cd2"]
    assert shown == [cd1]
    assert selected[0].text(0) == "本地.movie-cd1"
    assert Flags.success_list == {cd1.file_info.file_path, cd2.file_info.file_path}
    assert APP is not None
