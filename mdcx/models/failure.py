from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class FailureCategory(StrEnum):
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    SEARCH_NO_RESULT = "search_no_result"
    PARSER = "parser"
    METADATA = "metadata"
    IMAGE_DOWNLOAD = "image_download"
    FILE_IO = "file_io"
    RENAME_MOVE = "rename_move"
    INTERNAL_ERROR = "internal_error"

    @property
    def label(self) -> str:
        return _CATEGORY_TEXT[self][0]

    @property
    def description(self) -> str:
        return _CATEGORY_TEXT[self][1]


_CATEGORY_TEXT: dict[FailureCategory, tuple[str, str]] = {
    FailureCategory.NETWORK: ("网络连接", "网络请求、DNS 或代理异常；网络恢复后通常可以直接重试。"),
    FailureCategory.AUTHENTICATION: ("登录认证", "站点认证信息可能失效，请检查 Cookie、Token 或登录状态后再试。"),
    FailureCategory.SEARCH_NO_RESULT: ("未找到结果", "当前数据源没有匹配结果，可确认番号或尝试其他数据源。"),
    FailureCategory.PARSER: ("页面解析", "站点返回结构可能已变化，通常需要更新解析规则后再试。"),
    FailureCategory.METADATA: ("元数据", "返回数据缺少必要字段或格式异常，请检查数据源返回内容。"),
    FailureCategory.IMAGE_DOWNLOAD: ("图片下载", "封面或图片获取失败；网络或图片源恢复后通常可以重试。"),
    FailureCategory.FILE_IO: ("文件读写", "本地文件操作失败，请检查权限、文件占用和磁盘状态。"),
    FailureCategory.RENAME_MOVE: ("文件整理", "重命名或移动失败，请检查目标冲突、跨盘、链接或文件占用。"),
    FailureCategory.INTERNAL_ERROR: ("程序异常", "程序内部出现未预期错误，可展开调试信息并附日志反馈。"),
}

_STAGE_LABELS = {
    "scrape": "刮削",
    "crawl": "抓取",
    "search": "搜索",
    "image": "图片处理",
    "file": "文件处理",
    "move": "文件整理",
    "metadata": "元数据处理",
}


def failure_stage_label(stage: str) -> str:
    normalized = str(stage or "").strip()
    return _STAGE_LABELS.get(normalized.casefold(), normalized or "未知阶段")


@dataclass(frozen=True)
class FailureRecord:
    path: Path
    stage: str
    category: FailureCategory
    message: str
    retryable: bool
    site: str = ""
    debug_detail: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = field(default_factory=dict)

    def legacy_tuple(self) -> tuple[Path, str]:
        """Compatibility representation used by the old failed-list surface."""
        return self.path, self.message


def classify_failure(
    path: Path,
    message: str,
    *,
    stage: str = "scrape",
    site: str = "",
    debug_detail: str = "",
    context: dict[str, Any] | None = None,
    exception: BaseException | None = None,
) -> FailureRecord:
    """Convert the existing failure text into a small user-facing category.

    MDCx still has legacy paths that report plain text errors, so classification is
    intentionally conservative. Business code should pass explicit context when it
    already knows it rather than adding more keyword rules here.
    """

    text = str(message or "未知错误").strip()
    normalized = f"{stage} {text}".casefold()

    if isinstance(exception, (AssertionError, AttributeError, KeyError, NameError, TypeError)):
        category = FailureCategory.INTERNAL_ERROR
        retryable = False
    elif any(
        token in normalized
        for token in (
            "cookie",
            "token",
            "unauthorized",
            "forbidden",
            "http 401",
            "http 403",
            "status 401",
            "status 403",
            "登录",
            "认证",
            "验证码",
        )
    ):
        category = FailureCategory.AUTHENTICATION
        retryable = False
    elif any(token in normalized for token in ("no result", "not found", "未找到", "无结果", "没有结果")):
        category = FailureCategory.SEARCH_NO_RESULT
        retryable = True
    elif any(
        token in normalized
        for token in (
            "timeout",
            "timed out",
            "connection",
            "dns",
            "proxy",
            "http 429",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
            "网络",
        )
    ):
        category = FailureCategory.NETWORK
        retryable = True
    elif any(token in normalized for token in ("poster", "fanart", "thumb", "image", "图片", "海报")):
        category = FailureCategory.IMAGE_DOWNLOAD
        retryable = True
    elif any(token in normalized for token in ("target conflict", "目标冲突", "already exists", "已存在")):
        category = FailureCategory.RENAME_MOVE
        retryable = False
    elif any(token in normalized for token in ("rename", "move", "重命名", "移动")):
        category = FailureCategory.RENAME_MOVE
        retryable = True
    elif any(
        token in normalized for token in ("permission", "winerror 5", "locked", "in use", "文件", "目录", "ioerror")
    ):
        category = FailureCategory.FILE_IO
        retryable = True
    elif any(token in normalized for token in ("parse", "parser", "selector", "解析")):
        category = FailureCategory.PARSER
        retryable = False
    elif any(token in normalized for token in ("metadata", "nfo", "字段", "元数据")):
        category = FailureCategory.METADATA
        retryable = False
    else:
        category = FailureCategory.INTERNAL_ERROR
        retryable = False

    return FailureRecord(
        path=Path(path),
        stage=stage,
        category=category,
        message=text,
        retryable=retryable,
        site=site,
        debug_detail=debug_detail,
        context=dict(context or {}),
    )
