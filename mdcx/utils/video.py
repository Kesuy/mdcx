import json
import os
import re
import shutil
import subprocess
from pathlib import Path

try:
    import av
except ImportError:
    av = None


def _is_runnable(executable: str, version_flag: str = "-version") -> bool:
    try:
        subprocess.run(
            [executable, version_flag],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def find_ffmpeg_executable() -> str | None:
    """Find a working FFmpeg configured by the user or available on PATH."""
    candidates = [os.environ.get("MDCX_FFMPEG"), shutil.which("ffmpeg")]
    return next((str(item) for item in candidates if item and _is_runnable(str(item))), None)


def find_ffprobe_executable() -> str | None:
    candidates = [os.environ.get("MDCX_FFPROBE"), shutil.which("ffprobe")]
    return next((str(item) for item in candidates if item and _is_runnable(str(item))), None)


def get_video_metadata_pyav(p: Path) -> tuple[int, str]:
    if av is None:
        raise ImportError("Should not be called if pyav is not available")
    height = 0
    codec_fourcc = ""
    with av.open(p) as container:
        # 查找第一个视频流
        video_stream = next((s for s in container.streams.video), None)
        if video_stream:
            height = video_stream.height
            codec_fourcc = video_stream.codec_context.name.upper()
    return height, codec_fourcc


def get_video_metadata_ffmpeg(p: Path) -> tuple[int, str]:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
    ffprobe = find_ffprobe_executable()
    if ffprobe is not None:
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", str(p)]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags, check=True)
        data = json.loads(result.stdout)
        video_stream = next((stream for stream in data["streams"] if stream["codec_type"] == "video"), None)
        if video_stream:
            return int(video_stream["height"]), video_stream["codec_name"].upper()
        return 0, ""

    ffmpeg = find_ffmpeg_executable()
    if ffmpeg is None:
        raise RuntimeError("未找到可执行的 ffprobe 或 ffmpeg，无法读取视频分辨率。")
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(p)],
        capture_output=True,
        text=True,
        creationflags=creationflags,
        check=False,
    )
    video_line = next((line for line in result.stderr.splitlines() if "Video:" in line), "")
    matched = re.search(r"Video:\s*([^,\s]+).*?(\d{2,5})x(\d{2,5})(?:[,\s])", video_line)
    if matched is None:
        return 0, ""
    codec = matched.group(1).upper()
    if codec == "HEVC":
        codec = "HEVC"
    return int(matched.group(3)), codec


if av is not None:
    VIDEO_BACKEND = "pyav"
    get_video_metadata = get_video_metadata_pyav
else:
    VIDEO_BACKEND = "ffmpeg"
    get_video_metadata = get_video_metadata_ffmpeg
