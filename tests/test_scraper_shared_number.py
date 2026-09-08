import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdcx.models.enums import FileMode
from mdcx.models.flags import Flags
from mdcx.models.types import FileInfo


def _build_file_info(number: str) -> FileInfo:
    file_info = FileInfo.empty()
    file_info.number = number
    file_info.mosaic = "有码"
    file_info.file_path = Path(f"{number}.mp4")
    file_info.folder_path = Path(".")
    file_info.file_name = number
    file_info.file_ex = ".mp4"
    file_info.file_show_name = f"{number}.mp4"
    file_info.file_show_path = file_info.file_path
    file_info.sub_list = []
    return file_info


def _setup_scraper_test_env(monkeypatch: pytest.MonkeyPatch):
    from mdcx.core import scraper as scraper_module

    Flags.reset()

    async def fake_check_file(*_args, **_kwargs):
        return True

    def fake_get_movie_path_setting(_file_path=None):
        return SimpleNamespace(success_folder=Path("."), movie_path=Path("."))

    original_sleep = asyncio.sleep

    async def fast_sleep(_seconds: float):
        await original_sleep(0)

    monkeypatch.setattr(scraper_module, "check_file", fake_check_file)
    monkeypatch.setattr(scraper_module, "get_movie_path_setting", fake_get_movie_path_setting)
    monkeypatch.setattr(scraper_module.asyncio, "sleep", fast_sleep)
    from mdcx.config.enums import FixedScrapingType

    monkeypatch.setattr(scraper_module.manager.config, "fixed_scraping_type", FixedScrapingType.YOUMA)
    monkeypatch.setattr(scraper_module.manager.config, "main_mode", 1)
    monkeypatch.setattr(scraper_module.manager.config, "file_size", "0")
    return scraper_module


@pytest.mark.asyncio
async def test_same_number_waiting_task_stops_on_failed_status(monkeypatch: pytest.MonkeyPatch):
    scraper_module = _setup_scraper_test_env(monkeypatch)
    scraper = scraper_module.Scraper(crawler_provider=object())
    file_info = _build_file_info("ABC-123")

    scraper.session.cache("json_get_status")[file_info.number] = None

    task = asyncio.create_task(scraper._process_one_file(file_info, FileMode.Default))
    await asyncio.sleep(0.01)
    scraper.session.cache("json_get_status")[file_info.number] = False

    result = await asyncio.wait_for(task, timeout=1)
    assert result == (None, None)


@pytest.mark.asyncio
async def test_same_number_failed_status_returns_without_wait(monkeypatch: pytest.MonkeyPatch):
    scraper_module = _setup_scraper_test_env(monkeypatch)
    scraper = scraper_module.Scraper(crawler_provider=object())
    file_info = _build_file_info("DEF-456")

    scraper.session.cache("json_get_status")[file_info.number] = False

    result = await asyncio.wait_for(scraper._process_one_file(file_info, FileMode.Default), timeout=1)
    assert result == (None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("first_has_sub", [True, False])
async def test_shared_metadata_excludes_local_tags_and_uses_own_session(monkeypatch, first_has_sub):
    from mdcx.config.enums import DownloadableFile, Language, TagInclude
    from mdcx.models.session import ScrapeSession
    from mdcx.models.types import CrawlersResult

    module = _setup_scraper_test_env(monkeypatch)
    monkeypatch.setattr(module.manager.config, "download_files", [DownloadableFile.NFO])
    monkeypatch.setattr(module.manager.config, "keep_files", [])
    monkeypatch.setattr(
        module.manager.config, "nfo_tag_include", [TagInclude.CNWORD, TagInclude.MOSAIC, TagInclude.DEFINITION]
    )
    monkeypatch.setattr(module.manager.config, "hd_get", "video")
    for name in ("deal_some_field", "replace_special_word", "replace_word", "show_result"):
        monkeypatch.setattr(module, name, lambda *_: None)

    async def noop(*_):
        pass

    monkeypatch.setattr(module, "translate_actor", noop)
    monkeypatch.setattr(module, "translate_title_outline", noop)
    from mdcx.core import translate

    monkeypatch.setattr(translate.resources, "info_mapping_data", None)
    monkeypatch.setattr(
        type(module.manager.config),
        "get_field_config",
        lambda self, _: SimpleNamespace(
            translate=False,
            language=Language.ZH_CN,
        ),
    )
    crawls = []

    async def crawl(self, *_):
        crawls.append(True)
        result = CrawlersResult.empty()
        result.number = "ABC-123"
        result.mosaic = "有码"
        result.tags = ["剧情"]
        return result

    monkeypatch.setattr(module.FileScraper, "run", crawl)
    sizes = iter([("2160P", "UNLISTED-CODEC"), ("1080P", "SECOND-CODEC")])

    async def video_size(*_):
        return next(sizes)

    monkeypatch.setattr(module, "get_video_size", video_size)
    results = []

    class MetadataReady(Exception):
        pass

    def capture(_file, result):
        results.append(result)
        raise MetadataReady

    monkeypatch.setattr(module, "show_movie_info", capture)
    scraper = module.Scraper(object())
    unrelated = ScrapeSession()
    Flags.bind_session(unrelated)
    for index, has_sub in enumerate([first_has_sub, not first_has_sub]):
        file_info = _build_file_info("ABC-123")
        file_info.has_sub = has_sub
        file_info.mosaic = "有码" if index == 0 else "无码流出"
        with pytest.raises(MetadataReady):
            await scraper._process_one_file(file_info, FileMode.Default)
        scraper.session.cache("json_get_status")[file_info.number] = True

    assert len(crawls) == 1
    assert ("中文字幕" in results[0].tags) is first_has_sub
    assert ("中文字幕" in results[1].tags) is not first_has_sub
    assert "UNLISTED-CODEC" in results[0].tags
    assert "UNLISTED-CODEC" not in results[1].tags
    assert "2160P" not in results[1].tags
    assert "SECOND-CODEC" in results[1].tags
    assert "无码流出" in results[1].tags
    assert "有码" not in results[1].tags
    assert scraper.session.scrape_results["ABC-123"].tags == ["剧情"]
    assert not unrelated.scrape_results
    assert not unrelated.cache("json_get_status")
