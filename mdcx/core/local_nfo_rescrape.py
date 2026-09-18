from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Any

from ..base.file import save_success_list
from ..models.enums import FileMode
from ..models.flags import Flags
from ..models.log_buffer import LogBuffer
from ..signals import signal
from . import scraper as scraper_module
from .file import get_output_name as build_output_name
from .media_reorganization import MediaReorganizationError, reorganize_scraped_media

_INPLACE_ACTIVE: ContextVar[bool] = ContextVar("local_nfo_inplace_rescrape", default=False)
_INSTALLED = False
_ORIGINAL_PROCESS_ONE_FILE: Any = None
_ORIGINAL_RUN: Any = None
_ORIGINAL_CREATE_LINK: Any = None


def _rebase_generated_name(path: Path, generated_stem: str, source_stem: str, source_folder: Path) -> Path:
    name = path.name
    if generated_stem and name.startswith(generated_stem):
        name = source_stem + name[len(generated_stem) :]
    return source_folder / name


def get_inplace_rescrape_output_name(
    file_info,
    data,
    success_folder: Path,
    file_ex: str,
) -> tuple[Path, Path, Path, Path, Path, Path, str, Path, Path, Path]:
    """Keep a local-NFO rescrape in its current folder until final reorganization.

    The scrape refreshes NFO/images using the existing basename first.  Once the
    scrape succeeds, ``reorganize_scraped_media`` applies the same safe folder and
    companion-file rename logic used by the v4.0.25 NFO editor workflow.
    """

    generated = build_output_name(file_info, data, success_folder, file_ex)
    source_file = Path(file_info.file_path)
    source_folder = Path(file_info.folder_path or source_file.parent)
    source_stem = source_file.stem
    generated_stem = generated[1].stem

    nfo_path = _rebase_generated_name(generated[2], generated_stem, source_stem, source_folder)
    poster_with_name = _rebase_generated_name(generated[3], generated_stem, source_stem, source_folder)
    thumb_with_name = _rebase_generated_name(generated[4], generated_stem, source_stem, source_folder)
    fanart_with_name = _rebase_generated_name(generated[5], generated_stem, source_stem, source_folder)
    poster_final = _rebase_generated_name(generated[7], generated_stem, source_stem, source_folder)
    thumb_final = _rebase_generated_name(generated[8], generated_stem, source_stem, source_folder)
    fanart_final = _rebase_generated_name(generated[9], generated_stem, source_stem, source_folder)

    return (
        source_folder,
        source_file,
        nfo_path,
        poster_with_name,
        thumb_with_name,
        fanart_with_name,
        source_stem,
        poster_final,
        thumb_final,
        fanart_final,
    )


async def reorganize_local_nfo_rescrape(file_info, data, other):
    """Rename only the current movie folder and same-prefix files in its parent.

    A synthetic success root deliberately makes the existing v4.0.25 organizer
    treat the source as outside the configured success output.  That selects its
    established "keep the parent, rename only this movie folder" branch without
    creating or migrating into the real success directory.
    """

    old_file_path = Path(file_info.file_path)
    old_folder = old_file_path.parent
    synthetic_success_root = old_folder.parent / ".mdcx-inplace-output-root"
    reorganized = await reorganize_scraped_media(file_info, data, other, synthetic_success_root)

    if not reorganized.moved:
        return reorganized

    path_mapping = dict(reorganized.path_mapping) or {old_file_path: reorganized.new_file_path}
    for source_path, target_path in path_mapping.items():
        original_sources = Flags.file_new_path_dic.pop(source_path, None)
        if original_sources is not None:
            Flags.file_new_path_dic[target_path] = original_sources
        if source_path in Flags.success_list:
            Flags.success_list.discard(source_path)
            Flags.success_list.add(target_path)

    await save_success_list()
    signal.show_log_text(
        f"\n 🍀 本地 NFO 原地整理完成\n    原路径: {old_file_path}\n    新路径: {reorganized.new_file_path}"
    )
    return reorganized


def install_local_nfo_rescrape_hooks() -> None:
    """Install narrowly-scoped hooks for local-NFO rescrape tasks.

    Normal scraping and result-list rescraping keep the original code path.  The
    hook is activated only for paths explicitly marked by the local-NFO UI.
    """

    global _INSTALLED, _ORIGINAL_PROCESS_ONE_FILE, _ORIGINAL_RUN, _ORIGINAL_CREATE_LINK
    if _INSTALLED:
        return

    _INSTALLED = True
    scraper_class = scraper_module.Scraper
    _ORIGINAL_PROCESS_ONE_FILE = scraper_class._process_one_file
    _ORIGINAL_RUN = scraper_class._run
    _ORIGINAL_CREATE_LINK = scraper_module.newtdisk_creat_symlink
    original_output_name = scraper_module.get_output_name

    def output_name_wrapper(file_info, data, success_folder: Path, file_ex: str):
        if _INPLACE_ACTIVE.get():
            return get_inplace_rescrape_output_name(file_info, data, success_folder, file_ex)
        return original_output_name(file_info, data, success_folder, file_ex)

    async def create_link_wrapper(*args, **kwargs):
        if _INPLACE_ACTIVE.get():
            LogBuffer.log().write("\n 🍀 本地 NFO 原地整理：跳过成功目录软链接步骤")
            return None
        return await _ORIGINAL_CREATE_LINK(*args, **kwargs)

    async def process_one_file_wrapper(self, file_info, file_mode):
        source_path = Path(file_info.file_path)
        marked = file_mode == FileMode.Again and source_path in Flags.new_again_inplace_paths
        if not marked:
            return await _ORIGINAL_PROCESS_ONE_FILE(self, file_info, file_mode)

        token = _INPLACE_ACTIVE.set(True)
        try:
            result = await _ORIGINAL_PROCESS_ONE_FILE(self, file_info, file_mode)
        finally:
            _INPLACE_ACTIVE.reset(token)

        data, other = result
        if data is None or other is None:
            return result

        try:
            await reorganize_local_nfo_rescrape(file_info, data, other)
        except MediaReorganizationError as error:
            signal.show_log_text(f"\n 🟡 本地 NFO 已重新刮削，但原地整理失败：{error}")
            LogBuffer.log().write(f"\n 🟡 Local NFO in-place reorganization failed: {error}")
        return result

    async def run_wrapper(self, file_mode, movie_list):
        active_paths: set[Path] = set()
        if file_mode == FileMode.Again and movie_list:
            requested = {Path(path) for path in movie_list}
            active_paths = requested & set(Flags.again_inplace_paths)
            if active_paths:
                Flags.again_inplace_paths.difference_update(active_paths)
                Flags.new_again_inplace_paths.update(active_paths)
        try:
            return await _ORIGINAL_RUN(self, file_mode, movie_list)
        finally:
            if active_paths:
                Flags.new_again_inplace_paths.difference_update(active_paths)

    scraper_module.get_output_name = output_name_wrapper
    scraper_module.newtdisk_creat_symlink = create_link_wrapper
    scraper_class._process_one_file = process_one_file_wrapper
    scraper_class._run = run_wrapper
