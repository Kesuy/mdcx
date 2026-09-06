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


def _show_data(number: str, source: str, file_path: str, *, title_suffix: str = "") -> ShowData:
    data = ShowData.empty()
    data.show_name = number
    data.data.number = number
    data.data.title = f"{number} 示例标题 {title_suffix}".strip()
    data.data.field_sources[CrawlerResultFields.TITLE] = source
    data.file_info.number = number
    data.file_info.file_name = Path(file_path).name
    data.file_info.file_path = Path(file_path)
    return data


def _populate_result_tree(window: MyMAinWindow) -> tuple[int, int]:
    success_rows = [
        ("ABC-123", "javdb", r"D:\Media\有码\ABC-123 示例文件 1080p.mkv"),
        ("IPZZ-941", "dmm", r"D:\Media\长目录名称\IPZZ-941 example filename with very long suffix 2160p HDR.mp4"),
        ("FC2-PPV-1234567", "fc2", r"D:\Media\FC2\2026\FC2-PPV-1234567 这是一个很长的文件名用于测试结果列表显示.webm"),
        ("HEYZO-1234", "本地 NFO", r"D:\Media\欧美\HEYZO-1234.mp4"),
        ("SAMPLE-0001", "javbus", r"D:\Media\Nested\One\Two\Three\SAMPLE-0001 long path sample.mp4"),
    ]
    failed_rows = [
        ("FAIL-NET-001", "javdb", r"D:\Media\Failed\FAIL-NET-001 network timeout sample.mp4"),
        ("FAIL-AUTH-002", "fc2", r"D:\Media\Failed\FAIL-AUTH-002 cookie expired sample with long name.mp4"),
        ("FAIL-PARSE-003", "dmm", r"D:\Media\Failed\FAIL-PARSE-003 parser changed sample.mp4"),
        ("FAIL-IO-004", "local", r"D:\Media\Failed\非常长的目录名\FAIL-IO-004 file locked by another process.mkv"),
    ]
    for number, source, path in success_rows:
        data = _show_data(number, source, path, title_suffix="刮削成功")
        window._addTreeChild("succ", number, data)
        window.json_array[number] = data
    for number, source, path in failed_rows:
        data = _show_data(number, source, path, title_suffix="刮削失败")
        window._addTreeChild("fail", number, data)
        window.json_array[number] = data
    window.item_succ.setText(0, f"成功 ({window.item_succ.childCount()})")
    window.item_fail.setText(0, f"失败 ({window.item_fail.childCount()})")
    window.Ui.treeWidget_number.expandAll()
    return len(success_rows), len(failed_rows)


def _failure_records() -> list[FailureRecord]:
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


def _populate_success_history(window: MyMAinWindow) -> int:
    Flags.success_list = {
        Path(rf"D:\Media\Library\分类目录-{index:02d}\TEST-{index:04d} 这是用于滚动和长路径测试的已刮削成功文件名 2160p.mkv")
        for index in range(1, 31)
    }
    return len(Flags.success_list)


def _populate_failed_log(window: MyMAinWindow) -> int:
    Flags.failed_records = []
    rows = []
    for index in range(1, 36):
        path = rf"D:\Media\Failed\批量任务\第{index:02d}组\FAIL-{index:04d} long failed filename sample.mp4"
        reason = (
            "网络请求超时，代理连接被重置；将在网络恢复后重试"
            if index % 3 == 1
            else "未找到匹配结果，请检查番号或切换数据源"
            if index % 3 == 2
            else "文件被占用，移动到目标目录失败 [WinError 32]"
        )
        rows.append((Path(path), reason))
    Flags.failed_list = rows
    signal_qt.logs_failed_settext.emit("")
    for path, reason in rows:
        signal_qt.logs_failed_show.emit(f"{path}\n    原因：{reason}")
    window.update_failure_count(f"失败 ({len(rows)})")
    window.show_hide_failed_list(True)
    return len(rows)


def _prepare_size(window: MyMAinWindow, app: QApplication, width: int, height: int) -> None:
    window.resize(width, height)
    apply_responsive_layout(window)
    app.processEvents()


def _capture(window: MyMAinWindow, app: QApplication, output: Path, name: str, width: int, height: int) -> dict[str, object]:
    _prepare_size(window, app, width, height)
    size = _render_widget(window, output / f"{width}x{height}-{name}.jpg", quality=84)
    return {"name": name, "window": [width, height], "image": list(size)}


def _capture_success_history(
    window: MyMAinWindow,
    app: QApplication,
    output: Path,
    width: int,
    height: int,
) -> dict[str, object]:
    _prepare_size(window, app, width, height)
    window.pushButton_view_success_file_clicked()
    app.processEvents()
    assert window.Ui.widget_show_success.isVisibleTo(window)
    size = _render_widget(window, output / f"{width}x{height}-success-history.jpg", quality=84)
    window.Ui.widget_show_success.hide()
    return {"name": "success-history", "window": [width, height], "image": list(size)}


