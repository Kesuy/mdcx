"""
刮削过程所需图片操作
"""

import asyncio
import os
import time
import traceback
from pathlib import Path
from typing import cast

from PIL import Image

from ..base.image import add_mark_thread
from ..config.enums import DownloadableFile, FixedScrapingType, MarkType
from ..config.manager import manager
from ..models.log_buffer import LogBuffer
from ..models.types import CrawlersResult, FileInfo, OtherInfo
from ..signals import signal
from ..utils import executor, get_used_time
from ..utils.file import check_pic_async, copy_file_sync, delete_file_sync
from .mosaic import has_leak_mark, has_umr_mark, has_uncensored_mark, is_censored_mosaic

YOUMA_RIGHT_CROP_TYPES = {FixedScrapingType.YOUMA}
FACE_FALLBACK_CROP_TYPES = {
    FixedScrapingType.WUMA,
    FixedScrapingType.FC2,
    FixedScrapingType.OUMEI,
    FixedScrapingType.GUOCHAN,
    FixedScrapingType.SUREN,
    FixedScrapingType.AUTO,
}
LOCAL_NUMBER_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_face_crop_left(image: Image.Image, crop_width: int, log_fn=None) -> int | None:
    """延迟加载人脸检测后端，同时保留原有可替换的模块级接口。"""
    from .face_crop import get_face_crop_left as detect_face_crop_left

    return detect_face_crop_left(image, crop_width, log_fn=log_fn)


def _save_local_image_as_jpeg(source_path: Path, target_path: Path) -> tuple[bool, str]:
    temp_path = target_path.with_name(f"{target_path.name}.[LOCAL].jpg")
    try:
        with Image.open(source_path) as image:
            image.convert("RGB").save(temp_path, format="JPEG", quality=95, subsampling=0)
        os.replace(temp_path, target_path)
        return True, ""
    except Exception as exc:
        delete_file_sync(temp_path)
        return False, str(exc)


