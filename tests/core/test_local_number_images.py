from pathlib import Path

import pytest
from PIL import Image

from mdcx.base.file import move_other_file
from mdcx.config.enums import DownloadableFile, FixedScrapingType
from mdcx.config.manager import manager
from mdcx.core.image import prepare_local_number_images
from mdcx.core.scraper import prepare_primary_images
from mdcx.models.types import CrawlersResult, OtherInfo


def _save_image(path: Path, size: tuple[int, int], color: str) -> None:
    Image.new("RGB", size, color).save(path)


@pytest.mark.asyncio
async def test_prepare_local_number_images_builds_artwork_then_success_path_moves_all_matches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _save_image(source / "FC2-4869199 A.jpg", (800, 450), "red")
    _save_image(source / ".FC2-4869199 B.png", (640, 360), "blue")
    _save_image(source / ".fc2-4869199 C.webp", (320, 180), "green")
    _save_image(source / "FC2-1111111.jpg", (100, 100), "black")

    monkeypatch.setattr(manager.config, "use_local_number_images", True)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    monkeypatch.setattr(manager.config, "main_mode", 1)
    monkeypatch.setattr(manager.config, "success_file_move", True)
    monkeypatch.setattr(manager.config, "success_file_rename", True)
    monkeypatch.setattr(
        manager.config,
        "download_files",
        [DownloadableFile.POSTER, DownloadableFile.THUMB, DownloadableFile.FANART],
    )
    result = CrawlersResult.empty()
    result.number = "FC2-4869199"
    result.scraping_type = FixedScrapingType.FC2
    other = OtherInfo.empty()
    poster = target / "FC2-4869199-poster.jpg"
    thumb = target / "FC2-4869199-thumb.jpg"
    fanart = target / "FC2-4869199-fanart.jpg"

    found, success = await prepare_local_number_images(
        result,
        other,
        source,
        target,
        poster,
        thumb,
        fanart,
        copy_poster=False,
    )

    assert (found, success) == (True, True)
    assert (source / "FC2-4869199 A.jpg").is_file()
    assert (source / ".FC2-4869199 B.png").is_file()
    assert (source / ".fc2-4869199 C.webp").is_file()
    assert (source / "FC2-1111111.jpg").is_file()

    await move_other_file(result.number, source, target, "unrelated", "unrelated")

    assert not (source / "FC2-4869199 A.jpg").exists()
    assert not (source / ".FC2-4869199 B.png").exists()
    assert not (source / ".fc2-4869199 C.webp").exists()
    assert (target / "FC2-4869199 A.jpg").is_file()
    assert (target / ".FC2-4869199 B.png").is_file()
    assert (target / ".fc2-4869199 C.webp").is_file()

    # 文件名排序后以“.FC2-4869199 B.png”为第一张主艺术图。
    with Image.open(thumb) as image:
        assert image.size == (640, 360)
        assert image.format == "JPEG"
    with Image.open(fanart) as image:
        assert image.size == (640, 360)
        assert image.format == "JPEG"
    with Image.open(poster) as image:
        assert image.size == (240, 360)
        assert image.format == "JPEG"

    assert other.thumb_path == thumb
    assert other.fanart_path == fanart
    assert other.poster_path == poster
    assert other.thumb_marked is False
    assert other.fanart_marked is False
    assert other.poster_marked is False


@pytest.mark.asyncio
async def test_prepare_primary_images_does_not_call_web_downloads_when_local_image_matches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _save_image(source / "FC2-4869199 A.jpg", (800, 450), "red")

    monkeypatch.setattr(manager.config, "use_local_number_images", True)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    monkeypatch.setattr(
        manager.config,
        "download_files",
        [DownloadableFile.POSTER, DownloadableFile.THUMB, DownloadableFile.FANART],
    )
    result = CrawlersResult.empty()
    result.number = "FC2-4869199"
    result.scraping_type = FixedScrapingType.FC2
    other = OtherInfo.empty()

    async def unexpected_download(*_args, **_kwargs):
        pytest.fail("命中同番号本地图片后不应调用网站图片下载流程")

    monkeypatch.setattr("mdcx.core.scraper.thumb_download", unexpected_download)
    monkeypatch.setattr("mdcx.core.scraper.fanart_download", unexpected_download)
    monkeypatch.setattr("mdcx.core.scraper.poster_download", unexpected_download)

    assert await prepare_primary_images(
        result,
        other,
        "",
        source,
        target,
        target / "FC2-4869199-poster.jpg",
        target / "FC2-4869199-thumb.jpg",
        target / "FC2-4869199-fanart.jpg",
        media_context=None,
    )


@pytest.mark.asyncio
async def test_prepare_local_number_images_does_not_fall_back_past_first_sorted_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "ABC-123 A.jpg").write_text("not an image", encoding="utf-8")
    _save_image(source / "ABC-123 B.jpg", (800, 450), "blue")

    monkeypatch.setattr(manager.config, "use_local_number_images", True)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    monkeypatch.setattr(manager.config, "download_files", [DownloadableFile.THUMB])
    result = CrawlersResult.empty()
    result.number = "ABC-123"

    found, success = await prepare_local_number_images(
        result,
        OtherInfo.empty(),
        source,
        target,
        target / "poster.jpg",
        target / "thumb.jpg",
        target / "fanart.jpg",
        copy_poster=False,
    )

    assert (found, success) == (True, False)
    assert not (target / "thumb.jpg").exists()
