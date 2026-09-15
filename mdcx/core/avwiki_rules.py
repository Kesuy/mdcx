from __future__ import annotations

import re

# MGS 素人系中，有一部分作品在 MDCx 中拿到的是“厂牌短番号”，没有
# 200GANA / 300MIUM 这类三位数字前缀，因此不会被现有 SUREN 分类命中。
# 这里仅负责“是否值得查询 AV-Wiki”，不改变 SUREN / YOUMA 刮削分类。
#
# 数字前缀 MGS 番号继续由现有 SUREN 逻辑覆盖；这里补充 AV-Wiki 的 MGS
# 索引中会以短番号出现的系列，避免因为文件名省略 MGS 数字前缀而漏查。
AVWIKI_MGS_AMATEUR_SHORT_PREFIXES = frozenset(
    {
        "CMI",  # フルセイル / ゲスの極み映像
        "DDH",  # ドキュメントdeハメハメ
        "DNW",  # ドキュメントなう。
        "FIV",  # FIVE STARS
        "GBAN",  # ゲッツ!!
        "GES",  # フルセイル / ゲスの極み女子寮
        "GETS",  # ゲッツ!!
        "GNAB",  # ゲッツ!! / BANG!!
        "GZAP",  # ゲッツ!! / ZAP
        "KKJ",  # マジック / 口説き術
        "MFCC",  # MOON FORCE CHEERS omnibus
        "MFCD",  # MOON FORCE omnibus
        "MFCS",  # MOON FORCE 2nd
        "MFCT",  # MOON FORCE 2nd omnibus
        "MFCW",  # MOON FORCE WIFE
        "MGT",  # MEGATRA
        "MMNM",  # しろうとまんまん沼
        "ONEZ",  # ONE MORE
        "ORECZ",  # 俺の素人
        "OREMO",
        "ORESL",
        "OREV",
        "OTIM",  # ONETIME
        "SIMA",  # しろうとまんまん+
        "SIMD",
        "SIMF",
        "SIMH",
        "SIMM",
        "SIMT",
        "SIMW",
        "SRMM",
        "ZRC",  # マジック / 全裸カタログ
    }
)

# AV-Wiki 自身维护的 MGS 索引作为元数据兜底。这样即使同一厂牌以后新增短番号
# 前缀，只要 scraper 能拿到 studio / publisher / series，仍然会补查真实演员。
# 普通有码厂牌（S1、MOODYZ、IDEA POCKET 等）不会命中。
#
# “プレステージ”本身故意不作为提示：它同时包含大量普通有码作品，直接匹配会
# 让普通 YOUMA 平白增加 AV-Wiki 请求。其 MGS 素人系列通过更具体的系列名、
# 短番号前缀或现有数字前缀 SUREN 规则覆盖。
AVWIKI_MGS_AMATEUR_LABEL_HINTS = frozenset(
    {
        # AV-Wiki: MGS動画に出てるAV女優（素人名義）の名前が知りたい！
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
        # AV-Wiki MGSグループ / omnibus index. Existing labels above intentionally
        # overlap Jackson/KANBi/MOON FORCE/シロウトTV/ナンパTV/黒船.
        "○○から中出し",
        "FIVE STARS",
        "HIGH SCORE",
        "JUNKTION+",
        "MEGATRA",
        "SEXの逸材",
        "VIDEO PODCAST",
        "アフターサービス",
        "ドキュメントなう",
        "BOING",
        "GOOD-BYE-CHERRYBOY",
        "セイキョウイク",
        "BUZZDOCUMENT",
        "ONE MORE",
        "ONETIME",
        "ゲッツ",
        "シロウトなんなん",
        "フルセイル",
        "マジック",
        "同人AKIVAサークル",
        "舞ワイフ",
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