async def prepare_local_number_images(
    result: CrawlersResult,
    other: OtherInfo,
    folder_old_path: Path,
    folder_new_path: Path,
    poster_final_path: Path,
    thumb_final_path: Path,
    fanart_final_path: Path,
    *,
    copy_poster: bool,
) -> tuple[bool, bool]:
    """识别同番号原图，并严格用文件名排序后的第一张生成刮削图片。"""
    if not manager.config.use_local_number_images or manager.config.soft_link != 0:
        return False, True

    try:
        names = await asyncio.to_thread(os.listdir, folder_old_path)
    except OSError:
        return False, True

    final_paths = {poster_final_path, thumb_final_path, fanart_final_path}
    matched = sorted(
        (
            folder_old_path / name
            for name in names
            if result.number.casefold() in name.casefold()
            and Path(name).suffix.lower() in LOCAL_NUMBER_IMAGE_EXTENSIONS
            and folder_old_path / name not in final_paths
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )
    if not matched:
        return False, True

    # 原图由刮削成功路径中的 move_other_file() 统一移动，避免后续步骤失败时提前移走用户文件。
    source_image = matched[0]
    if not await check_pic_async(source_image):
        LogBuffer.log().write(f"\n 🔴 排序第一张同番号图片无法读取: {source_image.name}")
        return True, False

    download_files = manager.config.download_files
    if DownloadableFile.THUMB in download_files:
        copied, error = await asyncio.to_thread(_save_local_image_as_jpeg, source_image, thumb_final_path)
        if not copied:
            LogBuffer.log().write(f"\n 🔴 同番号图片生成 Thumb 失败: {error}")
            return True, False
        other.thumb_path = thumb_final_path
        other.thumb_marked = False

    if DownloadableFile.FANART in download_files:
        copied, error = await asyncio.to_thread(_save_local_image_as_jpeg, source_image, fanart_final_path)
        if not copied:
            LogBuffer.log().write(f"\n 🔴 同番号图片生成 Fanart 失败: {error}")
            return True, False
        other.fanart_path = fanart_final_path
        other.fanart_marked = False

    if DownloadableFile.POSTER in download_files:
        if copy_poster:
            poster_created, error = await asyncio.to_thread(_save_local_image_as_jpeg, source_image, poster_final_path)
            if not poster_created:
                LogBuffer.log().write(f"\n 🔴 同番号图片生成 Poster 失败: {error}")
        else:
            poster_created = await asyncio.to_thread(
                cut_thumb_to_poster,
                result,
                source_image,
                poster_final_path,
                result.scraping_type,
            )
        if not poster_created:
            return True, False
        other.poster_path = poster_final_path
        other.poster_marked = False

    LogBuffer.log().write(f"\n 🍀 已优先使用同番号本地图片: {source_image.name}")
    return True, True


async def add_mark(json_data: OtherInfo, file_info: FileInfo, mosaic: str):
    poster_marked = json_data.poster_marked
    thumb_marked = json_data.thumb_marked
    fanart_marked = json_data.fanart_marked
    download_files = manager.config.download_files
    mark_type = manager.config.mark_type
    has_sub = file_info.has_sub
    definition = file_info.definition
    mark_list = []
    if ("K" in definition or "UHD" in definition) and MarkType.HD in mark_type:
        if "8" in definition:
            mark_list.append("8K")
        else:
            mark_list.append("4K")
    if has_sub and MarkType.SUB in mark_type:
        mark_list.append("字幕")

    if is_censored_mosaic(mosaic):
        if MarkType.YOUMA in mark_type:
            mark_list.append("有码")
    elif has_umr_mark(mosaic):
        if MarkType.UMR in mark_type:
            mark_list.append("破解")
        elif MarkType.UNCENSORED in mark_type:
            mark_list.append("无码")
    elif has_leak_mark(mosaic):
        if MarkType.LEAK in mark_type:
            mark_list.append("流出")
        elif has_uncensored_mark(mosaic) and MarkType.UNCENSORED in mark_type:
            mark_list.append("无码")
    elif has_uncensored_mark(mosaic) and MarkType.UNCENSORED in mark_type:
        mark_list.append("无码")

    if mark_list:
        download_files = manager.config.download_files
        mark_show_type = ",".join(mark_list)
        poster_path = json_data.poster_path
        thumb_path = json_data.thumb_path
        fanart_path = json_data.fanart_path

        if (
            manager.config.thumb_mark == 1
            and DownloadableFile.THUMB in download_files
            and thumb_path
            and not thumb_marked
        ):
            await add_mark_thread(thumb_path, mark_list)
            LogBuffer.log().write(f"\n 🍀 Thumb add watermark: {mark_show_type}!")
        if (
            manager.config.poster_mark == 1
            and DownloadableFile.POSTER in download_files
            and poster_path
            and not poster_marked
        ):
            await add_mark_thread(poster_path, mark_list)
            LogBuffer.log().write(f"\n 🍀 Poster add watermark: {mark_show_type}!")
        if (
            manager.config.fanart_mark == 1
            and DownloadableFile.FANART in download_files
            and fanart_path
            and not fanart_marked
        ):
            await add_mark_thread(fanart_path, mark_list)
            LogBuffer.log().write(f"\n 🍀 Fanart add watermark: {mark_show_type}!")


def _right_crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    ax, ay, bx, by = width / 1.9, 0, width, height
    if width == 800:
        if height == 439:
            ax, ay, bx, by = 420, 0, width, height
        elif 499 <= height <= 503:
            ax, ay, bx, by = 437, 0, width, height
        else:
            ax, ay, bx, by = 421, 0, width, height
    elif width == 840 and height == 472:
        ax, ay, bx, by = 473, 0, 788, height
    return int(ax), int(ay), int(bx), int(by)


def _center_crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    crop_width = int(height / 1.5)
    ax = max(int((width - crop_width) / 2), 0)
    ay = 0
    bx = min(ax + crop_width, width)
    by = height
    return ax, ay, bx, by


def cut_thumb_to_poster(
    json_data: CrawlersResult,
    thumb_path: Path,
    poster_path: Path,
    scraping_type: FixedScrapingType,
    log_fn=None,
):
    start_time = time.time()
    log = log_fn or LogBuffer.log().write
    if os.path.exists(poster_path):
        delete_file_sync(poster_path)

    img = None
    img_new = None
    img_new_png = None
    # 打开图片, 获取图片尺寸
    try:
        img = Image.open(thumb_path)  # 返回一个Image对象
        img = cast("Image.Image", img)

        w, h = img.size
        prop = h / w
        log(f"\n 🖼 Poster裁剪: 开始处理({scraping_type.value})，源图={w}x{h}")

        # 优先按图片比例决定基础裁剪方式，保持旧版自动裁剪行为。
        if prop >= 1.4:
            copy_file_sync(thumb_path, poster_path)
            log(f"\n 🍀 Poster done! (copy thumb)({get_used_time(start_time)}s)")
            json_data.poster_from = "copy thumb"
            img.close()
            return True
        if prop >= 1:
            json_data.poster_from = "thumb center"
            ax, ay, bx, by = _center_crop_box(w, h)
            log("\n 🖼 Poster裁剪: 图片接近竖图，使用居中裁剪")

        # 横图有码作品固定走右裁剪；其余已枚举类型优先做人脸识别，失败后回退居中裁剪。
        elif scraping_type in YOUMA_RIGHT_CROP_TYPES:
            json_data.poster_from = "thumb right"
            ax, ay, bx, by = _right_crop_box(w, h)
            log("\n 🖼 Poster裁剪: 命中有码右裁策略")
        elif scraping_type in FACE_FALLBACK_CROP_TYPES:
            crop_width = int(h / 1.5)
            face_left = get_face_crop_left(img, crop_width, log_fn=log)
            if face_left is None:
                json_data.poster_from = "thumb center"
                ax, ay, bx, by = _center_crop_box(w, h)
            else:
                json_data.poster_from = "thumb face"
                ax, ay, bx, by = face_left, 0, face_left + crop_width, h
                if bx > w:
                    bx = w
                    ax = max(bx - crop_width, 0)
        else:
            json_data.poster_from = "thumb center"
            ax, ay, bx, by = _center_crop_box(w, h)
            log("\n 🖼 Poster裁剪: 未配置专用策略，默认居中裁剪")

        # 裁剪并保存
        img_new = img.convert("RGB")
        img_new = cast("Image.Image", img_new)
        img_new_png = img_new.crop((ax, ay, bx, by))
        img_new_png.save(poster_path, quality=95, subsampling=0)
        if executor.run(check_pic_async(poster_path)):
            log(f"\n 🍀 Poster done! ({json_data.poster_from})({get_used_time(start_time)}s)")
            return True
        log(f"\n 🥺 Poster cut failed! ({json_data.poster_from})({get_used_time(start_time)}s)")
    except Exception as e:
        log(f"\n 🥺 Poster failed! ({json_data.poster_from})({get_used_time(start_time)}s)\n    {str(e)}")
        signal.show_traceback_log(traceback.format_exc())
        signal.show_log_text(f"{traceback.format_exc()}\n Pic: {thumb_path}")
        return False
    finally:
        if img_new_png:
            img_new_png.close()
        if img_new:
            img_new.close()
        if img:
            img.close()
    return False
