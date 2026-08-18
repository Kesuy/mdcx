import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdcx.controllers.main_window import main_window as main_window_module
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.core.media_reorganization import MediaReorganizationError, MediaReorganizationResult
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo, ShowData


class _LineEdit:
    def __init__(self, value: str = ""):
        self.value = value

    def text(self) -> str:
        return self.value

    def setText(self, value: str) -> None:
        self.value = value


class _TextEdit(_LineEdit):
    def toPlainText(self) -> str:
        return self.value


class _Label:
    def __init__(self):
        self.value = ""

    def setText(self, value: str) -> None:
        self.value = value


def _ui() -> SimpleNamespace:
    return SimpleNamespace(
        lineEdit_nfo_number=_LineEdit("H4610-ORI696"),
        lineEdit_nfo_actor=_LineEdit("天宮まりる"),
        lineEdit_nfo_year=_LineEdit("2010"),
        lineEdit_nfo_title=_LineEdit("望月 奈々"),
        lineEdit_nfo_originaltitle=_LineEdit("望月 奈々"),
        textEdit_nfo_outline=_TextEdit("简介"),
        textEdit_nfo_originalplot=_TextEdit("原始简介"),
        textEdit_nfo_tag=_TextEdit("标签"),
        lineEdit_nfo_release=_LineEdit("2010-04-24"),
        lineEdit_nfo_runtime=_LineEdit("48"),
        lineEdit_nfo_score=_LineEdit("0.0"),
        lineEdit_nfo_wanted=_LineEdit(""),
        lineEdit_nfo_director=_LineEdit(""),
        lineEdit_nfo_series=_LineEdit(""),
        lineEdit_nfo_studio=_LineEdit("エッチな4610"),
        lineEdit_nfo_publisher=_LineEdit("エッチな4610"),
        lineEdit_nfo_poster=_LineEdit("poster-url"),
        lineEdit_nfo_cover=_LineEdit("cover-url"),
        lineEdit_nfo_trailer=_LineEdit(""),
        label_save_tips=_Label(),
        label_nfo=_Label(),
    )


