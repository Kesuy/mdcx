"""Capture every settings tab for visual layout inspection in CI."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MDCX_OFFLINE", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QScrollArea, QWidget

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout
from mdcx.controllers.main_window.settings_composites import _ensure_force_avwiki_actor_checkbox
from mdcx.controllers.main_window.settings_layout_polish import polish_settings_layout


def _direct_scroll_area(tab: QWidget) -> QScrollArea | None:
    areas = tab.findChildren(QScrollArea, options=Qt.FindChildOption.FindDirectChildrenOnly)
    return areas[0] if len(areas) == 1 else None


def _walk_item_widgets(item):
    widget = item.widget()
    if widget is not None:
        yield widget
        return
    layout = item.layout()
    if layout is None:
        return
    for index in range(layout.count()):
        yield from _walk_item_widgets(layout.itemAt(index))


def _is_multiline(widget: QWidget) -> bool:
    if not isinstance(widget, QLabel):
        return False
    text = widget.text().lower()
    return widget.wordWrap() or "\n" in text or "<br" in text


def _audit_rows(ui, tab: QWidget) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for layout in vars(ui).values():
        if not isinstance(layout, QGridLayout):
            continue
        parent = layout.parentWidget()
        if parent is None or not tab.isAncestorOf(parent):
            continue

        row_items: dict[int, list[object]] = {}
        for index in range(layout.count()):
            row, _column, row_span, _column_span = layout.getItemPosition(index)
            if row_span != 1:
                continue
            row_items.setdefault(row, []).append(layout.itemAt(index))

        for row, items in sorted(row_items.items()):
            widgets = []
            for item in items:
                for widget in _walk_item_widgets(item):
                    if not widget.isVisibleTo(tab):
                        continue
                    text = getattr(widget, "text", lambda: "")()
                    if not text and not widget.inherits("QLineEdit") and not widget.inherits("QComboBox"):
                        continue
                    center = widget.mapTo(parent, widget.rect().center())
                    widgets.append(
                        {
                            "name": widget.objectName(),
                            "class": widget.metaObject().className(),
                            "text": text,
                            "x": widget.mapTo(parent, widget.rect().topLeft()).x(),
                            "y": widget.mapTo(parent, widget.rect().topLeft()).y(),
                            "w": widget.width(),
                            "h": widget.height(),
                            "center_y": center.y(),
                            "multiline": _is_multiline(widget),
                        }
                    )
            if len(widgets) < 2:
                continue
            centers = [int(widget["center_y"]) for widget in widgets]
            rows.append(
                {
                    "layout": layout.objectName(),
                    "row": row,
                    "row_min_height": layout.rowMinimumHeight(row),
                    "center_spread": max(centers) - min(centers),
                    "widgets": widgets,
                }
            )
    return rows


def main() -> None:
    output = Path(os.environ.get("MDCX_UI_CAPTURE_DIR", "ui-captures"))
    output.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    MyMAinWindow.load_config = lambda self: None
    MyMAinWindow._finish_startup = lambda self: None
    window = MyMAinWindow()
    _ensure_force_avwiki_actor_checkbox(window.Ui)
    polish_settings_layout(window.Ui)
    window.resize(1920, 1080)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_setting)
    window.show()
    app.processEvents()
    apply_responsive_layout(window)
    polish_settings_layout(window.Ui)
    app.processEvents()

    tabs = window.Ui.tabWidget
    audit: dict[str, object] = {"window": [window.width(), window.height()], "tabs": []}
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        app.processEvents()
        apply_responsive_layout(window)
        polish_settings_layout(window.Ui)
        app.processEvents()

        tab = tabs.widget(index)
        title = tabs.tabText(index).strip() or tab.objectName()
        safe_title = "".join(char if char.isalnum() or char in "-_" else "_" for char in title)
        prefix = f"{index:02d}_{safe_title}"

        window.grab().save(str(output / f"window_{prefix}.png"))
        area = _direct_scroll_area(tab)
        if area is not None and area.widget() is not None:
            content = area.widget()
            content.grab().save(str(output / f"content_{prefix}.png"))
            content_size = [content.width(), content.height()]
        else:
            content_size = None

        rows = _audit_rows(window.Ui, tab)
        suspicious = [
            row
            for row in rows
            if int(row["center_spread"]) > 1
            and not any(bool(widget["multiline"]) for widget in row["widgets"])
        ]
        audit["tabs"].append(
            {
                "index": index,
                "object_name": tab.objectName(),
                "title": title,
                "content_size": content_size,
                "suspicious_rows": suspicious,
                "all_rows": rows,
            }
        )

    (output / "layout_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    suspicious_count = sum(len(tab["suspicious_rows"]) for tab in audit["tabs"])
    print(f"Captured {tabs.count()} settings tabs to {output}; suspicious compact rows: {suspicious_count}")
    window.close()
    window.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    main()
