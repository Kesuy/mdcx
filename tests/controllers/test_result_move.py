from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from mdcx.controllers.main_window import main_page_mixin as module
from mdcx.controllers.main_window.main_page_mixin import MainPageMixin
from mdcx.models.flags import Flags
from mdcx.models.types import ShowData


class _MoveWindow(MainPageMixin):
    def __init__(self, selected_entries):
        self.options = QFileDialog.Option.ShowDirsOnly
        self.show_data = None
        self.file_main_open_path = Path()
        self.json_array = {}
        self._selected_entries = selected_entries

    def _get_selected_success_entries(self):
        return self._selected_entries

    def _get_selected_entries(self):
        return self._selected_entries

    def _sync_related_moved_paths(self, _mapping, _selected, *, all_path_mapping=()):
        pass

    def set_main_info(self, _show_data):
        pass

    def _show_action_failure_feedback(self, *_args, **_kwargs):
        pass


def test_rule_based_move_asks_for_target_root_before_moving(monkeypatch, tmp_path: Path):
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    source_path = source_folder / "ABC-123.mp4"
    source_path.write_bytes(b"movie")

    configured_folder = tmp_path / "configured"
    configured_folder.mkdir()
    chosen_folder = tmp_path / "chosen"
    chosen_folder.mkdir()

    file_info = SimpleNamespace(file_path=source_path)
    show_data = SimpleNamespace(
        file_info=file_info,
        data=SimpleNamespace(number="ABC-123"),
        other=SimpleNamespace(),
    )
    selected_entries = [(SimpleNamespace(), "ABC-123", show_data, source_path)]
    window = _MoveWindow(selected_entries)

    events: list[str] = []
    captured: dict[str, object] = {}

    def fake_get_existing_directory(_parent, title, start_folder, **_kwargs):
        events.append("dialog")
        captured["dialog_title"] = title
        captured["start_folder"] = start_folder
        return str(chosen_folder)

    def fake_question(_parent, _title, message, *_args, **_kwargs):
        events.append("question")
        captured["message"] = message
        return QMessageBox.StandardButton.Yes

    async def fake_move(_file_info, _data, _other, target_root, **_kwargs):
        events.append("move")
        captured["target_root"] = target_root
        return SimpleNamespace(
            moved=False,
            old_file_path=source_path,
            new_file_path=source_path,
            path_mapping=(),
        )

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake_get_existing_directory)
    monkeypatch.setattr(QMessageBox, "question", fake_question)
    monkeypatch.setattr(
        module,
        "get_movie_path_setting",
        lambda _path: SimpleNamespace(success_folder=configured_folder),
    )
    monkeypatch.setattr(module, "move_finished_media_to_configured_folder", fake_move)
    monkeypatch.setattr(module.signal_qt, "show_log_text", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.signal_qt, "show_scrape_info", lambda *_args, **_kwargs: None)

    window.main_move_by_rule_click()

    assert events == ["dialog", "question", "move"]
    assert captured["start_folder"] == configured_folder.as_posix()
    assert captured["target_root"] == chosen_folder
    assert f"目标根目录：{chosen_folder}" in str(captured["message"])


def test_rule_based_move_cancelled_folder_picker_does_not_move(monkeypatch, tmp_path: Path):
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    source_path = source_folder / "ABC-123.mp4"
    source_path.write_bytes(b"movie")

    file_info = SimpleNamespace(file_path=source_path)
    show_data = SimpleNamespace(
        file_info=file_info,
        data=SimpleNamespace(number="ABC-123"),
        other=SimpleNamespace(),
    )
    window = _MoveWindow([(SimpleNamespace(), "ABC-123", show_data, source_path)])

    move_called = False

    async def fake_move(*_args, **_kwargs):
        nonlocal move_called
        move_called = True
        return SimpleNamespace(moved=False)

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        module,
        "get_movie_path_setting",
        lambda _path: SimpleNamespace(success_folder=tmp_path),
    )
    monkeypatch.setattr(module, "move_finished_media_to_configured_folder", fake_move)

    window.main_move_by_rule_click()

    assert move_called is False


def test_rule_based_move_treats_selected_multi_cd_rows_as_one_movie_group(monkeypatch, tmp_path: Path):
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    cd1 = source_folder / "ABC-123-cd1.mp4"
    cd2 = source_folder / "ABC-123-cd2.mp4"
    cd1.write_bytes(b"cd1")
    cd2.write_bytes(b"cd2")
    chosen_folder = tmp_path / "chosen"
    chosen_folder.mkdir()

    first_info = SimpleNamespace(file_path=cd1, number="ABC-123")
    second_info = SimpleNamespace(file_path=cd2, number="ABC-123")
    first = SimpleNamespace(file_info=first_info, data=SimpleNamespace(number="ABC-123"), other=SimpleNamespace())
    second = SimpleNamespace(file_info=second_info, data=SimpleNamespace(number="ABC-123"), other=SimpleNamespace())
    selected_entries = [
        (SimpleNamespace(), "ABC-123-cd1", first, cd1),
        (SimpleNamespace(), "ABC-123-cd2", second, cd2),
    ]
    window = _MoveWindow(selected_entries)

    calls: list[bool] = []

    async def fake_move(file_info, _data, _other, target_root, *, preserve_source_folder=False):
        calls.append(preserve_source_folder)
        new_folder = target_root / "ABC-123"
        new_cd1 = new_folder / cd1.name
        new_cd2 = new_folder / cd2.name
        file_info.file_path = new_cd1
        return SimpleNamespace(
            moved=True,
            old_file_path=cd1,
            new_file_path=new_cd1,
            path_mapping=((cd1, new_cd1), (cd2, new_cd2)),
        )

    async def fake_save_success_list(*_args, **_kwargs):
        return None

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(chosen_folder))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        module,
        "get_movie_path_setting",
        lambda _path: SimpleNamespace(success_folder=tmp_path),
    )
    monkeypatch.setattr(module, "move_finished_media_to_configured_folder", fake_move)
    monkeypatch.setattr(module, "save_success_list", fake_save_success_list)
    monkeypatch.setattr(module.signal_qt, "show_log_text", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.signal_qt, "show_scrape_info", lambda *_args, **_kwargs: None)

    window.main_move_by_rule_click()

    assert calls == [False]