@pytest.mark.parametrize("outcome", ["moved", "unchanged", "failure", "partial_failure", "write_failure"])
def test_save_nfo_info_clears_number_caches_after_writing_nfo(monkeypatch, tmp_path: Path, outcome: str):
    movie = tmp_path / "JAV_output" / "望月奈々" / "old" / "H4610-ORI696 望月奈々-CD1.wmv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    file_info = FileInfo.empty()
    file_info.file_path = movie
    file_info.folder_path = movie.parent
    file_info.file_name = movie.stem
    file_info.file_ex = movie.suffix
    file_info.cd_part = "-CD1"
    scraped_data = CrawlersResult.empty()
    scraped_data.number = "OLD-001"
    scraped_data.actor = "旧演员"
    show_data = ShowData(file_info=file_info, data=scraped_data, other=OtherInfo.empty(), show_name="row")
    sibling_movie = movie.with_name("H4610-ORI696 望月奈々-CD2.wmv")
    sibling_movie.write_bytes(b"movie-cd2")
    sibling_file_info = FileInfo.empty()
    sibling_file_info.file_path = sibling_movie
    sibling_file_info.folder_path = sibling_movie.parent
    sibling_file_info.file_name = sibling_movie.stem
    sibling_file_info.file_ex = sibling_movie.suffix
    sibling_file_info.cd_part = "-CD2"
    sibling_data = CrawlersResult.empty()
    sibling_data.number = "OLD-001"
    sibling_data.actor = "旧演员"
    sibling_show_data = ShowData(
        file_info=sibling_file_info,
        data=sibling_data,
        other=OtherInfo.empty(),
        show_name="row-cd2",
    )

    window = MyMAinWindow.__new__(MyMAinWindow)
    window.Ui = _ui()
    window.now_show_name = "row"
    window.json_array = {"row": show_data, "row-cd2": sibling_show_data}
    refreshed: list[ShowData] = []
    window.set_main_info = refreshed.append
    calls: list[tuple[str, object]] = []
    new_movie = (
        tmp_path / "JAV_output" / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる" / "H4610-ORI696 天宮まりる-CD1.wmv"
    )
    new_sibling_movie = new_movie.with_name("H4610-ORI696 天宮まりる-CD2.wmv")
    movie_nfo = movie.with_suffix(".nfo")
    sibling_nfo = sibling_movie.with_suffix(".nfo")
    movie_nfo.write_bytes(b"old-cd1")
    sibling_nfo.write_bytes(b"old-cd2")

    async def fake_write_nfo(*args, **kwargs):
        calls.append(("write", args[1].actor))
        args[2].write_text(args[1].actor, encoding="utf-8")
        if outcome == "write_failure" and len(calls) == 2:
            return False
        return True

    async def fake_reorganize(file_info_arg, data_arg, other_arg, success_folder_arg):
        calls.append(("reorganize", data_arg.actor))
        assert file_info_arg is file_info
        assert other_arg is show_data.other
        assert success_folder_arg == tmp_path / "JAV_output"
        if outcome == "partial_failure":
            file_info_arg.file_path = new_movie
            file_info_arg.folder_path = new_movie.parent
            file_info_arg.file_name = new_movie.stem
            raise MediaReorganizationError(
                "incomplete rollback",
                ((movie, new_movie), (sibling_movie, new_sibling_movie)),
            )
        if outcome == "failure":
            raise MediaReorganizationError("injected failure")
        if outcome == "unchanged":
            return MediaReorganizationResult(movie, movie, movie.parent, movie.parent, False)
        file_info_arg.file_path = new_movie
        file_info_arg.folder_path = new_movie.parent
        file_info_arg.file_name = new_movie.stem
        return MediaReorganizationResult(
            movie,
            new_movie,
            movie.parent,
            new_movie.parent,
            True,
            ((movie, new_movie), (sibling_movie, new_sibling_movie)),
        )

    async def fake_save_success_list():
        calls.append(("save_success", None))

    def run(awaitable):
        return asyncio.run(awaitable)

    monkeypatch.setattr(main_window_module, "write_nfo", fake_write_nfo)
    monkeypatch.setattr(main_window_module, "reorganize_scraped_media", fake_reorganize)
    monkeypatch.setattr(main_window_module, "save_success_list", fake_save_success_list)
    monkeypatch.setattr(main_window_module, "signal_qt", SimpleNamespace(show_log_text=lambda _message: None))
    monkeypatch.setattr(
        main_window_module,
        "get_movie_path_setting",
        lambda _path: SimpleNamespace(success_folder=tmp_path / "JAV_output"),
    )
    monkeypatch.setattr(main_window_module.executor, "run", run)
    monkeypatch.setattr(main_window_module.Flags, "success_list", {movie, sibling_movie})
    monkeypatch.setattr(
        main_window_module.Flags,
        "file_done_dic",
        {"OLD-001": {}, "H4610-ORI696": {}},
    )
    monkeypatch.setattr(
        main_window_module.Flags,
        "file_new_path_dic",
        {movie: [tmp_path / "input.wmv"], sibling_movie: [tmp_path / "input-cd2.wmv"]},
    )

    window.save_nfo_info()

    expected_calls = [
        ("write", "天宮まりる"),
        ("write", "天宮まりる"),
    ]
    if outcome != "write_failure":
        expected_calls.append(("reorganize", "天宮まりる"))
    if outcome in ("moved", "partial_failure"):
        expected_calls.append(("save_success", None))
    assert calls == expected_calls
    if outcome == "write_failure":
        assert show_data.data.actor == "旧演员"
        assert sibling_show_data.data.actor == "旧演员"
        assert movie_nfo.read_bytes() == b"old-cd1"
        assert sibling_nfo.read_bytes() == b"old-cd2"
        assert window.Ui.label_save_tips.value.startswith("保存失败，已恢复原信息!")
        assert main_window_module.Flags.file_done_dic == {"OLD-001": {}, "H4610-ORI696": {}}
        assert refreshed == []
        return
    assert show_data.data.actor == "天宮まりる"
    assert sibling_show_data.data.actor == "天宮まりる"
    assert main_window_module.Flags.file_done_dic == {}
    if outcome in ("moved", "partial_failure"):
        expected_label = "已保存并整理!" if outcome == "moved" else "信息已保存，自动整理失败!"
        assert window.Ui.label_save_tips.value.startswith(expected_label)
        assert window.Ui.label_nfo.value == str(new_movie)
        assert sibling_file_info.file_path == new_sibling_movie
        assert sibling_file_info.folder_path == new_sibling_movie.parent
        assert main_window_module.Flags.success_list == {new_movie, new_sibling_movie}
        assert main_window_module.Flags.file_new_path_dic == {
            new_movie: [tmp_path / "input.wmv"],
            new_sibling_movie: [tmp_path / "input-cd2.wmv"],
        }
    else:
        expected_label = "已保存!" if outcome == "unchanged" else "信息已保存，自动整理失败!"
        assert window.Ui.label_save_tips.value.startswith(expected_label)
        assert main_window_module.Flags.success_list == {movie, sibling_movie}
        assert main_window_module.Flags.file_new_path_dic == {
            movie: [tmp_path / "input.wmv"],
            sibling_movie: [tmp_path / "input-cd2.wmv"],
        }
    assert refreshed == [show_data]


