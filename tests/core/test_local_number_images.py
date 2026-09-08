from pathlib import Path

import pytest
from PIL import Image

from mdcx.base.file import move_other_file
from mdcx.config.enums import DownloadableFile, FixedScrapingType, KeepableFile
from mdcx.config.manager import manager
from mdcx.core.image import prepare_local_number_images
from mdcx.core.scraper import prepare_primary_images
from mdcx.models.types import CrawlersResult, OtherInfo


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(800, 450), (600, 600), (600, 840), (600, 1000)])
@pytest.mark.parametrize("face_found", [True, False])
async def test_local_fc2_crop_all_ratios_after_old_artwork_migration(tmp_path, monkeypatch, size, face_found):
    from mdcx.core.file import deal_old_files
    from mdcx.models.flags import Flags

    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    number = "FC2-1844229"
    movie = source / f"{number}.mp4"
    movie.write_bytes(b"test")
    originals = [source / f"{number} {index}.jpg" for index in (2, 10)]
    for path, color in zip(originals, ("red", "blue"), strict=True):
        _save_image(path, size, color)
    original_bytes = {path.name: path.read_bytes() for path in originals}
    for name in ("poster", "thumb", "fanart"):
        _save_image(source / f"{name}.jpg", (800, 450), "green")
    monkeypatch.setattr(manager.config, "use_local_number_images", True)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    monkeypatch.setattr(manager.config, "main_mode", 1)
    monkeypatch.setattr(manager.config, "success_file_move", True)
    monkeypatch.setattr(
        manager.config,
        "download_files",
        [
            DownloadableFile.POSTER,
            DownloadableFile.THUMB,
            DownloadableFile.FANART,
            DownloadableFile.IGNORE_WUMA,
            DownloadableFile.IGNORE_OUMEI,
            DownloadableFile.IGNORE_GUOCHAN,
        ],
    )
    monkeypatch.setattr(manager.config, "keep_files", [KeepableFile.POSTER, KeepableFile.THUMB, KeepableFile.FANART])
    calls = []

    def detect_left(*_args, **_kwargs):
        calls.append(True)
        return 0 if face_found else None

    def detect_box(_image, width, height):
        calls.append(True)
        return (0, 0, width, height) if face_found else None

    monkeypatch.setattr("mdcx.core.image.get_face_crop_left", detect_left)
    monkeypatch.setattr("mdcx.core.face_crop.get_face_crop_box", detect_box)
    result = CrawlersResult.empty()
    result.number = number
    result.scraping_type = FixedScrapingType.FC2
    other = OtherInfo.empty()
    poster, thumb, fanart = [target / f"{name}.jpg" for name in ("poster", "thumb", "fanart")]
    Flags.reset()
    Flags.file_done_dic[number] = {}
    try:
        acquired, _ = await deal_old_files(
            number,
            other,
            source,
            target,
            movie,
            target / f"{number}-thumb.jpg",
            target / f"{number}-poster.jpg",
            target / f"{number}-fanart.jpg",
            target / f"{number}.nfo",
            poster,
            thumb,
            fanart,
        )
        assert acquired
        assert await prepare_primary_images(result, other, "", source, target, poster, thumb, fanart, None)
        await move_other_file(number, source, target, movie.stem, number)
        assert calls == [True]
        assert other.face_detection_failed is not face_found
        for name, contents in original_bytes.items():
            assert not (source / name).exists()
            assert (target / name).read_bytes() == contents
        with Image.open(fanart) as image:
            assert image.size == size
            assert image.getpixel((0, 0))[0] > 240
        with Image.open(poster) as image:
            assert abs(image.height / image.width - 1.5) < 0.01
            assert image.getpixel((0, 0))[0] > 240
    finally:
        Flags.reset()


