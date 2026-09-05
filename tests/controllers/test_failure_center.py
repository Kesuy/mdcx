from pathlib import Path

from PyQt6.QtWidgets import QApplication

from mdcx.controllers.main_window.failure_center import FailureCenterDialog
from mdcx.models.failure import FailureCategory, FailureRecord

APP = QApplication.instance() or QApplication([])


def test_failure_center_groups_counts_and_retries_only_retryable_records():
    retried = []
    network = FailureRecord(Path("A.mp4"), "crawl", FailureCategory.NETWORK, "timeout", True)
    auth = FailureRecord(Path("B.mp4"), "crawl", FailureCategory.AUTHENTICATION, "cookie expired", False)
    dialog = FailureCenterDialog(retry_callback=retried.extend)

    dialog.set_records([network, auth])

    assert dialog.tree.topLevelItemCount() == 2
    assert "2 条失败记录" in dialog.summary.text()
    network_group = next(
        dialog.tree.topLevelItem(index)
        for index in range(dialog.tree.topLevelItemCount())
        if dialog.tree.topLevelItem(index).text(0).startswith("network")
    )
    dialog.tree.setCurrentItem(network_group)
    assert dialog.retry_group.isVisibleTo(dialog)
    dialog._retry_selected_group()
    assert retried == [network]
    assert "1 条失败记录" in dialog.summary.text()

    dialog.set_records([auth])
    auth_leaf = dialog.tree.topLevelItem(0).child(0).child(0)
    dialog.tree.setCurrentItem(auth_leaf)
    assert not dialog.retry_one.isVisibleTo(dialog)
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
    leaf = dialog.tree.topLevelItem(0).child(0).child(0)

    dialog.tree.setCurrentItem(leaf)
    assert "internal detail" not in dialog.detail.toPlainText()
    assert dialog.show_debug.isVisibleTo(dialog)
    dialog.show_debug.setChecked(True)
    assert "internal detail" in dialog.detail.toPlainText()
    dialog.close()
