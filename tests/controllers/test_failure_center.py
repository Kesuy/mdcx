from pathlib import Path

from PyQt6.QtWidgets import QApplication

from mdcx.controllers.main_window.failure_center import FailureCenterDialog
from mdcx.models.failure import FailureCategory, FailureRecord

APP = QApplication.instance() or QApplication([])


def test_failure_center_summarizes_filters_and_retries_only_direct_retry_records():
    retried = []
    network = FailureRecord(
        Path("A.mp4"),
        "crawl",
        FailureCategory.NETWORK,
        "timeout",
        True,
        site="javdb",
        context={"number": "ABC-001"},
    )
    auth = FailureRecord(
        Path("B.mp4"),
        "crawl",
        FailureCategory.AUTHENTICATION,
        "cookie expired",
        False,
        site="fc2ppvdb",
        context={"number": "FC2-123"},
    )
    dialog = FailureCenterDialog(retry_callback=retried.extend)

    dialog.set_records([network, auth])

    assert dialog.tree.topLevelItemCount() == 2
    assert "本轮失败 2" in dialog.summary.text()
    assert "可直接重试 1" in dialog.summary.text()
    assert "需处理 1" in dialog.summary.text()

    network_item = dialog.tree.topLevelItem(0)
    assert network_item.text(0) == "A.mp4"
    assert network_item.text(1) == "ABC-001"
    assert network_item.text(2) == "网络连接"
    assert network_item.text(4) == "javdb"
    assert network_item.text(5) == "可直接重试"
    assert dialog.retry_one.isEnabled()
    assert dialog.retry_all.isEnabled()
    assert "处理建议：网络请求" in dialog.detail.toPlainText()

    dialog.search.setText("FC2-123")
    assert dialog.tree.topLevelItemCount() == 1
    assert dialog.tree.topLevelItem(0).text(0) == "B.mp4"
    assert "当前显示 1" in dialog.summary.text()

    dialog._clear_filters()
    dialog._retry_all()
    assert retried == [network]
    assert "本轮失败 1" in dialog.summary.text()

    auth_item = dialog.tree.topLevelItem(0)
    dialog.tree.setCurrentItem(auth_item)
    assert auth_item.text(2) == "登录认证"
    assert not dialog.retry_one.isEnabled()
    assert not dialog.retry_all.isEnabled()
    assert dialog.retry_after_fix.isEnabled()
    dialog.close()


def test_failure_center_allows_explicit_retry_after_user_fix():
    retried = []
    auth = FailureRecord(
        Path("B.mp4"),
        "crawl",
        FailureCategory.AUTHENTICATION,
        "cookie expired",
        False,
    )
    dialog = FailureCenterDialog(retry_callback=retried.extend)
    dialog.set_records([auth])

    dialog._retry_selected_after_fix()

    assert retried == [auth]
    assert dialog.tree.topLevelItemCount() == 0
    assert "已提交 1 个任务重新刮削" in dialog.feedback.text()
    dialog.close()


def test_failure_center_filters_by_category_and_retry_state():
    records = [
        FailureRecord(Path("A.mp4"), "crawl", FailureCategory.NETWORK, "timeout", True),
        FailureRecord(Path("B.mp4"), "crawl", FailureCategory.NETWORK, "HTTP 429", True),
        FailureRecord(Path("C.mp4"), "scrape", FailureCategory.INTERNAL_ERROR, "boom", False),
    ]
    dialog = FailureCenterDialog()
    dialog.set_records(records)

    network_index = dialog.category_filter.findData(FailureCategory.NETWORK.value)
    dialog.category_filter.setCurrentIndex(network_index)
    assert dialog.tree.topLevelItemCount() == 2
    assert "网络连接 2" in dialog.category_summary.text()

    dialog.retry_filter.setCurrentIndex(dialog.retry_filter.findData("attention"))
    assert dialog.tree.topLevelItemCount() == 0

    dialog.category_filter.setCurrentIndex(0)
    assert dialog.tree.topLevelItemCount() == 1
    assert dialog.tree.topLevelItem(0).text(0) == "C.mp4"
    dialog.close()


def test_failure_center_focus_path_reveals_matching_filtered_record():
    first = FailureRecord(
        Path("A.mp4"),
        "crawl",
        FailureCategory.NETWORK,
        "timeout",
        True,
        context={"number": "ABC-001"},
    )
    second = FailureRecord(
        Path("B.mp4"),
        "crawl",
        FailureCategory.AUTHENTICATION,
        "cookie expired",
        False,
        context={"number": "ABC-002"},
    )
    dialog = FailureCenterDialog()
    dialog.set_records([first, second])
    dialog.search.setText("ABC-001")
    assert dialog.tree.topLevelItemCount() == 1

    assert dialog.focus_path(Path("B.mp4")) is True

    assert dialog.search.text() == ""
    assert dialog.tree.topLevelItemCount() == 2
    assert dialog.tree.currentItem().text(0) == "B.mp4"
    dialog.close()


def test_failure_debug_detail_is_hidden_until_requested():
    record = FailureRecord(
        Path("A.mp4"),
        "scrape",
        FailureCategory.INTERNAL_ERROR,
        "unexpected failure",
        False,
        debug_detail="Traceback: internal detail",
        context={"number": "ABC-123", "scrape_like": "info"},
    )
    dialog = FailureCenterDialog()
    dialog.set_records([record])
    leaf = dialog.tree.topLevelItem(0)

    dialog.tree.setCurrentItem(leaf)
    assert "程序异常" in dialog.detail.toPlainText()
    assert "发生阶段：刮削" in dialog.detail.toPlainText()
    assert "番号：ABC-123" in dialog.detail.toPlainText()
    assert "internal detail" not in dialog.detail.toPlainText()
    assert dialog.show_debug.isVisibleTo(dialog)
    dialog.show_debug.setChecked(True)
    assert "internal detail" in dialog.detail.toPlainText()
    dialog.close()