def test_batch_save_only_applies_dirty_fields_and_reorganizes_each_entry(monkeypatch, tmp_path: Path):
    entries: list[ShowData] = []
    original_titles = ["第一部标题", "第二部标题"]
    for index, title in enumerate(original_titles, start=1):
        movie = tmp_path / f"movie-{index}.mp4"
        movie.write_bytes(b"movie")
        file_info = FileInfo.empty()
        file_info.file_path = movie
        file_info.folder_path = movie.parent
        file_info.file_name = movie.stem
        file_info.file_ex = movie.suffix
        data = CrawlersResult.empty()
        data.number = f"OLD-{index:03d}"
        data.actor = f"旧演员{index}"
        data.title = title
        entries.append(
            ShowData(
                file_info=file_info,
                data=data,
                other=OtherInfo.empty(),
                show_name=f"row-{index}",
            )
        )

    window = MyMAinWindow.__new__(MyMAinWindow)
    window.Ui = _ui()
    window.Ui.lineEdit_nfo_actor.value = "共同新演员"
    window._nfo_batch_show_names = [entry.show_name for entry in entries]
    window._nfo_dirty_fields = {"actor"}
    window.json_array = {entry.show_name: entry for entry in entries}
    refreshed: list[ShowData] = []
    window.set_main_info = refreshed.append
    calls: list[tuple[str, str, str]] = []

    async def fake_write_nfo(file_info_arg, data_arg, *_args, **_kwargs):
        calls.append(("write", file_info_arg.file_path.name, data_arg.actor))
        return True

    async def fake_reorganize(file_info_arg, data_arg, _other_arg, _success_folder_arg):
        calls.append(("reorganize", file_info_arg.file_path.name, data_arg.actor))
        return MediaReorganizationResult(
            file_info_arg.file_path,
            file_info_arg.file_path,
            file_info_arg.file_path.parent,
            file_info_arg.file_path.parent,
            False,
        )

    def run(awaitable):
        return asyncio.run(awaitable)

    monkeypatch.setattr(main_window_module, "write_nfo", fake_write_nfo)
    monkeypatch.setattr(main_window_module, "reorganize_scraped_media", fake_reorganize)
    monkeypatch.setattr(
        main_window_module,
        "signal_qt",
        SimpleNamespace(stop=False, show_log_text=lambda _message: None, show_traceback_log=lambda _message: None),
    )
    monkeypatch.setattr(
        main_window_module,
        "get_movie_path_setting",
        lambda path: SimpleNamespace(success_folder=path.parent),
    )
    monkeypatch.setattr(main_window_module.executor, "run", run)
    monkeypatch.setattr(main_window_module.Flags, "success_list", {entry.file_info.file_path for entry in entries})
    monkeypatch.setattr(main_window_module.Flags, "file_done_dic", {entry.data.number: {} for entry in entries})
    monkeypatch.setattr(main_window_module.Flags, "file_new_path_dic", {})

    window.save_nfo_info()

    assert calls == [
        ("write", "movie-1.mp4", "共同新演员"),
        ("reorganize", "movie-1.mp4", "共同新演员"),
        ("write", "movie-2.mp4", "共同新演员"),
        ("reorganize", "movie-2.mp4", "共同新演员"),
    ]
    assert [entry.data.actor for entry in entries] == ["共同新演员", "共同新演员"]
    assert [entry.data.title for entry in entries] == original_titles
    assert refreshed == entries
    assert window.Ui.label_save_tips.value.startswith("批量保存完成：成功 2，失败 0!")
