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
    text = str(message or "未知错误").strip()
    normalized = f"{stage} {text}".casefold()

    if isinstance(exception, (AssertionError, AttributeError, KeyError, NameError, TypeError)):
        category = FailureCategory.INTERNAL_ERROR
        retryable = False
    elif any(
        token in normalized for token in ("cookie", "token", "unauthorized", "forbidden", "登录", "认证", "验证码")
    ):
        category = FailureCategory.AUTHENTICATION
        retryable = False
    elif any(token in normalized for token in ("no result", "not found", "未找到", "无结果", "没有结果")):
        category = FailureCategory.SEARCH_NO_RESULT
        retryable = True
    elif any(token in normalized for token in ("timeout", "timed out", "connection", "dns", "proxy", "http ", "网络")):
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