def _write_report(output: Path, report: dict[str, object]) -> None:
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    output = Path("ui-audit/windows-results")
    output.mkdir(parents=True, exist_ok=True)
    _patch_runtime_side_effects()
    app = QApplication.instance() or QApplication([])
    font_info = _configure_cjk_font(app)
    window = MyMAinWindow()
    window.show()
    app.processEvents()
    if not getattr(window, "_startup_finished", False):
        window._finish_startup()
    app.processEvents()

    report: dict[str, object] = {"font": font_info, "captures": [], "checks": {}}

    expected_success, expected_failed = _populate_result_tree(window)
    report["checks"]["result_tree_success_count"] = window.item_succ.childCount()
    report["checks"]["result_tree_failed_count"] = window.item_fail.childCount()
    assert window.item_succ.childCount() == expected_success
    assert window.item_fail.childCount() == expected_failed

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_main)
    for width, height in SIZES:
        report["captures"].append(_capture(window, app, output, "result-tree", width, height))
    _prepare_size(window, app, 880, 700)
    window.Ui.treeWidget_number.scrollToBottom()
    app.processEvents()
    _render_widget(window, output / "880x700-result-tree-failures.jpg", quality=84)

    success_history_count = _populate_success_history(window)
    report["checks"]["success_history_count"] = success_history_count
    for width, height in SIZES:
        report["captures"].append(_capture_success_history(window, app, output, width, height))
    report["checks"]["success_history_text_lines"] = len(window.Ui.textBrowser_show_success_list.toPlainText().splitlines())
    report["checks"]["success_history_scroll_max"] = window.Ui.textBrowser_show_success_list.verticalScrollBar().maximum()
    assert report["checks"]["success_history_text_lines"] == success_history_count
    assert report["checks"]["success_history_scroll_max"] > 0

    window.Ui.stackedWidget.setCurrentWidget(window.Ui.page_log)
    failed_log_count = _populate_failed_log(window)
    app.processEvents()
    failed_scroll = window.Ui.textBrowser_log_main_3.verticalScrollBar()
    report["checks"]["failed_log_count"] = failed_log_count
    report["checks"]["failed_log_scroll_max"] = failed_scroll.maximum()
    report["checks"]["failed_log_scroll_value"] = failed_scroll.value()
    report["checks"]["failed_log_retry_visible"] = window.Ui.pushButton_scraper_failed_list.isVisible()
    report["checks"]["failed_log_save_visible"] = window.Ui.pushButton_save_failed_list.isVisible()
    assert failed_scroll.maximum() > 0
    assert failed_scroll.value() == failed_scroll.maximum()
    assert window.Ui.pushButton_scraper_failed_list.isVisible()
    assert window.Ui.pushButton_save_failed_list.isVisible()
    for width, height in SIZES:
        report["captures"].append(_capture(window, app, output, "failed-log", width, height))

    window.show_hide_failed_list(False)
    Flags.failed_records = _failure_records()
    Flags.failed_list = [record.legacy_tuple() for record in Flags.failed_records]
    window.pushButton_show_hide_failed_list_clicked()
    app.processEvents()
    dialog = window._failure_center
    report["checks"]["failure_center_rows"] = dialog.tree.topLevelItemCount()
    report["checks"]["failure_center_summary"] = dialog.summary.text()
    assert dialog.tree.topLevelItemCount() == len(Flags.failed_records)
    assert dialog.retry_all.isEnabled()

    dialog.resize(700, 500)
    app.processEvents()
    _render_widget(dialog, output / "failure-center-700x500.jpg", quality=84)
    dialog.resize(920, 600)
    app.processEvents()
    _render_widget(dialog, output / "failure-center-920x600.jpg", quality=84)

    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(1))
    app.processEvents()
    report["checks"]["non_retryable_button_enabled"] = dialog.retry_one.isEnabled()
    assert not dialog.retry_one.isEnabled()
    _render_widget(dialog, output / "failure-center-non-retryable.jpg", quality=84)

    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(0))
    app.processEvents()
    report["checks"]["retryable_button_enabled"] = dialog.retry_one.isEnabled()
    report["checks"]["debug_button_visible"] = dialog.show_debug.isVisible()
    assert dialog.retry_one.isEnabled()
    assert dialog.show_debug.isVisible()
    dialog.show_debug.setChecked(True)
    app.processEvents()
    assert "Traceback" in dialog.detail.toPlainText()
    _render_widget(dialog, output / "failure-center-debug-detail.jpg", quality=84)

    retried: list[FailureRecord] = []
    dialog._retry_callback = lambda records: retried.extend(records) or True
    before_rows = dialog.tree.topLevelItemCount()
    dialog.retry_one.click()
    app.processEvents()
    report["checks"]["retry_selected_callback_count"] = len(retried)
    report["checks"]["failure_center_rows_after_retry"] = dialog.tree.topLevelItemCount()
    assert len(retried) == 1
    assert dialog.tree.topLevelItemCount() == before_rows - 1
    _render_widget(dialog, output / "failure-center-after-retry.jpg", quality=84)

    dialog.hide()
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
    main_scroll = window.Ui.textBrowser_log_main.verticalScrollBar()
    main_scroll.setValue(main_scroll.maximum())
    report["checks"]["main_failure_log_scroll_max"] = main_scroll.maximum()
    assert main_scroll.maximum() > 0
    for width, height in ((880, 700), (1100, 760)):
        report["captures"].append(_capture(window, app, output, "main-failure-log", width, height))

    _write_report(output, report)

    for timer_name in ("timer", "timer_scrape", "timer_update", "timer_remain_task"):
        timer = getattr(window, timer_name, None)
        if timer is not None:
            timer.stop()
    dialog.hide()
    dialog.deleteLater()
    window.hide()
    window.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    main()
