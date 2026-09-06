from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MDCX_OFFLINE", "1")

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractScrollArea,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTabWidget,
    QWidget,
)

import mdcx.controllers.main_window.main_window as main_window_module
from mdcx.controllers.main_window.failure_center import FailureCenterDialog
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout, show_responsive_overlay
from mdcx.models.failure import FailureCategory, FailureRecord


WINDOW_SIZES = ((880, 700), (1100, 760), (1400, 900), (1920, 1080))
CONTROL_TYPES = (QLabel, QPushButton, QCheckBox, QRadioButton, QComboBox, QLineEdit)


def _safe_name(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z._-]+", "_", text.strip())
    return text.strip("_") or "view"


def _patch_runtime_side_effects() -> None:
    main_window_module.check_version = lambda: None
    main_window_module.get_success_list = lambda: None
    main_window_module.save_remain_list = lambda: None
    main_window_module.show_netstatus = lambda: None
    MyMAinWindow.auto_start = lambda self: None


def _render_widget(widget: QWidget, path: Path, quality: int = 80) -> tuple[int, int]:
    image = widget.grab().toImage()
    if image.isNull():
        raise RuntimeError(f"failed to render {widget.objectName() or type(widget).__name__}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(path), "JPG", quality):
        raise RuntimeError(f"failed to save {path}")
    return image.width(), image.height()


def _has_scroll_ancestor(widget: QWidget, stop: QWidget) -> bool:
    parent = widget.parentWidget()
    while parent is not None and parent is not stop:
        if isinstance(parent, QAbstractScrollArea):
            return True
        parent = parent.parentWidget()
    return False


def _plain_text(widget: QWidget) -> str:
    if isinstance(widget, QLabel):
        return re.sub(r"<[^>]+>", "", widget.text()).strip()
    if isinstance(widget, (QPushButton, QCheckBox, QRadioButton)):
        return widget.text().replace("&", "").strip()
    if isinstance(widget, QComboBox):
        return widget.currentText().strip()
    if isinstance(widget, QLineEdit):
        return widget.placeholderText().strip()
    return ""


def _scan_runtime_geometry(window: QWidget, state: str) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for widget in window.findChildren(QWidget):
        if not widget.isVisibleTo(window) or widget.width() <= 0 or widget.height() <= 0:
            continue
        name = widget.objectName() or type(widget).__name__
        parent = widget.parentWidget()
        if parent is not None and parent.isVisibleTo(window) and not _has_scroll_ancestor(widget, window):
            geometry = widget.geometry()
            bounds = parent.rect().adjusted(-2, -2, 2, 2)
            if not bounds.contains(geometry):
                intersection = bounds.intersected(geometry)
                full_area = max(1, geometry.width() * geometry.height())
                visible_area = max(0, intersection.width()) * max(0, intersection.height())
                if visible_area / full_area < 0.85:
                    issues.append(
                        {
                            "state": state,
                            "kind": "outside-parent",
                            "widget": name,
                            "class": type(widget).__name__,
                            "geometry": [geometry.x(), geometry.y(), geometry.width(), geometry.height()],
                            "parent": parent.objectName() or type(parent).__name__,
                        }
                    )

        if not isinstance(widget, CONTROL_TYPES):
            continue
        text = _plain_text(widget)
        if not text or "\n" in text:
            continue
        if isinstance(widget, QLabel) and widget.wordWrap():
            continue
        if widget.property("mdcxFullText") is not None:
            continue
        available = max(1, widget.contentsRect().width() - 6)
        measured = widget.fontMetrics().horizontalAdvance(text)
        if measured > available * 1.18 and len(text) >= 6:
            issues.append(
                {
                    "state": state,
                    "kind": "possible-text-clipping",
                    "widget": name,
                    "class": type(widget).__name__,
                    "width": widget.width(),
                    "text_width": measured,
                    "text": text[:100],
                }
            )
    return issues


def _outermost_visible_tabs(container: QWidget, window: QWidget) -> list[QTabWidget]:
    result: list[QTabWidget] = []
    for tab in container.findChildren(QTabWidget):
        if not tab.isVisibleTo(window) or tab.count() == 0:
            continue
        parent = tab.parentWidget()
        nested = False
        while parent is not None and parent is not container:
            if isinstance(parent, QTabWidget):
                nested = True
                break
            parent = parent.parentWidget()
        if not nested:
            result.append(tab)
    return sorted(result, key=lambda item: (-item.count(), item.objectName()))


def _tab_title(tab: QTabWidget, index: int) -> str:
    return tab.tabText(index).strip() or tab.widget(index).objectName() or f"tab-{index}"


def _capture_scroll_contents(container: QWidget, output: Path, prefix: str) -> list[str]:
    saved: list[str] = []
    for scroll in container.findChildren(QScrollArea):
        if not scroll.isVisibleTo(container) or scroll.widget() is None:
            continue
        content = scroll.widget()
        if content.height() <= scroll.viewport().height() + 20:
            continue
        filename = f"scroll-{_safe_name(prefix)}-{_safe_name(scroll.objectName())}.jpg"
        _render_widget(content, output / filename, quality=72)
        saved.append(filename)
    return saved


def _make_contact_sheet(output: Path, title: str, shots: list[dict[str, object]]) -> str | None:
    if not shots:
        return None
    thumb_w, thumb_h, label_h = 430, 300, 30
    columns = 3
    rows = (len(shots) + columns - 1) // columns
    sheet = QImage(columns * thumb_w, rows * (thumb_h + label_h), QImage.Format.Format_RGB32)
    sheet.fill(Qt.GlobalColor.white)
    painter = QPainter(sheet)
    painter.setPen(Qt.GlobalColor.black)
    for index, shot in enumerate(shots):
        row, column = divmod(index, columns)
        x = column * thumb_w
        y = row * (thumb_h + label_h)
        source = QImage(str(output / str(shot["file"])))
        if not source.isNull():
            scaled = source.scaled(
                thumb_w - 8,
                thumb_h - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            target = QRect(x + 4, y + 4, scaled.width(), scaled.height())
            painter.drawImage(target, scaled)
        painter.drawText(QRect(x + 6, y + thumb_h, thumb_w - 12, label_h), Qt.AlignmentFlag.AlignLeft, str(shot["state"])[:70])
    painter.end()
    filename = f"contact-{_safe_name(title)}.jpg"
    sheet.save(str(output / filename), "JPG", 75)
    return filename


def _capture_failure_center(output: Path) -> dict[str, object]:
    dialog = FailureCenterDialog()
    dialog.set_records(
        [
            FailureRecord(Path(r"D:\Media\ABC-123 very long sample filename.mp4"), "scrape", FailureCategory.NETWORK, "连接超时", True, site="javdb"),
            FailureRecord(Path(r"D:\Media\XYZ-987.mp4"), "metadata", FailureCategory.METADATA, "缺少必要字段", False, site="dmm"),
            FailureRecord(Path(r"D:\Media\TEST-001.mp4"), "file", FailureCategory.FILE_IO, "文件被占用", True),
        ]
    )
    dialog.resize(920, 600)
    dialog.show()
    QApplication.processEvents()
    filename = "dialog-failure-center.jpg"
    size = _render_widget(dialog, output / filename)
    dialog.hide()
    dialog.deleteLater()
    return {"state": "failure-center", "file": filename, "size": list(size)}


def run(output: Path, full_scroll: bool) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    _patch_runtime_side_effects()
    app = QApplication.instance() or QApplication([])
    window = MyMAinWindow()
    window.show()
    app.processEvents()
    if not getattr(window, "_startup_finished", False):
        window._finish_startup()
    app.processEvents()

    all_issues: list[dict[str, object]] = []
    manifest: dict[str, object] = {
        "platform": os.name,
        "qt_platform": os.environ.get("QT_QPA_PLATFORM"),
        "qt_scale_factor": os.environ.get("QT_SCALE_FACTOR", "default"),
        "sizes": {},
        "scroll_captures": [],
    }

    stack = window.Ui.stackedWidget
    for width, height in WINDOW_SIZES:
        window.resize(width, height)
        apply_responsive_layout(window)
        app.processEvents()
        size_key = f"{width}x{height}"
        shots: list[dict[str, object]] = []

        for page_index in range(stack.count()):
            stack.setCurrentIndex(page_index)
            apply_responsive_layout(window)
            app.processEvents()
            page = stack.currentWidget()
            page_name = page.objectName() or f"page-{page_index}"
            tabs = _outermost_visible_tabs(page, window)
            primary_tab = tabs[0] if tabs else None
            tab_indices = range(primary_tab.count()) if primary_tab is not None else (None,)

            for tab_index in tab_indices:
                if primary_tab is not None and tab_index is not None:
                    primary_tab.setCurrentIndex(tab_index)
                    app.processEvents()
                    state = (
                        f"{page_name}__{primary_tab.objectName()}__{tab_index:02d}__"
                        f"{_tab_title(primary_tab, tab_index)}"
                    )
                else:
                    state = page_name
                apply_responsive_layout(window)
                app.processEvents()
                filename = f"{size_key}-{_safe_name(state)}.jpg"
                size = _render_widget(window, output / filename)
                shots.append({"state": state, "file": filename, "size": list(size)})
                all_issues.extend(_scan_runtime_geometry(window, f"{size_key}:{state}"))
                if full_scroll and (width, height) == (1400, 900):
                    manifest["scroll_captures"].extend(_capture_scroll_contents(page, output, state))

        if (width, height) == (1400, 900):
            for overlay_name in ("widget_show_success", "widget_show_tips", "widget_nfo"):
                overlay = getattr(window.Ui, overlay_name, None)
                if overlay is None:
                    continue
                show_responsive_overlay(window, overlay)
                app.processEvents()
                state = f"overlay-{overlay_name}"
                filename = f"{size_key}-{state}.jpg"
                size = _render_widget(window, output / filename)
                shots.append({"state": state, "file": filename, "size": list(size)})
                all_issues.extend(_scan_runtime_geometry(window, f"{size_key}:{state}"))
                overlay.hide()

            shots.append(_capture_failure_center(output))

        contact = _make_contact_sheet(output, size_key, shots)
        manifest["sizes"][size_key] = {"shots": shots, "contact": contact}

    unique: dict[tuple[object, ...], dict[str, object]] = {}
    for issue in all_issues:
        key = (issue.get("state"), issue.get("kind"), issue.get("widget"), issue.get("text"))
        unique[key] = issue
    issues = list(unique.values())
    manifest["issue_count"] = len(issues)
    manifest["issues"] = issues
    (output / "report.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"Runtime UI audit: {len(issues)} heuristic warnings",
        f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}",
        f"QT_SCALE_FACTOR={os.environ.get('QT_SCALE_FACTOR', 'default')}",
        "",
    ]
    for issue in issues:
        lines.append(json.dumps(issue, ensure_ascii=False))
    (output / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for timer_name in ("timer", "timer_scrape", "timer_update", "timer_remain_task"):
        timer = getattr(window, timer_name, None)
        if timer is not None:
            timer.stop()
    window.hide()
    window.deleteLater()
    app.processEvents()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--full-scroll", action="store_true")
    args = parser.parse_args()
    run(args.output, args.full_scroll)


if __name__ == "__main__":
    main()
