# ruff: noqa: E402, I001

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.result_model import RESULT_DATA_ROLE, ResultTreeItem, ResultTreeView
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


def test_result_items_keep_their_own_data_when_display_names_repeat():
    class Harness:
        _addTreeChild = MyMAinWindow._addTreeChild
        _get_selected_result_items = MyMAinWindow._get_selected_result_items
        _get_selected_entries = MyMAinWindow._get_selected_entries

    harness = Harness()
    harness.Ui = SimpleNamespace(treeWidget_number=ResultTreeView())
    harness.item_succ = ResultTreeItem(harness.Ui.treeWidget_number)
    harness.item_succ.setText(0, "成功")
    harness.item_fail = ResultTreeItem(harness.Ui.treeWidget_number)
    harness.item_fail.setText(0, "失败")
    harness._result_insertion_index = 0
    harness.json_array = {}

    first_data = CrawlersResult.empty()
    first_data.title = "first title"
    first = ShowData(FileInfo.empty(), first_data, OtherInfo.empty(), "相同名称")
    second_data = CrawlersResult.empty()
    second_data.title = "second title"
    second = ShowData(FileInfo.empty(), second_data, OtherInfo.empty(), "相同名称")
    harness._addTreeChild("succ", first.show_name, first)
    harness._addTreeChild("succ", second.show_name, second)

    first_item = harness.item_succ.child(0)
    second_item = harness.item_succ.child(1)
    assert first_item.data(0, RESULT_DATA_ROLE) is first
    assert second_item.data(0, RESULT_DATA_ROLE) is second
    first_item.setSelected(True)
    assert harness._get_selected_result_items() == [first_item]


def test_clicking_each_result_displays_that_items_bound_data():
    class Harness:
        _addTreeChild = MyMAinWindow._addTreeChild
        _get_selected_result_items = MyMAinWindow._get_selected_result_items
        _show_result_item = MyMAinWindow._show_result_item
        treeWidget_number_index_clicked = MyMAinWindow.treeWidget_number_index_clicked
        treeWidget_number_clicked = MyMAinWindow.treeWidget_number_clicked

    harness = Harness()
    harness.Ui = SimpleNamespace(treeWidget_number=ResultTreeView(), widget_nfo=SimpleNamespace(isHidden=lambda: True))
    harness.item_succ = ResultTreeItem(harness.Ui.treeWidget_number)
    harness.item_succ.setText(0, "成功")
    harness.item_fail = ResultTreeItem(harness.Ui.treeWidget_number)
    harness.item_fail.setText(0, "失败")
    harness._result_insertion_index = 0
    harness.json_array = {}
    shown = []
    harness.set_main_info = shown.append

    first = ShowData(FileInfo.empty(), CrawlersResult.empty(), OtherInfo.empty(), "相同名称")
    second = ShowData(FileInfo.empty(), CrawlersResult.empty(), OtherInfo.empty(), "相同名称")
    harness._addTreeChild("succ", first.show_name, first)
    harness._addTreeChild("succ", second.show_name, second)

    for item, expected in ((harness.item_succ.child(0), first), (harness.item_succ.child(1), second)):
        harness.Ui.treeWidget_number.clearSelection()
        item.setSelected(True)
        harness.treeWidget_number_clicked()
        assert shown[-1] is expected

    # The clicked index is authoritative even if a stale selection still points
    # at a different row during proxy-model sorting/reset activity.
    harness.Ui.treeWidget_number.clearSelection()
    harness.item_succ.child(0).setSelected(True)
    second_index = harness.Ui.treeWidget_number.indexFromItem(harness.item_succ.child(1))
    harness.treeWidget_number_index_clicked(second_index)
    assert shown[-1] is second
