from pathlib import Path

from PyQt6.QtWidgets import QApplication

from mdcx.controllers.main_window.failure_center import FailureCenterDialog
from mdcx.models.failure import FailureCategory, FailureRecord

APP = QApplication.instance() or QApplication([])


def test_failure_center_uses_flat_chinese_summary_and_retries_only_retryable_records():
    retried = []
    network = FailureRecord(Path("A.mp4"), "crawl", FailureCategory.NETWORK, "timeout", True)
    auth = FailureRecord(Path("B.mp4"), "crawl", FailureCategory.AUTHENTICATION, "cookie expired", False)
    dialog = FailureCenterDialog(retry_callback=retried.extend)

    dialog.set_records([network, auth])

    assert dialog.tree.topLevelItemCount() == 2
    assert "2 条失败" in dialog.summary.text()
    assert "1 条可直接重试" in dialog.summary.text()

    network_item = dialog.tree.topLevelItem(0)
    assert network_item.text(0) == "A.mp4"
    assert network_item.text(1) == "网络连接"
    assert dialog.retry_one.isEnabled()
    assert dialog.retry_all.isEnabled()
    assert "处理建议：网络请求" in dialog.detail.toPlainText()

    dialog._retry_all()
    assert retried == [network]
    assert "1 条失败" in dialog.summary.text()

    auth_item = dialog.tree.topLevelItem(0)
    dialog.tree.setCurrentItem(auth_item)
    assert auth_item.text(1) == "登录认证"
    assert not dialog.retry_one.isEnabled()
    assert not dialog.retry_all.isEnabled()
    dialog.close()


def test_failure_debug_detail_is_hidden_until_requested():
    record = FailureRecord(
        Path("A.mp4"),
        "scrape",
        FailureCategory.INTERNAL_ERROR,
        "unexpected failure",
        False,
        debug_detail="Traceback: internal detail",
    )
    dialog = FailureCenterDialog()
    dialog.set_records([record])
    leaf = dialog.tree.topLevelItem(0)

    dialog.tree.setCurrentItem(leaf)
    assert "程序异常" in dialog.detail.toPlainText()
    assert "发生阶段：刮削" in dialog.detail.toPlainText()
    assert "internal detail" not in dialog.detail.toPlainText()
    assert dialog.show_debug.isVisibleTo(dialog)
    dialog.show_debug.setChecked(True)
    assert "internal detail" in dialog.detail.toPlainText()
    dialog.close()
