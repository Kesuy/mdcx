from __future__ import annotations

import re

# MGS 素人系中，有一部分作品在 MDCx 中拿到的是“厂牌短番号”，没有
# 200GANA / 300MIUM 这类三位数字前缀，因此不会被现有 SUREN 分类命中。
# 这里仅负责“是否值得查询 AV-Wiki”，不改变 SUREN / YOUMA 刮削分类。
#
# 来源以 hdblog 的 MGS Amateur 分类为目标，并用 AV-Wiki 的 MGS 索引补齐
# 当前仍在更新的短番号系列。数字前缀 MGS 番号仍由现有 SUREN 逻辑覆盖。
AVWIKI_MGS_AMATEUR_SHORT_PREFIXES = frozenset(
    {
        "DDH",  # ドキュメントdeハメハメ
        "MFCW",  # MOON FORCE WIFE
        "MFCS",  # MOON FORCE 2nd
        "MMNM",  # しろうとまんまん沼
        "ORECZ",  # 俺の素人
        "OREMO",
        "ORESL",
        "OREV",
        "SIMA",  # しろうとまんまん+
        "SIMD",
        "SIMF",
        "SIMH",
        "SIMM",
        "SIMT",
        "SIMW",
        "SRMM",
    }
)

# 作为短番号表的兜底：同一 MGS 素人厂牌可能增加新前缀，只要刮削结果中的
# studio / publisher / series 明确属于这些系列，仍然触发 AV-Wiki。
# 普通有码厂牌（S1、MOODYZ、IDEA POCKET 等）不会命中。
AVWIKI_MGS_AMATEUR_LABEL_HINTS = frozenset(
    {
        "ARA",
        "BIBID",
        "DIEGO",
        "ENEMA",
        "HHH",
        "JACKSON",
        "KANBI",
        "MOONFORCE",
        "MOMOCO",
        "NTR.NET",
        "OUTDOOR",
        "SNAP×SNAP",
        "SUKESUKE+",
        "TAG",
        "TOKYO不倫FILE",
        "TOPランナー",
        "VLOGDIARY",
        "VOLARE",
        "えちサポ",
        "ギャルぽよ",
        "きゃんたま清掃員",
        "ゲスヤミ",
        "ゲス闇",
        "シロウトTV",
        "しろうとまんまん",
        "ドッキング",
        "ドキュメンTV",
        "ドキュメントDEハメハメ",
        "なまなま.NET",
        "ナンパDEハメハメ",
        "ナンパTV",
        "ハーレムTV",
        "ハメタバース",
        "はめちゃん",
        "プレステージプレミアム",
        "マッチングTV",
        "まんまんランド",
        "ヤミヤミ",
        "ラグジュTV",
        "ねこじま",
        "黒影",
        "黒船",
        "再教育",
        "最強属性",
        "素人こねくしょん",
        "同人配信",
        "何それえっろ",
        "変態サムライ",
        "素人CLOVER",
        "素人ハメ次郎",
        "街角シロウトナンパ",
        "俺の素人",
    }
)


def _normalize_label(value: str) -> str:
    return re.sub(r"[\s・･_.\-—–―()（）【】\[\]『』「」]+", "", str(value or "")).upper()


def _number_prefix(number: str) -> str:
    normalized = str(number or "").strip().upper()
    match = re.match(r"^([A-Z]+)", normalized)
    return match.group(1) if match else ""


def _label_matches(value: str, hint: str) -> bool:
    # ARA / HHH / TAG 这类短英文代号用包含匹配容易误伤普通厂牌
    # （例如 PARADISE、VINTAGE），因此短纯英文代号只允许完全相等。
    if hint.isascii() and hint.isalnum() and len(hint) <= 4:
        return value == hint
    return hint in value


def is_avwiki_mgs_amateur_number(number: str) -> bool:
    """Return True for known MGS-amateur short-number families."""
    return _number_prefix(number) in AVWIKI_MGS_AMATEUR_SHORT_PREFIXES


def is_avwiki_mgs_amateur_metadata(*values: str) -> bool:
    """Match known MGS-amateur makers/labels/series without changing scrape type."""
    normalized_values = [_normalize_label(value) for value in values if str(value or "").strip()]
    if not normalized_values:
        return False
    hints = tuple(_normalize_label(hint) for hint in AVWIKI_MGS_AMATEUR_LABEL_HINTS if _normalize_label(hint))
    return any(_label_matches(value, hint) for value in normalized_values for hint in hints)


def is_avwiki_mgs_amateur_result(number: str, studio: str = "", publisher: str = "", series: str = "") -> bool:
    return is_avwiki_mgs_amateur_number(number) or is_avwiki_mgs_amateur_metadata(studio, publisher, series)
