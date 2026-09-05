from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase, QRawFont
from PyQt6.QtWidgets import QApplication

CJK_VISUAL_SMOKE_TEXT = "刮削目录 / 网站 / 下载 / 命名 / 演员 / 设置 / 字段来源 / 失败中心"

_LINUX_PREFERRED_CJK_FAMILIES = (
    "Noto Sans CJK SC",
    "Noto Sans SC",
)

_WINDOWS_PREFERRED_CJK_FAMILIES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "DengXian",
    "Noto Sans SC",
    "SimHei",
    "SimSun",
)


def _supports_smoke_text(family: str) -> bool:
    raw_font = QRawFont.fromFont(QFont(family))
    return raw_font.isValid() and all(
        raw_font.supportsCharacter(ord(character))
        for character in CJK_VISUAL_SMOKE_TEXT
        if "\u4e00" <= character <= "\u9fff"
    )


def _load_windows_system_cjk_fonts() -> None:
    """Expose installed Windows fonts when Qt's offscreen plugin finds none."""
    if os.name != "nt":
        return
    font_root = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for filename in ("msyh.ttc", "NotoSansSC-VF.ttf", "Deng.ttf", "simhei.ttf", "simsun.ttc"):
        font_path = font_root / filename
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))


def configure_cjk_visual_test_font(app: QApplication) -> str | None:
    """Select an installed CJK font for visual tests without changing the app."""
    _load_windows_system_cjk_fonts()
    installed = QFontDatabase.families()
    installed_by_casefold = {family.casefold(): family for family in installed}
    preferred_families = _WINDOWS_PREFERRED_CJK_FAMILIES if os.name == "nt" else _LINUX_PREFERRED_CJK_FAMILIES
    ordered_families = [
        installed_by_casefold[family.casefold()]
        for family in preferred_families
        if family.casefold() in installed_by_casefold
    ]
    ordered_families.extend(
        family
        for family in QFontDatabase.families(QFontDatabase.WritingSystem.SimplifiedChinese)
        if family not in ordered_families
    )
    for family in ordered_families:
        if not _supports_smoke_text(family):
            continue
        font = QFont(family)
        if app.font().pointSizeF() > 0:
            font.setPointSizeF(app.font().pointSizeF())
        app.setFont(font)
        return family
    return None


def cjk_visual_test_font_error() -> str:
    return (
        "CJK visual/layout smoke skipped: no installed font can render "
        f"{CJK_VISUAL_SMOKE_TEXT!r}. Install fonts-noto-cjk on Linux or a system CJK font on Windows."
    )
