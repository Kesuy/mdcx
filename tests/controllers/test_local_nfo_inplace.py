from pathlib import Path
from types import SimpleNamespace

from mdcx.controllers.main_window import local_nfo_inplace as module
from mdcx.controllers.main_window.local_nfo_inplace import LocalNfoInplaceMixin
from mdcx.models.flags import Flags
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo, ShowData


def _show_data(file_path: Path, *, number: str, local: bool = True) -> ShowData:
    file_info = FileInfo.empty()
    file_info.file_path = file_path
    file_info.file_name = file_path.stem
    file_info.file_ex = file_path.suffix
    file_info.number = number
    data = CrawlersResult.empty()
    data.number = number
    return ShowData(
        file_info=file_info,
        data=data,
        other=OtherInfo.empty(),
        show_name=("本地." if local else "1.") + file_path.stem,
    )


class _CheckBox:
    def __init__(self, checked: bool):
        self.checked = checked

    def isChecked(self):
        return self.checked


class _Harness(LocalNfoInplaceMixin):
    def __init__(self, show_data: ShowData | None, *, inplace_enabled: bool = False):
        self.show_data = show_data
        self.selected = (
            None if show_data is None else (None, show_data.show_name, show_data, show_data.file_info.file_path)
        )
        self.Ui = SimpleNamespace(checkBox_local_nfo_inplace_reorganize=_CheckBox(inplace_enabled))

    def _get_single_selected_entry(self):
        return self.selected


def test_inplace_preference_is_saved_in_main_config_without_sidecar_ini(monkeypatch, tmp_path):
    saves = []
    fake_manager = SimpleNamespace(
        data_folder=tmp_path,
        config=SimpleNamespace(local_nfo_inplace_reorganize=False),
        save=lambda: saves.append(True),
    )
    monkeypatch.setattr(module, "manager", fake_manager)

    module._save_local_nfo_inplace_enabled(True)

    assert fake_manager.config.local_nfo_inplace_reorganize is True
    assert saves == [True]
    assert not (tmp_path / "ui_preferences.ini").exists()


def test_legacy_ui_preferences_ini_is_migrated_then_removed(monkeypatch, tmp_path):
    legacy = tmp_path / "ui_preferences.ini"
    legacy.write_text("[scrape]\nlocal_nfo_inplace_reorganize=true\n", encoding="utf-8")
    saves = []
    fake_manager = SimpleNamespace(
        data_folder=tmp_path,
        config=SimpleNamespace(local_nfo_inplace_reorganize=False),
        save=lambda: saves.append(True),
    )
    monkeypatch.setattr(module, "manager", fake_manager)

    assert module.local_nfo_inplace_enabled() is True
    assert fake_manager.config.local_nfo_inplace_reorganize is True
    assert saves == [True]
    assert not legacy.exists()


def test_local_nfo_rescrape_prefills_canonical_nfo_number_not_filename_stem():
    file_path = Path("FZ88 御藤静.mp4")
    harness = _Harness(_show_data(file_path, number="FZ88"))

    assert harness._local_nfo_default_number(file_path, file_path.name) == "FZ88"


def test_non_local_rescrape_keeps_filename_stem_fallback():
    file_path = Path("FZ88 御藤静.mp4")
    harness = _Harness(_show_data(file_path, number="FZ88", local=False))

    assert harness._local_nfo_default_number(file_path, file_path.name) == "FZ88 御藤静"


def test_inplace_marker_is_added_only_for_main_panel_local_nfo_entry(monkeypatch):
    local_path = Path("local.mp4")
    normal_path = Path("normal.mp4")
    local = _Harness(_show_data(local_path, number="LOCAL-001"), inplace_enabled=True)
    normal = _Harness(_show_data(normal_path, number="NORMAL-001", local=False), inplace_enabled=True)

    monkeypatch.setattr(module, "signal_qt", SimpleNamespace(show_log_text=lambda _message: None))
    original = Flags.again_inplace_paths
    try:
        Flags.again_inplace_paths = set()
        local._mark_local_nfo_inplace_request(local_path)
        normal._mark_local_nfo_inplace_request(normal_path)

        assert Flags.again_inplace_paths == {local_path}
    finally:
        Flags.again_inplace_paths = original


def test_inplace_marker_is_not_added_when_switch_is_off(monkeypatch):
    file_path = Path("local.mp4")
    harness = _Harness(_show_data(file_path, number="LOCAL-001"), inplace_enabled=False)

    monkeypatch.setattr(module, "signal_qt", SimpleNamespace(show_log_text=lambda _message: None))
    original = Flags.again_inplace_paths
    try:
        Flags.again_inplace_paths = set()
        harness._mark_local_nfo_inplace_request(file_path)

        assert Flags.again_inplace_paths == set()
    finally:
        Flags.again_inplace_paths = original
