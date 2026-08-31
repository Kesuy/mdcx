from __future__ import annotations

import ast
import os
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMainWindow

from mdcx.controllers.main_window.help_controller import HelpControllerMixin
from mdcx.controllers.main_window.log_controller import LogControllerMixin
from mdcx.controllers.main_window.main_page_mixin import MainPageMixin
from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.page_setup_mixin import PageSetupMixin
from mdcx.controllers.main_window.preview_controller import PreviewControllerMixin
from mdcx.controllers.main_window.settings_tool_slots import SettingsToolSlotsMixin
from mdcx.controllers.main_window.window_lifecycle import WindowLifecycleMixin
from mdcx.views.MDCx import Ui_MDCx

APP = QApplication.instance() or QApplication([])
ROOT = Path(__file__).resolve().parents[2]


def test_main_ui_is_composed_from_page_sized_designer_forms():
    views = ROOT / "mdcx" / "views"
    shell = ET.parse(views / "MDCx.ui").getroot()
    assert shell.findtext("class") == "MDCxShell"

    expected = {
        "main_page.ui": "page_main",
        "log_page.ui": "page_log",
        "network_page.ui": "page_net",
        "tool_page.ui": "page_tool",
        "settings_page.ui": "page_setting",
        "about_page.ui": "page_about",
        "nfo_overlay.ui": "widget_nfo",
    }
    for filename, root_name in expected.items():
        component = ET.parse(views / filename).getroot()
        assert component.find("widget").get("name") == root_name

    facade = ast.parse((views / "MDCx.py").read_text(encoding="utf-8"))
    assert len(facade.body) < 20

    window = QMainWindow()
    ui = Ui_MDCx()
    ui.setupUi(window)
    assert len(ui._page_views) == len(expected)
    assert ui.stackedWidget.count() == 6


def test_designer_sources_do_not_contain_inline_qss():
    views = ROOT / "mdcx" / "views"
    for path in views.glob("*.ui"):
        root = ET.parse(path).getroot()
        assert root.findall(".//property[@name='styleSheet']") == [], path.name


def test_settings_groups_are_native_designer_layouts_without_child_geometry():
    root = ET.parse(ROOT / "mdcx" / "views" / "settings_page.ui").getroot()
    groups = root.findall(".//widget[@class='QGroupBox']")

    assert len(groups) == 60
    assert all(group.find("./layout") is not None for group in groups)
    assert all(
        child.find("./property[@name='geometry']") is None for group in groups for child in group.findall("./widget")
    )


def test_main_window_delegates_page_and_lifecycle_responsibilities():
    assert issubclass(MyMAinWindow, PageSetupMixin)
    assert issubclass(MyMAinWindow, MainPageMixin)
    assert issubclass(MyMAinWindow, SettingsToolSlotsMixin)
    assert issubclass(MyMAinWindow, WindowLifecycleMixin)
    assert issubclass(MyMAinWindow, PreviewControllerMixin)
    assert issubclass(MyMAinWindow, LogControllerMixin)
    assert issubclass(MyMAinWindow, HelpControllerMixin)

    delegated = {
        "closeEvent",
        "resizeEvent",
        "show_main",
        "show_log",
        "show_help",
        "show_nfo",
        "_setup_fc2ppvdb_cookie_ui",
        "main_del_file_click",
        "pushButton_save_config_clicked",
        "change_buttons_status",
    }
    assert delegated.isdisjoint(MyMAinWindow.__dict__)

    source_path = ROOT / "mdcx" / "controllers" / "main_window" / "main_window.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    window_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MyMAinWindow")
    methods = {
        node.name: node for node in window_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert len(source.splitlines()) < 350
    assert set(methods) <= {
        "__init__",
        "_finish_startup",
        "_get_cutwindow",
        "_get_nfo_controller",
        "_get_file_controller",
        "_get_scrape_controller",
        "_get_tool_controller",
        "_apply_nfo_editor_patch",
        "_show_nfo_info",
        "_save_batch_nfo_info",
        "_find_related_cd_entries",
        "_save_nfo_entry",
        "save_nfo_info",
    }
