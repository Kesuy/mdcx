from pathlib import Path
from types import SimpleNamespace

import pytest

from mdcx.base.file import clean_rescrape_source_folder
from mdcx.config.manager import manager
from mdcx.core.scraper import Scraper
from mdcx.models.enums import FileMode
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo


@pytest.fixture
def source(monkeypatch, tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    folder = root / "old-name"
    folder.mkdir()
    monkeypatch.setattr(manager.config, "del_empty_folder", True)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    paths = SimpleNamespace(
        movie_paths=[root],
        success_folder=tmp_path / "success",
        failed_folder=tmp_path / "failed",
        softlink_path=tmp_path / "links",
    )
    monkeypatch.setattr("mdcx.base.file.get_movie_path_setting", lambda _: paths)
    return folder / "ABC-123.mp4"


@pytest.mark.asyncio
async def test_remove_only_empty_source_preserving_parent_and_unrelated_empty_folder(source):
    sibling = source.parent.parent / "unrelated"
    sibling.mkdir()
    await clean_rescrape_source_folder(source)
    assert not source.parent.exists()
    assert source.parent.parent.is_dir()
    assert sibling.is_dir()


@pytest.mark.asyncio
@pytest.mark.parametrize("remaining", ["ABC-123.mp4", "photo.jpg", ".DS_Store", "skip", "subfolder"])
async def test_never_remove_nonempty_source(source, remaining):
    item = source.parent / remaining
    item.mkdir() if remaining == "subfolder" else item.write_text("keep")
    await clean_rescrape_source_folder(source)
    assert item.exists()


@pytest.mark.asyncio
async def test_preserve_library_root(source):
    source.parent.rmdir()
    await clean_rescrape_source_folder(source.parent.parent / source.name)
    assert source.parent.parent.is_dir()


@pytest.mark.asyncio
@pytest.mark.parametrize("option,value", [("del_empty_folder", False), ("soft_link", 1), ("soft_link", 2)])
async def test_respects_cleanup_and_link_settings(source, monkeypatch, option, value):
    monkeypatch.setattr(manager.config, option, value)
    await clean_rescrape_source_folder(source)
    assert source.parent.is_dir()


@pytest.mark.asyncio
@pytest.mark.parametrize("is_junction", [False, True])
async def test_preserve_directory_links(source, monkeypatch, is_junction):
    monkeypatch.setattr(Path, "is_junction" if is_junction else "is_symlink", lambda self: self == source.parent)
    await clean_rescrape_source_folder(source)
    assert source.parent.is_dir()


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["", "https://example.com/movie/ABC-123"])
@pytest.mark.parametrize("succeeds", [False, True])
async def test_rescrape_success_cleans_source_but_failure_preserves_it(source, monkeypatch, url, succeeds):
    file_info = FileInfo.empty()
    file_info.file_path = source
    file_info.folder_path = source.parent
    file_info.appoint_url = url

    async def process(*args):
        return (CrawlersResult.empty(), OtherInfo.empty()) if succeeds else (None, None)

    monkeypatch.setattr(Scraper, "_process_one_file_with_context", process)
    scraper = Scraper.__new__(Scraper)
    await scraper._process_one_file(file_info, FileMode.Again)
    assert source.parent.exists() is not succeeds