def test_multi_cd_path_sync_preserves_metadata_and_updates_shared_runtime_caches(
    monkeypatch,
    tmp_path: Path,
):
    old_folder = tmp_path / "old"
    new_folder = tmp_path / "new"
    old_folder.mkdir()
    new_folder.mkdir()
    old_cd1 = old_folder / "ABC-123-cd1.mp4"
    old_cd2 = old_folder / "ABC-123-cd2.mp4"
    old_poster = old_folder / "ABC-123-poster.jpg"
    old_subtitle = old_folder / "ABC-123-cd2.zh.srt"
    new_cd1 = new_folder / "ABC-123-cd1.mp4"
    new_cd2 = new_folder / "ABC-123-cd2.mp4"
    new_poster = new_folder / "ABC-123-poster.jpg"
    new_subtitle = new_folder / "ABC-123-cd2.zh.srt"

    first = ShowData.empty()
    first.show_name = "1-1.ABC-123-cd1"
    first.file_info.file_path = new_cd1
    first.data.number = "ABC-123"

    second = ShowData.empty()
    second.show_name = "1-2.ABC-123-cd2"
    second.file_info.file_path = old_cd2
    second.file_info.folder_path = old_folder
    second.file_info.file_name = old_cd2.stem
    second.file_info.file_ex = old_cd2.suffix
    second.file_info.file_show_name = "ABC-123-cd2"
    second.file_info.file_show_path = old_cd2
    second.file_info.cd_part = "-cd2"
    second.file_info.definition = "4K"
    second.file_info.codec = "H265"
    second.file_info.has_sub = True
    second.file_info.sub_list = [str(old_subtitle)]
    second.other.poster_path = old_poster
    second.data.number = "ABC-123"

    window = object.__new__(MainPageMixin)
    window.json_array = {first.show_name: first, second.show_name: second}
    window.file_main_open_path = old_cd2

    monkeypatch.setattr(
        Flags,
        "file_done_dic",
        {
            "ABC-123": {
                "poster": old_poster,
                "thumb": None,
                "fanart": None,
                "trailer": None,
                "local_poster": old_poster,
                "local_thumb": None,
                "local_fanart": None,
                "local_trailer": None,
            }
        },
    )
    monkeypatch.setattr(Flags, "success_list", {old_cd1, old_cd2})
    monkeypatch.setattr(Flags, "pic_catch_set", {old_poster})
    monkeypatch.setattr(Flags, "extrafanart_deal_set", set())
    monkeypatch.setattr(Flags, "trailer_deal_set", set())
    monkeypatch.setattr(Flags, "theme_videos_deal_set", set())
    monkeypatch.setattr(Flags, "nfo_deal_set", {old_subtitle})
    monkeypatch.setattr(Flags, "file_new_path_dic", {old_cd2: [old_poster]})

    movie_mapping = ((old_cd1, new_cd1), (old_cd2, new_cd2))
    all_mapping = (
        (old_cd1, new_cd1),
        (old_cd2, new_cd2),
        (old_poster, new_poster),
        (old_subtitle, new_subtitle),
    )

    window._sync_related_moved_paths(movie_mapping, first, all_path_mapping=all_mapping)

    assert second.file_info.file_path == new_cd2
    assert second.file_info.folder_path == new_folder
    assert second.file_info.cd_part == "-cd2"
    assert second.file_info.file_show_name == "ABC-123-cd2"
    assert second.file_info.definition == "4K"
    assert second.file_info.codec == "H265"
    assert second.file_info.has_sub is True
    assert second.file_info.sub_list == [str(new_subtitle)]
    assert second.other.poster_path == new_poster
    assert Flags.file_done_dic["ABC-123"]["poster"] == new_poster
    assert Flags.file_done_dic["ABC-123"]["local_poster"] == new_poster
    assert Flags.pic_catch_set == {new_poster}
    assert Flags.nfo_deal_set == {new_subtitle}
    assert Flags.file_new_path_dic == {new_cd2: [new_poster]}
    assert Flags.success_list == {new_cd1, new_cd2}
    assert window.file_main_open_path == new_cd2
