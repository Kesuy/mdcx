from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MDCX_OFFLINE", "1")

from PyQt6.QtWidgets import QApplication

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout
from mdcx.gen.field_enums import CrawlerResultFields
from mdcx.models.failure import FailureCategory, FailureRecord
from mdcx.models.flags import Flags
from mdcx.models.types import ShowData
from mdcx.signals import signal_qt
from ui_runtime_audit import _configure_cjk_font, _patch_runtime_side_effects, _render_widget

SIZES = ((880, 700), (1100, 760), (1400, 900))


def _data(number: str, source: str, path: str, status: str) -> ShowData:
    value = ShowData.empty()
    value.show_name = number
    value.data.number = number
    value.data.title = f"{number} 示例标题 {status}"
    value.data.field_sources[CrawlerResultFields.TITLE] = source
    value.file_info.number = number
    value.file_info.file_name = Path(path).name
    value.file_info.file_path = Path(path)
    return value


def _populate_tree(window: MyMAinWindow) -> None:
    success = [
        ("ABC-123", "javdb", r"D:\Media\有码\ABC-123 示例文件 1080p.mkv"),
        ("IPZZ-941", "dmm", r"D:\Media\长目录名称\IPZZ-941 example filename with very long suffix 2160p HDR.mp4"),
        ("FC2-PPV-1234567", "fc2", r"D:\Media\FC2\2026\FC2-PPV-1234567 这是一个很长的文件名用于测试结果列表显示.webm"),
        ("HEYZO-1234", "本地 NFO", r"D:\Media\欧美\HEYZO-1234.mp4"),
        ("SAMPLE-0001", "javbus", r"D:\Media\Nested\One\Two\Three\SAMPLE-0001 long path sample.mp4"),
    ]
    failed = [
        ("FAIL-NET-001", "javdb", r"D:\Media\Failed\FAIL-NET-001 network timeout sample.mp4"),
        ("FAIL-AUTH-002", "fc2", r"D:\Media\Failed\FAIL-AUTH-002 cookie expired sample with long name.mp4"),
        ("FAIL-PARSE-003", "dmm", r"D:\Media\Failed\FAIL-PARSE-003 parser changed sample.mp4"),
        ("FAIL-IO-004", "local", r"D:\Media\Failed\非常长的目录名\FAIL-IO-004 file locked by another process.mkv"),
    ]
    for number, source, path in success:
        item = _data(number, source, path, "刮削成功")
        window._addTreeChild("succ", number, item)
        window.json_array[number] = item
    for number, source, path in failed:
        item = _data(number, source, path, "刮削失败")
        window._addTreeChild("fail", number, item)
        window.json_array[number] = item
    window.item_succ.setText(0, f"成功 ({window.item_succ.childCount()})")
    window.item_fail.setText(0, f"失败 ({window.item_fail.childCount()})")
    window.Ui.treeWidget_number.expandAll()


def _records() -> list[FailureRecord]:
    return [
        FailureRecord(
            Path(r"D:\Media\Failed\FAIL-NET-001 network timeout sample.mp4"),
            "crawl",
            FailureCategory.NETWORK,
            "请求 https://example.invalid/api/movie/FAIL-NET-001 超时：ReadTimeout after 30 seconds",
            True,
            site="javdb",
            debug_detail="Traceback (most recent call last):\n  File crawler.py, line 321\nTimeoutError: simulated timeout",
        ),
        FailureRecord(
            Path(r"D:\Media\Failed\FAIL-AUTH-002 cookie expired sample with long name.mp4"),
            "search",
            FailureCategory.AUTHENTICATION,
            "HTTP 403，Cookie 已失效，请重新登录后更新 Cookie。",
            False,
            site="fc2cmadb",
        ),
        FailureRecord(
            Path(r"D:\Media\Failed\FAIL-PARSE-003 parser changed sample.mp4"),
            "metadata",
            FailureCategory.PARSER,
            "页面结构变化，未找到标题选择器 #video-title；这是用于验证长错误原因显示的附加说明。",
            False,
            site="dmm",
            debug_detail="selector=#video-title\nhtml_length=184233\nParserError: expected node was not found",
        ),
        FailureRecord(
            Path(r"D:\Media\Failed\非常长的目录名\FAIL-IO-004 file locked by another process.mkv"),
            "file",
            FailureCategory.FILE_IO,
            "[WinError 32] 文件正由另一进程使用，无法移动到目标目录。",
            True,
            site="本地文件",
        ),
        FailureRecord(
            Path(r"D:\Media\Failed\Nested\Level1\Level2\Level3\FAIL-IMG-005 extremely-long-name-for-layout-testing.mp4"),
            "image",
            FailureCategory.IMAGE_DOWNLOAD,
            "海报下载返回 HTTP 503，备用图片源也暂时不可用。",
            True,
            site="javbus",
        ),
    ]


