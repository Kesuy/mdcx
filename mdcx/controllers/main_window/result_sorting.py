import re
from dataclasses import dataclass
from typing import Literal

ResultSortMode = Literal["完成顺序", "番号", "演员"]


@dataclass(frozen=True)
class ResultSortEntry:
    show_name: str
    number: str
    actor: str
    insertion_index: int


def _natural_key(value: str) -> tuple[tuple[int, object], ...]:
    parts = re.split(r"(\d+)", str(value or "").strip().casefold())
    return tuple((1, int(part)) if part.isdigit() else (0, part) for part in parts if part)


def sort_result_entries(
    entries: list[ResultSortEntry],
    mode: ResultSortMode,
    *,
    descending: bool = False,
) -> list[ResultSortEntry]:
    if mode == "番号":
        return sorted(
            entries,
            key=lambda entry: (_natural_key(entry.number), _natural_key(entry.show_name), entry.insertion_index),
            reverse=descending,
        )
    if mode == "演员":
        return sorted(
            entries,
            key=lambda entry: (_natural_key(entry.actor), _natural_key(entry.number), entry.insertion_index),
            reverse=descending,
        )
    return sorted(entries, key=lambda entry: entry.insertion_index, reverse=descending)
