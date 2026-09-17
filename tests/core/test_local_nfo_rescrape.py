from pathlib import Path

from mdcx.config.manager import manager
from mdcx.core import scraper as scraper_module
from mdcx.core.scraper import _get_inplace_rescrape_output_name, again_search
from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags
from mdcx.models.types import CrawlersResult, FileInfo


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


def test_local_nfo_rescrape_output_stays_in_source_folder_until_reorganization(monkeypatch, tmp_path: Path):
    source_folder = tmp_path / "library" / "old movie"
    source_folder.mkdir(parents=True)
    movie = source_folder / "old-name.mp4"
    movie.write_bytes(b"movie")
    success_folder = tmp_path / "sorted"

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

    paths = _get_inplace_rescrape_output_name(_file_info(movie), _data(), success_folder, ".mp4")

    assert paths[0] == source_folder
    assert paths[1] == movie
    assert paths[2] == source_folder / "old-name.nfo"
    assert paths[3] == source_folder / "old-name-poster.jpg"
    assert paths[4] == source_folder / "old-name-thumb.jpg"
    assert paths[5] == source_folder / "old-name-fanart.jpg"
    assert all(path.parent == source_folder for path in (*paths[1:6], *paths[7:10]))
    assert not success_folder.exists()


def test_again_search_transfers_local_nfo_inplace_marker(monkeypatch, tmp_path: Path):
    movie = tmp_path / "movie.mp4"
    started = []
    old_again = Flags.again_dic
    old_new_again = Flags.new_again_dic
    old_pending = Flags.again_inplace_paths
    old_active = Flags.new_again_inplace_paths
    try:
        Flags.again_dic = {movie: ("FC2-4833176", "", "")}
        Flags.again_inplace_paths = {movie}
        Flags.new_again_dic = {}
        Flags.new_again_inplace_paths = set()
        monkeypatch.setattr(scraper_module, "start_new_scrape", lambda mode, paths: started.append((mode, paths)))

        again_search()

        assert Flags.new_again_dic == {movie: ("FC2-4833176", "", "")}
        assert Flags.new_again_inplace_paths == {movie}
        assert Flags.again_dic == {}
        assert Flags.again_inplace_paths == set()
        assert started == [(FileMode.Again, [movie])]
    finally:
        Flags.again_dic = old_again
        Flags.new_again_dic = old_new_again
        Flags.again_inplace_paths = old_pending
        Flags.new_again_inplace_paths = old_active
