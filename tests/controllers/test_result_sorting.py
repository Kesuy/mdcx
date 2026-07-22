# ruff: noqa: E402, I001

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.result_sorting import ResultSortEntry, sort_result_entries
from mdcx.models.types import CrawlersResult, FileInfo, OtherInfo, ShowData

APP = QApplication.instance() or QApplication([])


def _entries() -> list[ResultSortEntry]:
    return [
        ResultSortEntry("third", "H10", "佐藤", 2),
        ResultSortEntry("first", "H2", "天宮", 0),
        ResultSortEntry("second", "A-20", "阿部", 1),
    ]


def test_sort_result_entries_keeps_completion_order_by_default():
    assert [entry.show_name for entry in sort_result_entries(_entries(), "完成顺序")] == [
        "first",
        "second",
        "third",
    ]


def test_sort_result_entries_uses_natural_number_order():
    assert [entry.show_name for entry in sort_result_entries(_entries(), "番号")] == [
        "second",
        "first",
        "third",
    ]


def test_sort_result_entries_sorts_actor_and_supports_descending():
    assert [entry.show_name for entry in sort_result_entries(_entries(), "演员", descending=True)] == [
        "second",
        "first",
        "third",
    ]


def test_main_result_tree_reorders_success_children_by_number():
    class Harness:
        _addTreeChild = MyMAinWindow._addTreeChild
        _sort_success_results = MyMAinWindow._sort_success_results

    harness = Harness()
    harness.Ui = SimpleNamespace(treeWidget_number=QTreeWidget())
    harness.item_succ = QTreeWidgetItem(harness.Ui.treeWidget_number, ["成功"])
    harness.item_fail = QTreeWidgetItem(harness.Ui.treeWidget_number, ["失败"])
    harness.result_sort_combo = QComboBox()
    harness.result_sort_combo.addItems(["完成顺序", "番号", "演员"])
    harness.result_sort_order_button = QPushButton("↑")
    harness._result_sort_descending = False
    harness._result_insertion_index = 0
    harness.json_array = {}

    for show_name, number in (("row-10", "H10"), ("row-2", "H2")):
        data = CrawlersResult.empty()
        data.number = number
        harness.json_array[show_name] = ShowData(FileInfo.empty(), data, OtherInfo.empty(), show_name)
        harness._addTreeChild("succ", show_name)

    harness.result_sort_combo.setCurrentText("番号")
    harness._sort_success_results()

    assert [harness.item_succ.child(index).text(0) for index in range(2)] == ["row-2", "row-10"]
    assert APP is not None
