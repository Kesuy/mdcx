import os
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QComboBox, QMainWindow

from mdcx.config.enums import Website, website_display_name, website_from_display_name
from mdcx.config.models import Config
from mdcx.controllers.main_window import init as window_init
from mdcx.controllers.main_window.site_priority_dialog import _make_site_item, _parse_sites, _sites_text
from mdcx.crawlers import get_registered_crawler_site_values
from mdcx.views.MDCx import Ui_MDCx

APP = QApplication.instance() or QApplication([])


def test_fc2ppvdb_is_available_in_single_website_options():
    registered_sites = get_registered_crawler_site_values()

    assert Website.FC2PPVDB.value in registered_sites


def test_single_website_combo_displays_fc2cmadb_instead_of_legacy_internal_name():
    window = QMainWindow()
    ui = Ui_MDCx()
    ui.setupUi(window)
    options = [ui.comboBox_website_all.itemText(index) for index in range(ui.comboBox_website_all.count())]

    assert "fc2cmadb" in options
    assert Website.FC2PPVDB.value not in options


def test_runtime_initialized_single_website_combo_displays_fc2cmadb(monkeypatch):
    monkeypatch.setattr(window_init, "setup_result_sort_ui", lambda _window: None)
    monkeypatch.setattr(window_init, "setup_local_nfo_button", lambda _window: None)
    monkeypatch.setattr(window_init, "_setup_combo_boxes", lambda _window: None)
    monkeypatch.setattr(window_init, "setup_site_priority_ui", lambda _window: None)
    monkeypatch.setattr(window_init, "setup_responsive_ui", lambda _window: None)

    window = MagicMock()
    window.Ui.comboBox_website_all = QComboBox()
    window.Ui.comboBox_custom_website = QComboBox()

    window_init.Init_Ui(window)

    options = [
        window.Ui.comboBox_website_all.itemText(index) for index in range(window.Ui.comboBox_website_all.count())
    ]
    assert "fc2cmadb" in options
    assert Website.FC2PPVDB.value not in options


def test_fc2cmadb_display_name_round_trips_to_legacy_config_value():
    assert website_display_name(Website.FC2PPVDB) == "fc2cmadb"
    assert website_from_display_name("fc2cmadb") == Website.FC2PPVDB
    assert website_display_name(Website.FC2) == "fc2"
    assert website_from_display_name("fc2") == Website.FC2


def test_fc2_priority_editor_displays_alias_but_keeps_internal_site_value():
    item = _make_site_item(Website.FC2PPVDB)

    assert item.text() == "fc2cmadb"
    assert item.data(Qt.ItemDataRole.UserRole) == Website.FC2PPVDB.value
    assert _sites_text([Website.FC2PPVDB, Website.FC2]) == "fc2cmadb,fc2"
    assert _parse_sites("fc2cmadb,fc2") == [Website.FC2PPVDB, Website.FC2]


def test_javdbapi_is_available_in_single_website_options():
    registered_sites = get_registered_crawler_site_values()

    assert Website.JAVDBAPI.value in registered_sites


def test_config_website_schema_uses_registered_crawler_sites():
    website_schema = Config.json_schema()["$defs"]["Website"]
    registered_sites = get_registered_crawler_site_values()

    assert website_schema["enum"] == registered_sites
    assert Website.AIRAV.value not in website_schema["enum"]