@pytest.mark.asyncio
@pytest.mark.parametrize("copy_poster", [True, False])
async def test_local_artwork_uses_natural_first_image_and_obeys_face_crop_switch(tmp_path, monkeypatch, copy_poster):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _save_image(source / "FC2-1234567 10.jpg", (800, 450), "blue")
    _save_image(source / "FC2-1234567 2.jpg", (800, 450), "red")
    _save_image(target / "poster.jpg", (800, 450), "green")
    monkeypatch.setattr(manager.config, "use_local_number_images", True)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    # Match the user's settings: other uncensored categories must not override
    # the independent FC2 option, even when old artwork is retained.
    files = [
        DownloadableFile.POSTER,
        DownloadableFile.THUMB,
        DownloadableFile.FANART,
        DownloadableFile.IGNORE_WUMA,
        DownloadableFile.IGNORE_OUMEI,
        DownloadableFile.IGNORE_GUOCHAN,
    ]
    monkeypatch.setattr(manager.config, "keep_files", [KeepableFile.POSTER, KeepableFile.THUMB, KeepableFile.FANART])
    if copy_poster:
        files.append(DownloadableFile.IGNORE_FC2)
    monkeypatch.setattr(manager.config, "download_files", files)
    calls = []
    monkeypatch.setattr("mdcx.core.image.get_face_crop_left", lambda *_args, **_kwargs: calls.append(True) or 400)
    result = CrawlersResult.empty()
    result.number = "FC2-1234567"
    result.scraping_type = FixedScrapingType.FC2
    other = OtherInfo.empty()
    assert await prepare_primary_images(
        result, other, "", source, target, target / "poster.jpg", target / "thumb.jpg", target / "fanart.jpg", None
    )
    with Image.open(target / "fanart.jpg") as image:
        assert image.size == (800, 450)
        assert image.getpixel((0, 0))[0] > 240
    with Image.open(target / "poster.jpg") as image:
        assert image.size == ((800, 450) if copy_poster else (300, 450))
    assert bool(calls) is not copy_poster
    assert not other.face_detection_failed


@pytest.mark.asyncio
async def test_local_face_miss_records_warning_without_failing_scrape(tmp_path, monkeypatch):
    _save_image(tmp_path / "FC2-1234567.jpg", (800, 450), "red")
    monkeypatch.setattr(manager.config, "use_local_number_images", True)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    monkeypatch.setattr(manager.config, "download_files", [DownloadableFile.POSTER])
    monkeypatch.setattr("mdcx.core.image.get_face_crop_left", lambda *_args, **_kwargs: None)
    result = CrawlersResult.empty()
    result.number = "FC2-1234567"
    result.scraping_type = FixedScrapingType.FC2
    other = OtherInfo.empty()
    assert await prepare_local_number_images(
        result,
        other,
        tmp_path,
        tmp_path,
        tmp_path / "poster.jpg",
        tmp_path / "thumb.jpg",
        tmp_path / "fanart.jpg",
        copy_poster=False,
    ) == (True, True)
    assert other.face_detection_failed
    assert result.poster_from == "thumb center"


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
async def test_explicit_url_rescrape_bypasses_local_images_and_forces_web_refresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    calls = []
    result = CrawlersResult.empty()
    result.number = "062526_001"
    other = OtherInfo.empty()

    async def unexpected_local(*_args, **_kwargs):
        pytest.fail("指定详情页重新刮削时不应复用同番号本地图片")

    async def fresh_thumb(*_args, **kwargs):
        calls.append(("thumb", kwargs["force_refresh"]))
        return True

    async def fresh_fanart(*_args, **kwargs):
        calls.append(("fanart", kwargs["force_refresh"]))
        return True

    async def fresh_poster(*_args, **kwargs):
        calls.append(("poster", kwargs["force_refresh"]))
        return True

    monkeypatch.setattr("mdcx.core.scraper.prepare_local_number_images", unexpected_local)
    monkeypatch.setattr("mdcx.core.scraper.thumb_download", fresh_thumb)
    monkeypatch.setattr("mdcx.core.scraper.fanart_download", fresh_fanart)
    monkeypatch.setattr("mdcx.core.scraper.poster_download", fresh_poster)

    assert await prepare_primary_images(
        result,
        other,
        "",
        tmp_path,
        tmp_path,
        tmp_path / "poster.jpg",
        tmp_path / "thumb.jpg",
        tmp_path / "fanart.jpg",
        media_context=None,
        force_refresh=True,
    )
    assert calls == [("thumb", True), ("fanart", True), ("poster", True)]


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
