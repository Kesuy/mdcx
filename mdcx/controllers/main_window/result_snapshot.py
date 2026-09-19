from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from mdcx.config.enums import FixedScrapingType, Website
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.types import CrawlersResult, FieldProvenance, FileInfo, OtherInfo, ShowData

RESULT_SNAPSHOT_FORMAT = "mdcx-result-snapshot"
RESULT_SNAPSHOT_VERSION = 1
ResultStatus = Literal["succ", "fail"]


class ResultSnapshotError(ValueError):
    """Raised when a saved result snapshot cannot be read safely."""


def _json_key(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {_json_key(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


def _restore_file_info(raw: object) -> FileInfo:
    result = FileInfo.empty()
    if not isinstance(raw, dict):
        return result

    path_fields = {"file_path", "file_show_path", "folder_path"}
    for key, value in raw.items():
        if not hasattr(result, key):
            continue
        if key in path_fields:
            value = Path(str(value)) if value else Path()
        setattr(result, key, value)
    return result


def _restore_field_sources(raw: object) -> dict[CrawlerResultFields, str]:
    if not isinstance(raw, dict):
        return {}
    restored: dict[CrawlerResultFields, str] = {}
    for key, value in raw.items():
        try:
            field = CrawlerResultFields(str(key))
        except ValueError:
            continue
        restored[field] = str(value)
    return restored


def _restore_provenance(raw: object) -> dict[str, FieldProvenance]:
    if not isinstance(raw, dict):
        return {}
    restored: dict[str, FieldProvenance] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        restored[str(key)] = FieldProvenance(
            value=value.get("value"),
            source=str(value.get("source", "")),
            translated=bool(value.get("translated", False)),
            priority_chain=tuple(str(item) for item in value.get("priority_chain", []) or []),
        )
    return restored


def _restore_external_ids(raw: object) -> dict[Website, str]:
    if not isinstance(raw, dict):
        return {}
    restored: dict[Website, str] = {}
    for key, value in raw.items():
        try:
            website = Website(str(key))
        except ValueError:
            continue
        restored[website] = str(value)
    return restored


def _restore_crawlers_result(raw: object) -> CrawlersResult:
    result = CrawlersResult.empty()
    if not isinstance(raw, dict):
        return result

    for key, value in raw.items():
        if not hasattr(result, key):
            continue
        if key == "scraping_type":
            try:
                value = FixedScrapingType(str(value))
            except ValueError:
                value = result.scraping_type
        elif key == "field_sources":
            value = _restore_field_sources(value)
        elif key == "provenance":
            value = _restore_provenance(value)
        elif key == "external_ids":
            value = _restore_external_ids(value)
        elif key in {"thumb_list", "poster_list"} and isinstance(value, list):
            value = [tuple(item) if isinstance(item, list) else item for item in value]
        setattr(result, key, value)
    return result


def _restore_other_info(raw: object) -> OtherInfo:
    result = OtherInfo.empty()
    if not isinstance(raw, dict):
        return result

    path_fields = {"fanart_path", "poster_path", "thumb_path"}
    tuple_fields = {"poster_size", "thumb_size"}
    for key, value in raw.items():
        if not hasattr(result, key):
            continue
        if key in path_fields:
            value = Path(str(value)) if value else None
        elif key in tuple_fields and isinstance(value, list):
            value = tuple(int(item) for item in value[:2])
        setattr(result, key, value)
    return result


def show_data_to_dict(show_data: ShowData) -> dict[str, Any]:
    return {
        "show_name": show_data.show_name,
        "file_info": _json_value(show_data.file_info),
        "data": _json_value(show_data.data),
        "other": _json_value(show_data.other),
    }


def show_data_from_dict(raw: object) -> ShowData:
    if not isinstance(raw, dict):
        raise ResultSnapshotError("结果记录格式错误")
    return ShowData(
        file_info=_restore_file_info(raw.get("file_info")),
        data=_restore_crawlers_result(raw.get("data")),
        other=_restore_other_info(raw.get("other")),
        show_name=str(raw.get("show_name", "")).strip(),
    )


def save_result_snapshot(path: Path, records: list[tuple[ResultStatus, ShowData]]) -> None:
    payload = {
        "format": RESULT_SNAPSHOT_FORMAT,
        "version": RESULT_SNAPSHOT_VERSION,
        "records": [
            {
                "status": status,
                "show_data": show_data_to_dict(show_data),
            }
            for status, show_data in records
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_result_snapshot(path: Path) -> list[tuple[ResultStatus, ShowData]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ResultSnapshotError(f"无法读取结果文件：{error}") from error

    if not isinstance(payload, dict) or payload.get("format") != RESULT_SNAPSHOT_FORMAT:
        raise ResultSnapshotError("不是 MDCx 结果文件")
    if payload.get("version") != RESULT_SNAPSHOT_VERSION:
        raise ResultSnapshotError(f"不支持的结果文件版本：{payload.get('version')}")

    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise ResultSnapshotError("结果文件缺少 records 列表")

    records: list[tuple[ResultStatus, ShowData]] = []
    for raw_record in raw_records:
        if not isinstance(raw_record, dict):
            raise ResultSnapshotError("结果文件包含无效记录")
        status = raw_record.get("status")
        if status not in {"succ", "fail"}:
            raise ResultSnapshotError(f"未知结果状态：{status}")
        show_data = show_data_from_dict(raw_record.get("show_data"))
        if not show_data.show_name:
            raise ResultSnapshotError("结果记录缺少名称")
        records.append((status, show_data))
    return records
