"""Compatibility facade for the split Qt Designer views.

The public ``Ui_MDCx`` name and every generated widget attribute are kept so
controllers and third-party integrations do not need to know that the former
single 25k-line form is now composed from page-sized forms.
"""

from __future__ import annotations

from PyQt6 import QtCore

from .MDCx_shell import Ui_MDCxShell
from .about_page import Ui_AboutPage
from .log_page import Ui_LogPage
from .main_page import Ui_MainPage
from .network_page import Ui_NetworkPage
from .nfo_overlay import Ui_NfoOverlay
from .settings_page import Ui_SettingsPage
from .tool_page import Ui_ToolPage


class Ui_MDCx(Ui_MDCxShell):
    """Assemble shell, pages and overlays while preserving the legacy API."""

    _COMPONENTS = (
        (Ui_MainPage, "page_main"),
        (Ui_LogPage, "page_log"),
        (Ui_NetworkPage, "page_net"),
        (Ui_ToolPage, "page_tool"),
        (Ui_SettingsPage, "page_setting"),
        (Ui_AboutPage, "page_about"),
        (Ui_NfoOverlay, "widget_nfo"),
    )

    def setupUi(self, MDCx):
        super().setupUi(MDCx)
        self._page_views = []
        for view_type, root_name in self._COMPONENTS:
            view = view_type()
            view.setupUi(getattr(self, root_name))
            self.__dict__.update(
                (name, value)
                for name, value in vars(view).items()
                if not name.startswith("_")
            )
            self._page_views.append(view)

        # Component forms connect against their page roots. Designer's slot
        # convention historically targeted the QMainWindow, so reconnect once
        # after every object has been assembled.
        QtCore.QMetaObject.connectSlotsByName(MDCx)
