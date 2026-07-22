from pathlib import Path

import pytest

from mdcx.config.manager import manager
from mdcx.core.media_reorganization import MediaReorganizationError, reorganize_scraped_media
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo


def _configure_naming(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(manager.config, "success_file_move", True)
    monkeypatch.setattr(manager.config, "success_file_rename", True)
    monkeypatch.setattr(manager.config, "folder_name", "{{ actor }}/{{ number }} {{ title }} {{ actor }}")
    monkeypatch.setattr(manager.config, "naming_file", "{{ number }} {{ actor }}")
    monkeypatch.setattr(manager.config, "folder_name_max", 240)
    monkeypatch.setattr(manager.config, "file_name_max", 240)
    monkeypatch.setattr(manager.config, "folder_hd", False)
    monkeypatch.setattr(manager.config, "file_hd", False)
    monkeypatch.setattr(manager.config, "folder_cnword", False)
    monkeypatch.setattr(manager.config, "file_cnword", False)
    monkeypatch.setattr(manager.config, "folder_moword", False)
    monkeypatch.setattr(manager.config, "file_moword", False)
    monkeypatch.setattr(manager.config, "success_file_move", True)
    monkeypatch.setattr(manager.config, "success_file_rename", True)
    monkeypatch.setattr(manager.config, "main_mode", 1)
    monkeypatch.setattr(manager.config, "soft_link", 0)
    monkeypatch.setattr(manager.config, "prevent_char", "")
    monkeypatch.setattr(manager.config, "media_type", [".wmv", ".mp4"])


def _build_data() -> CrawlersResult:
    data = CrawlersResult.empty()
    data.number = "H4610-ORI696"
    data.title = "望月 奈々"
    data.actor = "天宮まりる"
    return data


def _build_file_info(path: Path) -> FileInfo:
    info = FileInfo.empty()
    info.number = "H4610-ORI696"
    info.file_path = path
    info.folder_path = path.parent
    info.file_name = path.stem
    info.file_ex = path.suffix
    info.file_show_name = path.name
    info.file_show_path = path
    return info


@pytest.mark.asyncio
async def test_reorganize_scraped_media_matches_edited_actor_example(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    for name in (
        old_movie.name,
        "H4610-ORI696 望月奈々.nfo",
        "fanart.jpg",
        "poster.jpg",
        "thumb.jpg",
    ):
        (old_folder / name).write_text(name, encoding="utf-8")

    file_info = _build_file_info(old_movie)
    other = OtherInfo.empty()
    other.fanart_path = old_folder / "fanart.jpg"
    other.poster_path = old_folder / "poster.jpg"
    other.thumb_path = old_folder / "thumb.jpg"

    result = await reorganize_scraped_media(file_info, _build_data(), other, output)

    expected_folder = output / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる"
    expected_movie = expected_folder / "H4610-ORI696 天宮まりる.wmv"
    assert result.old_file_path == old_movie
    assert result.new_file_path == expected_movie
    assert sorted(path.name for path in expected_folder.iterdir()) == [
        "H4610-ORI696 天宮まりる.nfo",
        "H4610-ORI696 天宮まりる.wmv",
        "fanart.jpg",
        "poster.jpg",
        "thumb.jpg",
    ]
    assert not old_folder.exists()
    assert not (output / "望月奈々").exists()
    assert file_info.file_path == expected_movie
    assert file_info.folder_path == expected_folder
    assert file_info.file_name == "H4610-ORI696 天宮まりる"
    assert other.fanart_path == expected_folder / "fanart.jpg"
    assert other.poster_path == expected_folder / "poster.jpg"
    assert other.thumb_path == expected_folder / "thumb.jpg"


@pytest.mark.asyncio
async def test_reorganize_scraped_media_refuses_existing_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_movie.write_bytes(b"old")
    target_folder = output / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる"
    target_folder.mkdir(parents=True)
    marker = target_folder / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    file_info = _build_file_info(old_movie)

    with pytest.raises(MediaReorganizationError, match="目标目录已存在"):
        await reorganize_scraped_media(file_info, _build_data(), OtherInfo.empty(), output)

    assert old_movie.read_bytes() == b"old"
    assert marker.read_text(encoding="utf-8") == "keep"
    assert file_info.file_path == old_movie


@pytest.mark.asyncio
async def test_reorganize_scraped_media_refuses_folder_with_another_movie(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_movie.write_bytes(b"movie")
    another_movie = old_folder / "OTHER-001.mp4"
    another_movie.write_bytes(b"other")
    file_info = _build_file_info(old_movie)

    with pytest.raises(MediaReorganizationError, match="多个影片文件"):
        await reorganize_scraped_media(file_info, _build_data(), OtherInfo.empty(), output)

    assert old_movie.exists()
    assert another_movie.exists()


@pytest.mark.asyncio
async def test_reorganize_scraped_media_rolls_back_partial_rename(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_nfo = old_folder / "H4610-ORI696 望月奈々.nfo"
    old_movie.write_bytes(b"movie")
    old_nfo.write_text("nfo", encoding="utf-8")
    file_info = _build_file_info(old_movie)

    from mdcx.core import media_reorganization as module

    original_rename = module._rename_case_safe
    rename_count = 0

    def fail_second_rename(source: Path, target: Path) -> None:
        nonlocal rename_count
        rename_count += 1
        if rename_count == 2:
            raise OSError("injected rename failure")
        original_rename(source, target)

    monkeypatch.setattr(module, "_rename_case_safe", fail_second_rename)

    with pytest.raises(MediaReorganizationError, match="已尝试回滚"):
        await reorganize_scraped_media(file_info, _build_data(), OtherInfo.empty(), output)

    target_folder = output / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる"
    assert not target_folder.exists()
    assert old_movie.read_bytes() == b"movie"
    assert old_nfo.read_text(encoding="utf-8") == "nfo"
    assert file_info.file_path == old_movie


@pytest.mark.asyncio
async def test_reorganize_scraped_media_never_overwrites_concurrently_created_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_movie.write_bytes(b"movie")
    target_folder = output / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる"

    from mdcx.core import media_reorganization as module

    original_rename = module._rename_no_replace

    def create_target_before_rename(source: Path, target: Path) -> None:
        if source == old_folder:
            target.mkdir()
        original_rename(source, target)

    monkeypatch.setattr(module, "_rename_no_replace", create_target_before_rename)

    with pytest.raises(MediaReorganizationError, match="目标已存在"):
        await reorganize_scraped_media(_build_file_info(old_movie), _build_data(), OtherInfo.empty(), output)

    assert old_movie.read_bytes() == b"movie"
    assert target_folder.is_dir()
    assert list(target_folder.iterdir()) == []


@pytest.mark.asyncio
async def test_reorganize_scraped_media_reports_incomplete_rollback_and_tracks_actual_movie(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_nfo = old_folder / "H4610-ORI696 望月奈々.nfo"
    old_movie.write_bytes(b"movie")
    old_nfo.write_text("nfo", encoding="utf-8")
    file_info = _build_file_info(old_movie)

    from mdcx.core import media_reorganization as module

    original_rename = module._rename_case_safe
    rename_count = 0

    def fail_nfo_and_movie_rollback(source: Path, target: Path) -> None:
        nonlocal rename_count
        rename_count += 1
        if rename_count in (3, 4):
            raise OSError(f"injected failure {rename_count}")
        original_rename(source, target)

    monkeypatch.setattr(module, "_rename_case_safe", fail_nfo_and_movie_rollback)

    with pytest.raises(MediaReorganizationError, match="回滚不完整"):
        await reorganize_scraped_media(file_info, _build_data(), OtherInfo.empty(), output)

    actual_movie = old_folder / "H4610-ORI696 天宮まりる.wmv"
    assert actual_movie.read_bytes() == b"movie"
    assert old_nfo.read_text(encoding="utf-8") == "nfo"
    assert file_info.file_path == actual_movie


@pytest.mark.asyncio
async def test_reorganize_scraped_media_refuses_source_outside_success_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    output.mkdir()
    old_folder = tmp_path / "other-drive" / "望月奈々" / "old"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_movie.write_bytes(b"movie")
    file_info = _build_file_info(old_movie)

    with pytest.raises(MediaReorganizationError, match="不在成功输出目录内"):
        await reorganize_scraped_media(file_info, _build_data(), OtherInfo.empty(), output)

    assert old_movie.exists()
    assert not (output / "天宮まりる").exists()


@pytest.mark.asyncio
async def test_reorganize_scraped_media_refuses_broken_symlink_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _configure_naming(monkeypatch)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_movie.write_bytes(b"movie")
    target_folder = output / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる"
    target_folder.parent.mkdir(parents=True)
    target_folder.symlink_to(tmp_path / "missing-target", target_is_directory=True)

    with pytest.raises(MediaReorganizationError, match="目标目录已存在"):
        await reorganize_scraped_media(_build_file_info(old_movie), _build_data(), OtherInfo.empty(), output)

    assert old_movie.exists()
    assert target_folder.is_symlink()


@pytest.mark.asyncio
async def test_reorganize_scraped_media_refuses_symlink_success_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _configure_naming(monkeypatch)
    real_output = tmp_path / "real-output"
    real_output.mkdir()
    output = tmp_path / "JAV_output"
    output.symlink_to(real_output, target_is_directory=True)
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_movie.write_bytes(b"movie")

    with pytest.raises(MediaReorganizationError, match="符号链接或 junction"):
        await reorganize_scraped_media(_build_file_info(old_movie), _build_data(), OtherInfo.empty(), output)

    assert old_movie.read_bytes() == b"movie"


@pytest.mark.asyncio
async def test_reorganize_scraped_media_handles_windows_case_only_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _configure_naming(monkeypatch)
    monkeypatch.setattr(manager.config, "folder_name", "{{ actor }}/fixed")
    monkeypatch.setattr(manager.config, "naming_file", "{{ number }} {{ actor }}")
    output = tmp_path / "JAV_output"
    old_folder = output / "ACTOR" / "fixed"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 ACTOR.wmv"
    old_nfo = old_folder / "H4610-ORI696 ACTOR.nfo"
    old_movie.write_bytes(b"movie")
    old_nfo.write_text("nfo", encoding="utf-8")
    data = _build_data()
    data.actor = "actor"

    from mdcx.core import media_reorganization as module

    monkeypatch.setattr(module.os.path, "normcase", lambda path: str(path).lower())

    result = await reorganize_scraped_media(_build_file_info(old_movie), data, OtherInfo.empty(), output)

    expected_folder = output / "actor" / "fixed"
    assert result.new_file_path == expected_folder / "H4610-ORI696 actor.wmv"
    assert (expected_folder / "H4610-ORI696 actor.wmv").read_bytes() == b"movie"
    assert (expected_folder / "H4610-ORI696 actor.nfo").read_text(encoding="utf-8") == "nfo"
    assert not (output / "ACTOR").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("move_enabled", "rename_enabled", "expected_folder_changed", "expected_name"),
    [
        (False, True, False, "H4610-ORI696 天宮まりる.wmv"),
        (True, False, True, "H4610-ORI696 望月奈々.wmv"),
        (False, False, False, "H4610-ORI696 望月奈々.wmv"),
    ],
)
async def test_reorganize_scraped_media_respects_move_and_rename_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    move_enabled: bool,
    rename_enabled: bool,
    expected_folder_changed: bool,
    expected_name: str,
):
    _configure_naming(monkeypatch)
    monkeypatch.setattr(manager.config, "success_file_move", move_enabled)
    monkeypatch.setattr(manager.config, "success_file_rename", rename_enabled)
    output = tmp_path / "JAV_output"
    old_folder = output / "望月奈々" / "H4610-ORI696 望月 奈々 望月奈々"
    old_folder.mkdir(parents=True)
    old_movie = old_folder / "H4610-ORI696 望月奈々.wmv"
    old_nfo = old_folder / "H4610-ORI696 望月奈々.nfo"
    old_movie.write_bytes(b"movie")
    old_nfo.write_text("nfo", encoding="utf-8")

    result = await reorganize_scraped_media(_build_file_info(old_movie), _build_data(), OtherInfo.empty(), output)

    expected_folder = (
        output / "天宮まりる" / "H4610-ORI696 望月 奈々 天宮まりる" if expected_folder_changed else old_folder
    )
    assert result.new_file_path == expected_folder / expected_name
    assert result.new_file_path.read_bytes() == b"movie"
    expected_nfo_name = Path(expected_name).with_suffix(".nfo").name
    assert (expected_folder / expected_nfo_name).read_text(encoding="utf-8") == "nfo"
    assert result.moved is (move_enabled or rename_enabled)


def test_rename_no_replace_windows_does_not_load_posix_libc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from mdcx.core import media_reorganization as module

    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text("content", encoding="utf-8")
    monkeypatch.setattr(module.sys, "platform", "win32")

    def fail_cdll(*_args, **_kwargs):
        raise AssertionError("Windows 分支不应加载 ctypes.CDLL(None)")

    monkeypatch.setattr(module.ctypes, "CDLL", fail_cdll)

    module._rename_no_replace(source, target)

    assert not source.exists()
    assert target.read_text(encoding="utf-8") == "content"