def _size(window: MyMAinWindow, app: QApplication, width: int, height: int) -> None:
    window.resize(width, height)
    apply_responsive_layout(window)
    app.processEvents()


def _main_shot(window: MyMAinWindow, app: QApplication, output: Path, name: str, size: tuple[int, int]) -> None:
    _size(window, app, *size)
    _render_widget(window, output / f"{size[0]}x{size[1]}-{name}.jpg", quality=84)


def _success_history(window: MyMAinWindow, app: QApplication, output: Path, report: dict) -> None:
    Flags.success_list = {
        Path(rf"D:\Media\Library\分类目录-{index:02d}\TEST-{index:04d} 这是用于滚动和长路径测试的已刮削成功文件名 2160p.mkv")
        for index in range(1, 31)
    }
    for width, height in SIZES:
        _size(window, app, width, height)
        window.pushButton_view_success_file_clicked()
        app.processEvents()
        overlay = window.Ui.widget_show_success
        assert overlay.isVisible()
        parent = overlay.parentWidget()
        report["checks"][f"success_overlay_{width}_parent"] = parent.objectName() if parent else None
        report["checks"][f"success_overlay_{width}_geometry"] = [
            overlay.x(), overlay.y(), overlay.width(), overlay.height()
        ]
        _render_widget(overlay, output / f"{width}x{height}-success-history-surface.jpg", quality=84)
        overlay.hide()
    text = window.Ui.textBrowser_show_success_list.toPlainText().splitlines()
    scroll = window.Ui.textBrowser_show_success_list.verticalScrollBar()
    report["checks"]["success_history_count"] = len(Flags.success_list)
    report["checks"]["success_history_text_lines"] = len(text)
    report["checks"]["success_history_scroll_max"] = scroll.maximum()
    assert len(text) == 30
    assert scroll.maximum() > 0


def _legacy_failures(window: MyMAinWindow, app: QApplication, output: Path, report: dict) -> None:
    Flags.failed_records = []
    rows = []
    for index in range(1, 36):
        path = Path(rf"D:\Media\Failed\批量任务\第{index:02d}组\FAIL-{index:04d} long failed filename sample.mp4")
        reason = (
            "网络请求超时，代理连接被重置；将在网络恢复后重试"
            if index % 3 == 1
            else "未找到匹配结果，请检查番号或切换数据源"
            if index % 3 == 2
            else "文件被占用，移动到目标目录失败 [WinError 32]"
        )
        rows.append((path, reason))
    Flags.failed_list = rows
    signal_qt.logs_failed_settext.emit("")
    for path, reason in rows:
        signal_qt.logs_failed_show.emit(f"{path}\n    原因：{reason}")
    window.update_failure_count("失败 (35)")
    window.show_hide_failed_list(True)
    app.processEvents()
    browser = window.Ui.textBrowser_log_main_3
    scroll = browser.verticalScrollBar()
    report["checks"]["failed_log_count"] = 35
    report["checks"]["failed_log_scroll_max"] = scroll.maximum()
    report["checks"]["failed_log_scroll_value"] = scroll.value()
    report["checks"]["failed_log_retry_visible"] = window.Ui.pushButton_scraper_failed_list.isVisible()
    report["checks"]["failed_log_save_visible"] = window.Ui.pushButton_save_failed_list.isVisible()
    assert scroll.maximum() > 0 and scroll.value() == scroll.maximum()
    assert window.Ui.pushButton_scraper_failed_list.isVisible()
    assert window.Ui.pushButton_save_failed_list.isVisible()
    for size in SIZES:
        _main_shot(window, app, output, "failed-log", size)
    window.show_hide_failed_list(False)


