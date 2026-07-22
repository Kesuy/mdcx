import asyncio
import ctypes
import errno
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ..config.manager import manager
from ..models.types import CrawlersResult, FileInfo, OtherInfo
from .file import get_output_name


class MediaReorganizationError(RuntimeError):
    """按新元数据重组已刮削媒体时发生的可恢复错误。"""

    def __init__(self, message: str, path_mapping: tuple[tuple[Path, Path], ...] = ()):
        super().__init__(message)
        self.path_mapping = path_mapping


@dataclass(frozen=True)
class MediaReorganizationResult:
    old_file_path: Path
    new_file_path: Path
    old_folder: Path
    new_folder: Path
    moved: bool
    path_mapping: tuple[tuple[Path, Path], ...] = ()


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _same_spelling(left: Path, right: Path) -> bool:
    return os.path.abspath(left) == os.path.abspath(right)


def _renamed_companion_name(name: str, old_stem: str, new_stem: str) -> str:
    if not name.startswith(old_stem) or len(name) == len(old_stem):
        return name
    if name[len(old_stem)] not in ".-_ ":
        return name
    return new_stem + name[len(old_stem) :]


def _media_extensions() -> set[str]:
    configured = manager.config.media_type
    if isinstance(configured, str):
        configured = configured.split("|")
    return {extension.lower() if extension.startswith(".") else f".{extension.lower()}" for extension in configured}


def _split_cd_stem(stem: str, cd_part: str) -> tuple[str, str]:
    normalized_cd_part = str(cd_part or "")
    if normalized_cd_part and stem.lower().endswith(normalized_cd_part.lower()):
        return stem[: -len(normalized_cd_part)], stem[-len(normalized_cd_part) :]
    return stem, ""


def _matching_cd_suffix(stem: str, base_stem: str, cd_part: str) -> str | None:
    matched = re.fullmatch(r"(.*?)(\d{1,2})", cd_part)
    if not matched:
        return None
    prefix = matched.group(1)
    sibling = re.fullmatch(rf"{re.escape(base_stem)}({re.escape(prefix)}\d{{1,2}})", stem, flags=re.IGNORECASE)
    return sibling.group(1) if sibling else None


def _assert_single_movie_group(old_file_path: Path, old_folder: Path, cd_part: str) -> list[Path]:
    media_extensions = _media_extensions()
    movies = [
        path
        for path in old_folder.iterdir()
        if path.is_file() and path.suffix.lower() in media_extensions and not path.stem.lower().endswith("-trailer")
    ]
    base_stem, current_suffix = _split_cd_stem(old_file_path.stem, cd_part)
    if not current_suffix:
        grouped = [old_file_path]
    else:
        grouped = [path for path in movies if _matching_cd_suffix(path.stem, base_stem, cd_part) is not None]

    unrelated = [path for path in movies if not any(_same_path(path, grouped_path) for grouped_path in grouped)]
    if unrelated:
        names = "、".join(path.name for path in unrelated)
        raise MediaReorganizationError(f"当前目录包含多个影片文件，不能自动整体迁移：{names}")
    if not any(_same_path(path, old_file_path) for path in grouped):
        raise MediaReorganizationError(f"无法按分集规则识别当前影片：{old_file_path.name}")
    return sorted(grouped, key=lambda path: path.name.lower())


def _assert_target_within_output(target_folder: Path, success_folder: Path) -> None:
    try:
        target_folder.resolve(strict=False).relative_to(success_folder.resolve(strict=False))
    except ValueError as exc:
        raise MediaReorganizationError(f"按当前设置生成的目标目录超出成功输出目录：{target_folder}") from exc


