from pathlib import Path

import pytest
from PIL import Image

from mdcx.config.enums import DownloadableFile, FixedScrapingType, KeepableFile
from mdcx.config.manager import manager
from mdcx.core.web import extrafanart_download, fanart_download, poster_download, thumb_download
from mdcx.models.types import CrawlersResult, OtherInfo


class _ImageContext:
    async def save_image(self, _url: str, destination: Path, _folder: Path) -> bool:
        Image.new("RGB", (32, 32), "blue").save(destination)
        return True


class _FailingImageContext:
    async def save_image(self, _url: str, _destination: Path, _folder: Path) -> bool:
        return False


@pytest.mark.asyncio
async def test_force_refresh_replaces_a_kept_thumb_atomically(monkeypatch, tmp_path: Path):
    thumb_path = tmp_path / "062526_001-thumb.jpg"
    Image.new("RGB", (32, 32), "red").save(thumb_path)
    monkeypatch.setattr(manager.config, "download_files", [DownloadableFile.THUMB])
    monkeypatch.setattr(manager.config, "keep_files", [KeepableFile.THUMB])

    result = CrawlersResult.empty()
    result.number = "062526_001"
    result.thumb = "https://example.invalid/kzdbdxg.jpg"
    result.thumb_from = "avsox"
    other = OtherInfo.empty()
    other.thumb_path = thumb_path

    assert await thumb_download(
        result,
        other,
        "",
        tmp_path,
        thumb_path,
        _ImageContext(),
        force_refresh=True,
    )

    with Image.open(thumb_path) as image:
        assert image.getpixel((0, 0))[2] > image.getpixel((0, 0))[0]
    assert not thumb_path.with_suffix(".[DOWNLOAD].jpg").exists()
    assert other.thumb_path == thumb_path


@pytest.mark.asyncio
async def test_force_refresh_failure_preserves_kept_thumb_and_reports_failure(monkeypatch, tmp_path: Path):
    thumb_path = tmp_path / "062526_001-thumb.jpg"
    Image.new("RGB", (32, 32), "red").save(thumb_path)
    monkeypatch.setattr(manager.config, "download_files", [DownloadableFile.THUMB])
    monkeypatch.setattr(manager.config, "keep_files", [KeepableFile.THUMB])

    result = CrawlersResult.empty()
    result.number = "062526_001"
    result.thumb = "https://example.invalid/unavailable.jpg"
    result.thumb_from = "avsox"
    other = OtherInfo.empty()
    other.thumb_path = thumb_path

    assert not await thumb_download(
        result,
        other,
        "",
        tmp_path,
        thumb_path,
        _FailingImageContext(),
        force_refresh=True,
    )

    with Image.open(thumb_path) as image:
        assert image.getpixel((0, 0))[0] > image.getpixel((0, 0))[2]
    assert not thumb_path.with_suffix(".[DOWNLOAD].jpg").exists()


@pytest.mark.asyncio
async def test_force_refresh_replaces_kept_poster_and_fanart(monkeypatch, tmp_path: Path):
    poster_path = tmp_path / "062526_001-poster.jpg"
    thumb_path = tmp_path / "062526_001-thumb.jpg"
    fanart_path = tmp_path / "062526_001-fanart.jpg"
    Image.new("RGB", (32, 32), "red").save(poster_path)
    Image.new("RGB", (32, 32), "blue").save(thumb_path)
    Image.new("RGB", (32, 32), "red").save(fanart_path)
    monkeypatch.setattr(manager.config, "download_files", [DownloadableFile.POSTER, DownloadableFile.FANART])
    monkeypatch.setattr(manager.config, "keep_files", [KeepableFile.POSTER, KeepableFile.FANART])

    result = CrawlersResult.empty()
    result.number = "062526_001"
    result.scraping_type = FixedScrapingType.WUMA
    result.poster = "https://example.invalid/kzdbdxg-poster.jpg"
    result.poster_from = "avsox"
    result.image_download = True
    other = OtherInfo.empty()
    other.poster_path = poster_path
    other.thumb_path = thumb_path
    other.fanart_path = fanart_path

    assert await poster_download(
        result,
        other,
        "",
        tmp_path,
        poster_path,
        _ImageContext(),
        force_refresh=True,
    )
    assert await fanart_download(
        result.number,
        other,
        "",
        fanart_path,
        force_refresh=True,
    )

    for image_path in (poster_path, fanart_path):
        with Image.open(image_path) as image:
            assert image.getpixel((0, 0))[2] > image.getpixel((0, 0))[0]
    assert not poster_path.with_suffix(".[DOWNLOAD].jpg").exists()
    assert not fanart_path.with_suffix(".[COPY].jpg").exists()


@pytest.mark.asyncio
async def test_force_refresh_replaces_entire_extrafanart_set(monkeypatch, tmp_path: Path):
    extrafanart_folder = tmp_path / "extrafanart"
    extrafanart_folder.mkdir()
    Image.new("RGB", (32, 32), "red").save(extrafanart_folder / "fanart1.jpg")
    Image.new("RGB", (32, 32), "red").save(extrafanart_folder / "fanart2.jpg")
    monkeypatch.setattr(manager.config, "download_files", [DownloadableFile.EXTRAFANART])
    monkeypatch.setattr(manager.config, "keep_files", [KeepableFile.EXTRAFANART])

    async def save_extrafanart(task):
        Image.new("RGB", (32, 32), "blue").save(task[1])
        return True

    monkeypatch.setattr("mdcx.core.web.download_extrafanart_task", save_extrafanart)

    assert await extrafanart_download(
        ["https://example.invalid/kzdbdxg-fanart.jpg"],
        "avsox",
        tmp_path,
        force_refresh=True,
    )

    assert [path.name for path in extrafanart_folder.iterdir()] == ["fanart1.jpg"]
    with Image.open(extrafanart_folder / "fanart1.jpg") as image:
        assert image.getpixel((0, 0))[2] > image.getpixel((0, 0))[0]
    assert not (tmp_path / "extrafanart[DOWNLOAD]").exists()