def _failure_center(window: MyMAinWindow, app: QApplication, output: Path, report: dict) -> None:
    Flags.failed_records = _records()
    Flags.failed_list = [record.legacy_tuple() for record in Flags.failed_records]
    window.pushButton_show_hide_failed_list_clicked()
    app.processEvents()
    dialog = window._failure_center
    report["checks"]["failure_center_rows"] = dialog.tree.topLevelItemCount()
    report["checks"]["failure_center_summary"] = dialog.summary.text()
    assert dialog.tree.topLevelItemCount() == 5
    assert dialog.retry_all.isEnabled()

    for width, height in ((700, 500), (920, 600)):
        dialog.resize(width, height)
        app.processEvents()
        _render_widget(dialog, output / f"failure-center-{width}x{height}.jpg", quality=84)

    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(1))
    app.processEvents()
    report["checks"]["non_retryable_button_enabled"] = dialog.retry_one.isEnabled()
    assert not dialog.retry_one.isEnabled()
    _render_widget(dialog, output / "failure-center-non-retryable.jpg", quality=84)

    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(0))
    app.processEvents()
    assert dialog.retry_one.isEnabled() and dialog.show_debug.isVisible()
    dialog.show_debug.setChecked(True)
    app.processEvents()
    assert "Traceback" in dialog.detail.toPlainText()
    report["checks"]["retryable_button_enabled"] = True
    report["checks"]["debug_button_visible"] = True
    _render_widget(dialog, output / "failure-center-debug-detail.jpg", quality=84)

    retried: list[FailureRecord] = []
    dialog._retry_callback = lambda records: retried.extend(records) or True
    before = dialog.tree.topLevelItemCount()
    dialog.retry_one.click()
    app.processEvents()
    report["checks"]["retry_selected_callback_count"] = len(retried)
    report["checks"]["failure_center_rows_after_retry"] = dialog.tree.topLevelItemCount()
    assert len(retried) == 1 and dialog.tree.topLevelItemCount() == before - 1
    _render_widget(dialog, output / "failure-center-after-retry.jpg", quality=84)
    dialog.hide()


def _main_failure_log(window: MyMAinWindow, app: QApplication, output: Path, report: dict) -> None:
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_log)
    window.Ui.textBrowser_log_main.clear()
    for index in range(1, 28):
        window.show_log_text(
            f"❌ [{index:02d}/27] FAIL-{index:04d} 刮削失败 | site=javdb | "
            f"D:\\Media\\VeryLongFolder\\FAIL-{index:04d}.mp4 | "
            "https://example.invalid/api/search?number=FAIL-0001&source=runtime-layout-audit | timeout=30s"
        )
    window._flush_main_log_queue()
    app.processEvents()
    scroll = window.Ui.textBrowser_log_main.verticalScrollBar()
    scroll.setValue(scroll.maximum())
    report["checks"]["main_failure_log_scroll_max"] = scroll.maximum()
    assert scroll.maximum() > 0
    for size in ((880, 700), (1100, 760)):
        _main_shot(window, app, output, "main-failure-log", size)


def main() -> None:
    output = Path("ui-audit/windows-results")
    output.mkdir(parents=True, exist_ok=True)
    _patch_runtime_side_effects()
    app = QApplication.instance() or QApplication([])
    report = {"font": _configure_cjk_font(app), "checks": {}}

    window = MyMAinWindow()
    window.show()
    app.processEvents()
    if not getattr(window, "_startup_finished", False):
        window._finish_startup()
    app.processEvents()

    _populate_tree(window)
    report["checks"]["result_tree_success_count"] = window.item_succ.childCount()
    report["checks"]["result_tree_failed_count"] = window.item_fail.childCount()
    assert window.item_succ.childCount() == 5 and window.item_fail.childCount() == 4
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    for size in SIZES:
        _main_shot(window, app, output, "result-tree", size)
    _size(window, app, 880, 700)
    window.Ui.treeWidget_number.scrollToBottom()
    app.processEvents()
    _render_widget(window, output / "880x700-result-tree-failures.jpg", quality=84)

    _success_history(window, app, output, report)
    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_log)
    _legacy_failures(window, app, output, report)
    _failure_center(window, app, output, report)
    _main_failure_log(window, app, output, report)

    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("timer", "timer_scrape", "timer_update", "timer_remain_task"):
        timer = getattr(window, name, None)
        if timer is not None:
            timer.stop()
    if hasattr(window, "_failure_center"):
        window._failure_center.hide()
        window._failure_center.deleteLater()
    window.hide()
    window.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    main()
