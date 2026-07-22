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


@pytest.mark.parametrize("outcome", ["moved", "unchanged", "failure"])
def test_save_nfo_info_clears_number_caches_after_writing_nfo(monkeypatch, tmp_path: Path, outcome: str):
    movie = tmp_path / "JAV_output" / "望月奈々" / "old" / "H4610-ORI696 望月奈々.wmv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    file_info = FileInfo.empty()
    file_info.file_path = movie
    file_info.folder_path = movie.parent
    file_info.file_name = movie.stem
    file_info.file_ex = movie.suffix
    scraped_data = CrawlersResult.empty()
    scraped_data.number = "OLD-001"
    show_data = ShowData(file_info=file_info, data=scraped_data, other=OtherInfo.empty(), show_name="row")

    window = MyMAinWindow.__new__(MyMAinWindow)
    window.Ui = _ui()
    window.now_show_name = "row"
    window.json_array = {"row": show_data}
    refreshed: list[ShowData] = []
    window.set_main_info = refreshed.append
    calls: list[tuple[str, object]] = []
    new_movie = (
        tmp_path / "JAV_output" / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる" / "H4610-ORI696 天宮まりる.wmv"
    )

    async def fake_write_nfo(*args, **kwargs):
        calls.append(("write", args[1].actor))
        return True

    async def fake_reorganize(file_info_arg, data_arg, other_arg, success_folder_arg):
        calls.append(("reorganize", data_arg.actor))
        assert file_info_arg is file_info
        assert other_arg is show_data.other
        assert success_folder_arg == tmp_path / "JAV_output"
        if outcome == "failure":
            raise MediaReorganizationError("injected failure")
        if outcome == "unchanged":
            return MediaReorganizationResult(movie, movie, movie.parent, movie.parent, False)
        file_info_arg.file_path = new_movie
        file_info_arg.folder_path = new_movie.parent
        file_info_arg.file_name = new_movie.stem
        return MediaReorganizationResult(movie, new_movie, movie.parent, new_movie.parent, True)

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
    monkeypatch.setattr(main_window_module.Flags, "success_list", {movie})
    monkeypatch.setattr(
        main_window_module.Flags,
        "file_done_dic",
        {"OLD-001": {}, "H4610-ORI696": {}},
    )
    monkeypatch.setattr(main_window_module.Flags, "file_new_path_dic", {movie: [tmp_path / "input.wmv"]})

    window.save_nfo_info()

    expected_calls = [("write", "天宮まりる"), ("reorganize", "天宮まりる")]
    if outcome == "moved":
        expected_calls.append(("save_success", None))
    assert calls == expected_calls
    assert show_data.data.actor == "天宮まりる"
    assert main_window_module.Flags.file_done_dic == {}
    if outcome == "moved":
        assert window.Ui.label_save_tips.value.startswith("已保存并整理!")
        assert window.Ui.label_nfo.value == str(new_movie)
        assert main_window_module.Flags.success_list == {new_movie}
        assert main_window_module.Flags.file_new_path_dic == {new_movie: [tmp_path / "input.wmv"]}
    else:
        expected_label = "已保存!" if outcome == "unchanged" else "信息已保存，自动整理失败!"
        assert window.Ui.label_save_tips.value.startswith(expected_label)
        assert main_window_module.Flags.success_list == {movie}
        assert main_window_module.Flags.file_new_path_dic == {movie: [tmp_path / "input.wmv"]}
    assert refreshed == [show_data]
