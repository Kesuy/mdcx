import hashlib
from dataclasses import dataclass
from pathlib import Path

from mdcx.config.manager import manager
from mdcx.core.file import get_file_info_v2
from mdcx.core.nfo import get_nfo_data
from mdcx.models.types import FileInfo, ShowData


class LocalNfoLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalNfoLoadResult:
    primary: ShowData
    entries: tuple[ShowData, ...]


def _media_files(folder: Path) -> list[Path]:
    extensions = {
        extension.lower() if str(extension).startswith(".") else f".{str(extension).lower()}"
        for extension in manager.config.media_type
    }
    return sorted(
        (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in extensions),
        key=lambda path: path.name.casefold(),
    )


def _same_number(left: str, right: str) -> bool:
    return bool(left and right and left.strip().casefold() == right.strip().casefold())


def _cd_base_stem(path: Path, file_info: FileInfo) -> str:
    cd_part = str(file_info.cd_part or "")
    if cd_part and path.stem.casefold().endswith(cd_part.casefold()):
        return path.stem[: -len(cd_part)]
    return path.stem


def _local_show_name(file_info: FileInfo) -> str:
    identity = str(file_info.file_path.resolve(strict=False)).casefold().encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:8]
    return f"本地.{file_info.file_show_name} [{digest}]"


async def _select_media(nfo_path: Path, candidates: list[tuple[Path, FileInfo]]) -> tuple[Path, FileInfo]:
    exact = [entry for entry in candidates if entry[0].stem.casefold() == nfo_path.stem.casefold()]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]

    provisional_path, provisional_info = candidates[0]
    data, _other = await get_nfo_data(provisional_path, provisional_info.number, nfo_path)
    if data is not None:
        matching = [entry for entry in candidates if _same_number(entry[1].number, data.number)]
        if len(matching) == 1:
            return matching[0]
        if matching and all(entry[1].cd_part for entry in matching):
            groups: dict[str, list[tuple[Path, FileInfo]]] = {}
            for entry in matching:
                groups.setdefault(_cd_base_stem(*entry).casefold(), []).append(entry)
            matching_base = nfo_path.stem.casefold()
            if matching_base in groups:
                return groups[matching_base][0]
            if len(groups) == 1:
                return next(iter(groups.values()))[0]

    raise LocalNfoLoadError("当前目录有多个视频，无法确定所选 NFO 对应的视频文件")


async def load_local_nfo(nfo_path: Path) -> LocalNfoLoadResult:
    nfo_path = Path(nfo_path)
    if not nfo_path.is_file() or nfo_path.suffix.lower() != ".nfo":
        raise LocalNfoLoadError(f"NFO 文件不存在或格式不正确：{nfo_path}")

    media_paths = _media_files(nfo_path.parent)
    if not media_paths:
        raise LocalNfoLoadError("所选 NFO 目录中没有找到受支持的视频文件")

    candidates = [(path, await get_file_info_v2(path, copy_sub=False)) for path in media_paths]
    primary_path, primary_info = await _select_media(nfo_path, candidates)

    if primary_info.cd_part:
        primary_base = _cd_base_stem(primary_path, primary_info).casefold()
        related = [
            entry
            for entry in candidates
            if entry[1].cd_part
            and _same_number(entry[1].number, primary_info.number)
            and _cd_base_stem(*entry).casefold() == primary_base
        ]
    else:
        related = [(primary_path, primary_info)]

    loaded_entries: list[ShowData] = []
    primary: ShowData | None = None
    for media_path, file_info in related:
        own_nfo_path = media_path.with_suffix(".nfo")
        source_nfo_path = own_nfo_path if own_nfo_path.is_file() else nfo_path
        data, other = await get_nfo_data(media_path, file_info.number, source_nfo_path)
        if data is None or other is None:
            if media_path == primary_path:
                raise LocalNfoLoadError(f"NFO 文件无法解析或缺少标题：{source_nfo_path}")
            continue
        show_name = _local_show_name(file_info)
        show_data = ShowData(file_info=file_info, data=data, other=other, show_name=show_name)
        loaded_entries.append(show_data)
        if media_path == primary_path:
            primary = show_data

    if primary is None:
        raise LocalNfoLoadError(f"无法加载所选 NFO：{nfo_path}")
    return LocalNfoLoadResult(primary=primary, entries=tuple(loaded_entries))