def _assert_source_within_output(old_folder: Path, success_folder: Path) -> None:
    try:
        old_folder.resolve(strict=True).relative_to(success_folder.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise MediaReorganizationError(f"当前影片目录不在成功输出目录内，不能安全地自动整理：{old_folder}") from exc


def _is_directory_link(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def _assert_no_linked_source_directory(old_folder: Path, success_folder: Path) -> None:
    current = old_folder
    while True:
        if _is_directory_link(current):
            raise MediaReorganizationError(f"当前影片路径包含符号链接或 junction，不能安全地自动整理：{current}")
        if _same_path(current, success_folder):
            return
        parent = current.parent
        if _same_path(parent, current):
            raise MediaReorganizationError("当前影片路径与成功输出目录的路径表示不一致，不能安全地自动整理")
        current = parent


def _assert_same_filesystem(old_folder: Path, target_folder: Path) -> None:
    existing_target_parent = target_folder.parent
    while not existing_target_parent.exists() and existing_target_parent != existing_target_parent.parent:
        existing_target_parent = existing_target_parent.parent
    if old_folder.stat().st_dev != existing_target_parent.stat().st_dev:
        raise MediaReorganizationError("源目录和目标目录位于不同磁盘或挂载点，不能安全地自动整理")


def _remove_empty_parents(start: Path, stop: Path) -> None:
    current = start
    stop_resolved = stop.resolve(strict=False)
    while not _same_path(current, stop):
        try:
            current.resolve(strict=False).relative_to(stop_resolved)
            current.rmdir()
        except (OSError, ValueError):
            break
        current = current.parent


def _rename_no_replace(source: Path, target: Path) -> None:
    """同卷原子改名；若目标在任意时刻已存在则绝不覆盖。"""

    if os.path.lexists(target):
        raise FileExistsError(errno.EEXIST, "目标已存在", str(target))

    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        if not hasattr(libc, "renameat2"):
            source.rename(target)
            return
        source_bytes = os.fsencode(source)
        target_bytes = os.fsencode(target)
        at_fdcwd = -100
        rename_noreplace = 1
        result = libc.renameat2(at_fdcwd, source_bytes, at_fdcwd, target_bytes, rename_noreplace)
        if result == 0:
            return
        error_number = ctypes.get_errno()
        if error_number not in (errno.ENOSYS, errno.EINVAL):
            raise OSError(error_number, os.strerror(error_number), str(target))

    if sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        if not hasattr(libc, "renamex_np"):
            source.rename(target)
            return
        source_bytes = os.fsencode(source)
        target_bytes = os.fsencode(target)
        rename_excl = 0x00000004
        result = libc.renamex_np(source_bytes, target_bytes, rename_excl)
        if result == 0:
            return
        error_number = ctypes.get_errno()
        if error_number not in (errno.ENOSYS, errno.EINVAL):
            raise OSError(error_number, os.strerror(error_number), str(target))

    # Windows 的 os.rename 不覆盖现有目标；未知平台保留前置 lexists 防护。
    source.rename(target)


def _rename_case_safe(source: Path, target: Path) -> None:
    if _same_spelling(source, target):
        return
    if os.path.normcase(str(source)) == os.path.normcase(str(target)):
        temporary = source.with_name(f"{source.name}.MDCx.rename.tmp")
        counter = 0
        while temporary.exists():
            counter += 1
            temporary = source.with_name(f"{source.name}.MDCx.rename.{counter}.tmp")
        _rename_no_replace(source, temporary)
        try:
            _rename_no_replace(temporary, target)
        except Exception:
            _rename_no_replace(temporary, source)
            raise
        return
    _rename_no_replace(source, target)


def _try_rollback_rename(source: Path, target: Path, errors: list[str], label: str) -> None:
    if not os.path.lexists(target) or os.path.lexists(source):
        return
    try:
        _rename_case_safe(target, source)
    except Exception as exc:
        errors.append(f"{label}: {exc}")


def _rename_case_only_folder_path(old_folder: Path, new_folder: Path, success_folder: Path) -> list[tuple[Path, Path]]:
    old_relative = old_folder.relative_to(success_folder)
    new_relative = new_folder.relative_to(success_folder)
    if len(old_relative.parts) != len(new_relative.parts):
        raise MediaReorganizationError("仅大小写变化的目标目录层级不一致")

    completed: list[tuple[Path, Path]] = []
    current_parent = success_folder
    try:
        for old_part, new_part in zip(old_relative.parts, new_relative.parts, strict=True):
            source = current_parent / old_part
            target = current_parent / new_part
            if old_part != new_part:
                _rename_case_safe(source, target)
                completed.append((source, target))
            current_parent = target
    except Exception as exc:
        rollback_errors: list[str] = []
        for source, target in reversed(completed):
            _try_rollback_rename(source, target, rollback_errors, f"恢复目录 {source}")
        detail = f"；回滚不完整：{'；'.join(rollback_errors)}" if rollback_errors else ""
        raise MediaReorganizationError(f"仅大小写目录改名失败：{exc}{detail}") from exc
    return completed


def _map_path_after_move(
    path: Path | None,
    *,
    old_folder: Path,
    new_folder: Path,
    old_stem: str,
    new_stem: str,
) -> Path | None:
    if path is None:
        return None
    try:
        relative = path.relative_to(old_folder)
    except ValueError:
        return path
    if len(relative.parts) == 1:
        relative = Path(_renamed_companion_name(relative.name, old_stem, new_stem))
    return new_folder / relative


def _update_runtime_paths(
    file_info: FileInfo,
    other: OtherInfo,
    *,
    old_file_path: Path,
    actual_file_path: Path,
) -> None:
    old_folder = old_file_path.parent
    actual_folder = actual_file_path.parent
    mapped_sub_list = [
        _map_path_after_move(
            Path(path),
            old_folder=old_folder,
            new_folder=actual_folder,
            old_stem=old_file_path.stem,
            new_stem=actual_file_path.stem,
        )
        for path in file_info.sub_list
    ]
    file_info.file_path = actual_file_path
    file_info.folder_path = actual_folder
    file_info.file_name = actual_file_path.stem
    file_info.file_ex = actual_file_path.suffix
    file_info.file_show_name = actual_file_path.name
    file_info.file_show_path = actual_file_path
    file_info.sub_list = [str(path) for path in mapped_sub_list if path is not None]

    other.fanart_path = _map_path_after_move(
        other.fanart_path,
        old_folder=old_folder,
        new_folder=actual_folder,
        old_stem=old_file_path.stem,
        new_stem=actual_file_path.stem,
    )
    other.poster_path = _map_path_after_move(
        other.poster_path,
        old_folder=old_folder,
        new_folder=actual_folder,
        old_stem=old_file_path.stem,
        new_stem=actual_file_path.stem,
    )
    other.thumb_path = _map_path_after_move(
        other.thumb_path,
        old_folder=old_folder,
        new_folder=actual_folder,
        old_stem=old_file_path.stem,
        new_stem=actual_file_path.stem,
    )


def update_runtime_paths_after_reorganization(
    file_info: FileInfo,
    other: OtherInfo,
    old_file_path: Path,
    new_file_path: Path,
) -> None:
    """将同一多 CD 组中其他结果项的内存路径同步到整理后位置。"""

    _update_runtime_paths(
        file_info,
        other,
        old_file_path=old_file_path,
        actual_file_path=new_file_path,
    )


def _reorganize_scraped_media_sync(
    file_info: FileInfo,
    data: CrawlersResult,
    other: OtherInfo,
    success_folder: Path,
) -> MediaReorganizationResult:
    old_file_path = file_info.file_path
    old_folder = old_file_path.parent
    if not old_file_path.is_file():
        raise MediaReorganizationError(f"影片文件不存在：{old_file_path}")

    (
        new_folder,
        new_file_path,
        _nfo_path,
        _poster_with_filename,
        _thumb_with_filename,
        _fanart_with_filename,
        _naming_rule,
        _poster_final_path,
        _thumb_final_path,
        _fanart_final_path,
    ) = get_output_name(file_info, data, success_folder, old_file_path.suffix)

    if not manager.config.success_file_move:
        new_folder = old_folder
    if manager.config.success_file_rename:
        new_file_path = new_folder / new_file_path.name
    else:
        new_file_path = new_folder / old_file_path.name

    folder_relocates = not _same_path(old_folder, new_folder)
    if folder_relocates and os.path.lexists(new_folder):
        raise MediaReorganizationError(f"目标目录已存在，为避免覆盖已停止自动整理：{new_folder}")
    _assert_target_within_output(new_folder, success_folder)
    _assert_source_within_output(old_folder, success_folder)
    _assert_no_linked_source_directory(old_folder, success_folder)
    old_stem = old_file_path.stem
    new_stem = new_file_path.stem
    old_base_stem, old_cd_suffix = _split_cd_stem(old_stem, file_info.cd_part)
    new_base_stem, new_cd_suffix = _split_cd_stem(new_stem, file_info.cd_part)
    rename_old_stem = old_base_stem if old_cd_suffix and new_cd_suffix else old_stem
    rename_new_stem = new_base_stem if old_cd_suffix and new_cd_suffix else new_stem
    folder_case_changes = not folder_relocates and not _same_spelling(old_folder, new_folder)
    folder_changes = folder_relocates or folder_case_changes
    file_changes = old_file_path.name != new_file_path.name
    if not folder_changes and not file_changes:
        return MediaReorganizationResult(old_file_path, old_file_path, old_folder, old_folder, False)

    movie_group = _assert_single_movie_group(old_file_path, old_folder, file_info.cd_part)
    if folder_changes and _same_path(old_folder, success_folder):
        raise MediaReorganizationError("当前影片位于成功输出根目录，不能安全地整体迁移该目录")
    if folder_relocates:
        _assert_same_filesystem(old_folder, new_folder)

    rename_pairs: list[tuple[Path, Path]] = []
    paths = sorted(old_folder.iterdir(), key=lambda path: (not _same_path(path, old_file_path), path.name.lower()))
    for path in paths:
        if not path.is_file():
            continue
        new_name = _renamed_companion_name(path.name, rename_old_stem, rename_new_stem)
        if new_name == path.name:
            continue
        target = path.with_name(new_name)
        if os.path.lexists(target) and not _same_path(path, target):
            raise MediaReorganizationError(f"目标文件已存在，为避免覆盖已停止自动整理：{target}")
        rename_pairs.append((path, target))

    if folder_relocates:
        new_folder.parent.mkdir(parents=True, exist_ok=True)
    folder_moved = False
    case_folder_renames: list[tuple[Path, Path]] = []
    completed_renames: list[tuple[Path, Path]] = []
    try:
        if folder_relocates:
            _rename_case_safe(old_folder, new_folder)
            folder_moved = True
        elif folder_case_changes:
            case_folder_renames = _rename_case_only_folder_path(old_folder, new_folder, success_folder)

        active_folder = new_folder if folder_changes else old_folder
        for old_path, target_path in rename_pairs:
            source = active_folder / old_path.name
            target = active_folder / target_path.name
            _rename_case_safe(source, target)
            completed_renames.append((source, target))
    except Exception as exc:
        rollback_errors: list[str] = []
        for source, target in reversed(completed_renames):
            _try_rollback_rename(source, target, rollback_errors, f"恢复文件 {source}")
        if case_folder_renames:
            for source, target in reversed(case_folder_renames):
                _try_rollback_rename(source, target, rollback_errors, f"恢复目录 {source}")
        elif folder_moved and new_folder.exists() and not old_folder.exists():
            try:
                old_folder.parent.mkdir(parents=True, exist_ok=True)
                _rename_case_safe(new_folder, old_folder)
            except Exception as rollback_exc:
                rollback_errors.append(f"恢复影片目录 {old_folder}: {rollback_exc}")
        _remove_empty_parents(new_folder.parent, success_folder)
        actual_mapping: list[tuple[Path, Path]] = []
        for movie_path in movie_group:
            renamed_name = _renamed_companion_name(movie_path.name, rename_old_stem, rename_new_stem)
            candidates = (
                movie_path,
                old_folder / renamed_name,
                new_folder / movie_path.name,
                new_folder / renamed_name,
            )
            actual_path = next((path for path in candidates if path.is_file()), None)
            if actual_path is not None and not _same_path(actual_path, movie_path):
                actual_mapping.append((movie_path, actual_path))
        actual_file_path = dict(actual_mapping).get(old_file_path)
        if actual_file_path is not None and not _same_path(actual_file_path, old_file_path):
            _update_runtime_paths(
                file_info,
                other,
                old_file_path=old_file_path,
                actual_file_path=actual_file_path,
            )
            rollback_errors.append(f"影片当前位于 {actual_file_path}")
        detail = f"；回滚不完整：{'；'.join(rollback_errors)}" if rollback_errors else ""
        raise MediaReorganizationError(
            f"自动整理失败，已尝试回滚：{exc}{detail}",
            tuple(actual_mapping),
        ) from exc

    _update_runtime_paths(file_info, other, old_file_path=old_file_path, actual_file_path=new_file_path)

    if folder_changes:
        _remove_empty_parents(old_folder.parent, success_folder)

    path_mapping = tuple(
        (
            path,
            new_folder / _renamed_companion_name(path.name, rename_old_stem, rename_new_stem),
        )
        for path in movie_group
    )
    return MediaReorganizationResult(old_file_path, new_file_path, old_folder, new_folder, True, path_mapping)


async def reorganize_scraped_media(
    file_info: FileInfo,
    data: CrawlersResult,
    other: OtherInfo,
    success_folder: Path,
) -> MediaReorganizationResult:
    """按当前命名设置迁移一个已刮削的单影片目录，并同步其内存路径。"""

    try:
        return await asyncio.to_thread(_reorganize_scraped_media_sync, file_info, data, other, success_folder)
    except MediaReorganizationError:
        raise
    except Exception as exc:
        raise MediaReorganizationError(f"自动整理失败：{exc}") from exc
