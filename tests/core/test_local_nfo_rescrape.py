import asyncio
from pathlib import Path

from mdcx.config.manager import manager
from mdcx.core import local_nfo_rescrape as inplace_module
from mdcx.core.local_nfo_rescrape import get_inplace_rescrape_output_name, reorganize_local_nfo_rescrape
from mdcx.models.flags import Flags
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo


def _file_info(path: Path) -> FileInfo:
    info = FileInfo.empty()
    info.file_path = path
    info.folder_path = path.parent
    info.file_name = path.stem
    info.file_ex = path.suffix
    info.number = "FC2-4833176"
    return info


def _data() -> CrawlersResult:
    data = CrawlersResult.empty()
    data.number = "FC2-4833176"
    data.title = "updated title"
    data.actor = "updated actor"
    return data


def _configure_naming(monkeypatch) -> None:
    monkeypatch.setattr(manager.config, "main_mode", 1)
    monkeypatch.setattr(manager.config, "success_file_move", True)
    monkeypatch.setattr(manager.config, "success_file_rename", True)
    monkeypatch.setattr(manager.config, "folder_name", "{{ number }} {{ actor }}")
    monkeypatch.setattr(manager.config, "naming_file", "{{ number }} {{ actor }}")
    monkeypatch.setattr(manager.config, "folder_name_max", 240)
    monkeypatch.setattr(manager.config, "file_name_max", 240)
    monkeypatch.setattr(manager.config, "folder_hd", False)
    monkeypatch.setattr(manager.config, "file_hd", False)
    monkeypatch.setattr(manager.config, "folder_cnword", False)
    monkeypatch.setattr(manager.config, "file_cnword", False)
    monkeypatch.setattr(manager.config, "folder_moword", False)
    monkeypatch.setattr(manager.config, "file_moword", False)
    monkeypatch.setattr(manager.config, "prevent_char", "")
    monkeypatch.setattr(manager.config, "pic_simple_name", False)


def test_local_nfo_rescrape_output_stays_in_source_folder_until_reorganization(monkeypatch, tmp_path: Path):
    source_folder = tmp_path / "library" / "old movie"
    source_folder.mkdir(parents=True)
    movie = source_folder / "old-name.mp4"
    movie.write_bytes(b"movie")
    success_folder = tmp_path / "sorted"
    _configure_naming(monkeypatch)

    paths = get_inplace_rescrape_output_name(_file_info(movie), _data(), success_folder, ".mp4")

    assert paths[0] == source_folder
    assert paths[1] == movie
    assert paths[2] == source_folder / "old-name.nfo"
    assert paths[3] == source_folder / "old-name-poster.jpg"
    assert paths[4] == source_folder / "old-name-thumb.jpg"
    assert paths[5] == source_folder / "old-name-fanart.jpg"
    assert all(path.parent == source_folder for path in (*paths[1:6], *paths[7:10]))
    assert paths[6] == "old-name"
    assert not success_folder.exists()


def test_local_nfo_rescrape_reorganizes_only_inside_current_parent(monkeypatch, tmp_path: Path):
    source_parent = tmp_path / "library"
    source_folder = source_parent / "old movie"
    source_folder.mkdir(parents=True)
    movie = source_folder / "old-name.mp4"
    movie.write_bytes(b"movie")
    (source_folder / "old-name.nfo").write_text("<movie />", encoding="utf-8")
    (source_folder / "old-name.srt").write_text("subtitle", encoding="utf-8")
    success_folder = tmp_path / "sorted"
    _configure_naming(monkeypatch)

    async def no_save_success_list(*_args, **_kwargs):
        return None

    monkeypatch.setattr(inplace_module, "save_success_list", no_save_success_list)
    old_file_new_path_dic = Flags.file_new_path_dic
    old_success_list = Flags.success_list
    try:
        Flags.file_new_path_dic = {}
        Flags.success_list = set()
        file_info = _file_info(movie)
        result = asyncio.run(reorganize_local_nfo_rescrape(file_info, _data(), OtherInfo.empty()))
    finally:
        Flags.file_new_path_dic = old_file_new_path_dic
        Flags.success_list = old_success_list

    expected_folder = source_parent / "FC2-4833176 updated actor"
    expected_movie = expected_folder / "FC2-4833176 updated actor.mp4"
    assert result.moved is True
    assert result.new_folder == expected_folder
    assert result.new_file_path == expected_movie
    assert expected_movie.is_file()
    assert (expected_folder / "FC2-4833176 updated actor.nfo").is_file()
    assert (expected_folder / "FC2-4833176 updated actor.srt").is_file()
    assert not source_folder.exists()
    assert not success_folder.exists()
